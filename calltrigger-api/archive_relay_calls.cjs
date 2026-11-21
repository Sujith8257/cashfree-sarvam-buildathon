const terminal = new Set(['connected', 'no_answer', 'failed', 'busy', 'rejected', 'canceled', 'cancelled']);
const attemptIdPattern = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i;

function present(value) {
  return typeof value === 'string' && value.trim() && !/^(na|n\/a|unknown|null)$/i.test(value.trim())
    ? value.trim() : null;
}

function asUtc(value) {
  if (typeof value !== 'string' || !value) return null;
  const timestamp = Date.parse(/[zZ]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
  return Number.isFinite(timestamp) ? new Date(timestamp).toISOString() : null;
}

function archiveCalls(supabase, supabaseKey) {
  const org = process.env.SARVAM_VOICE_ORG_ID;
  const workspace = process.env.SARVAM_VOICE_WORKSPACE_ID;
  const app = process.env.SARVAM_VOICE_APP_ID;
  const voiceKey = process.env.SARVAM_VOICE_API_KEY;
  if (![org, workspace, app].every(value => value && /^[A-Za-z0-9_-]+$/.test(value)) || !voiceKey) {
    throw new Error('Supply the Sarvam Voice workspace identifiers and API key');
  }

  const sarvam = 'https://apps.sarvam.ai';
  const outbound = `${sarvam}/api/outbounds/v1/orgs/${org}/workspaces/${workspace}/outbounds`;
  const analytics = `${sarvam}/api/analytics/v1/${org}/${workspace}/${app}`;
  const storage = `${supabase.origin}/storage/v1/object/`;
  const tracked = new Map();
  const stored = new Set();

  async function sarvamGet(path) {
    const response = await fetch(analytics + path, {
      headers: { 'X-API-Key': voiceKey }, redirect: 'error', signal: AbortSignal.timeout(25_000),
    });
    if (!response.ok && response.status !== 404) throw new Error(`Sarvam analytics returned ${response.status}`);
    return response;
  }

  async function upload(path, type, body) {
    const response = await fetch(storage + path, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(45_000),
      headers: { apikey: supabaseKey, 'Content-Type': type, 'x-upsert': 'true' }, body,
    });
    if (!response.ok) throw new Error(`Supabase call archive upload returned ${response.status}`);
  }

  async function isArchived(path) {
    const response = await fetch(`${storage}authenticated/${path}.json`, {
      method: 'HEAD', headers: { apikey: supabaseKey }, redirect: 'error', signal: AbortSignal.timeout(12_000),
    });
    if (response.ok) return true;
    if (response.status === 400 || response.status === 404) return false;
    throw new Error(`Supabase call archive lookup returned ${response.status}`);
  }

  async function paymentStatus(linkId) {
    const clientId = process.env.CASHFREE_SANDBOX_CLIENT_ID;
    const secret = process.env.CASHFREE_SANDBOX_CLIENT_SECRET;
    if (!clientId || !secret || typeof linkId !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(linkId)) return null;
    const response = await fetch(`https://sandbox.cashfree.com/pg/links/${linkId}`, {
      headers: { 'x-api-version': '2025-01-01', 'x-client-id': clientId, 'x-client-secret': secret },
      redirect: 'error', signal: AbortSignal.timeout(10_000),
    }).catch(() => null);
    if (!response?.ok) return null;
    const link = await response.json();
    return link.link_id === linkId ? present(link.link_status) : null;
  }

  function track(node, startedAt) {
    if (node.status !== 'COMPLETED' || node.input?.url !== outbound || node.output?.status !== 200) return;
    const id = node.output.body?.attempt_id;
    if (!attemptIdPattern.test(id || '') || tracked.has(id) || stored.has(id)) return;

    const raw = node.input.body?.data;
    let body = raw;
    if (typeof raw === 'string') {
      try { body = JSON.parse(raw); } catch { return; }
    }
    const variables = body?.app_config?.agent_variables;
    const customerId = variables?.customer_id;
    if (body?.app_config?.app_id !== app || !['string', 'number'].includes(typeof customerId) ||
        !String(customerId).trim()) return;
    tracked.set(id, { customerId, linkId: variables.link_id, startedAt: Date.parse(startedAt) });
  }

  async function save(attempt, source) {
    const status = attempt.connectivity_status;
    if (!terminal.has(status)) return 'pending';
    if (status === 'connected' && (!attempt.interaction_id || !attempt.end_datetime)) return 'pending';
    const timestamp = asUtc(attempt.start_datetime ?? attempt.attempted_at);
    if (!timestamp) return 'pending';

    const path = `call-recordings/sandbox/${attempt.attempt_id}`;
    if (await isArchived(path)) return 'existing';
    let transcript = null;
    let recording = null;
    if (status === 'connected') {
      const id = encodeURIComponent(attempt.interaction_id);
      const [text, audio] = await Promise.all([sarvamGet(`/transcripts/${id}`), sarvamGet(`/recordings/${id}`)]);
      if (!text.ok || !audio.ok) return 'pending';
      const { messages } = await text.json();
      if (!Array.isArray(messages) || (attempt.num_messages > 0 && !messages.length)) return 'pending';
      transcript = messages;
      const wav = Buffer.from(await audio.arrayBuffer());
      if (wav.subarray(0, 4).toString() !== 'RIFF' || wav.subarray(8, 12).toString() !== 'WAVE') {
        throw new Error('Sarvam returned an unexpected recording format');
      }
      recording = `${path}.wav`;
      await upload(recording, 'audio/wav', wav);
    }

    const variables = attempt.agent_variables || {};
    const reportedDate = present(variables.promisedToPayDate ?? variables.promise_to_pay_date);
    const amount = Number(variables.promisedToPayAmount ?? variables.promise_to_pay_amount);
    const doc = {
      attempt_id: attempt.attempt_id,
      customer_id: source.customerId,
      call_datetime: timestamp,
      call_status: status,
      language_used: present(attempt.language_name),
      call_transcript: transcript,
      call_summary: present(variables.callSummary ?? variables.call_summary),
      customer_feedback: present(variables.customerFeedback ?? variables.customer_feedback),
      payment_status: await paymentStatus(source.linkId),
      promise_to_pay_date: reportedDate && /^\d{4}-\d{2}-\d{2}$/.test(reportedDate) ? reportedDate : null,
      promise_to_pay_amount: Number.isFinite(amount) && amount > 0 ? amount : null,
      call_recording: recording,
    };
    // Write the metadata last so a failed upload can be retried without duplicating the log.
    await upload(`${path}.json`, 'application/json', JSON.stringify(doc));
    return 'added';
  }

  async function sync() {
    if (!tracked.size) return { saved: 0, verified: 0, pending: 0 };
    const lower = Math.min(...Array.from(tracked.values(), source => source.startedAt), Date.now()) - 60_000;
    const query = new URLSearchParams({
      start_datetime: new Date(lower).toISOString(), end_datetime: new Date().toISOString(),
      limit: '100', sort_by: 'effective_datetime', sort_order: 'desc',
    });
    let saved = 0;
    let verified = 0;
    for (let offset = 0; tracked.size; offset += 100) {
      query.set('offset', String(offset));
      const response = await sarvamGet(`/attempts?${query}`);
      if (!response.ok) throw new Error('Sarvam attempts endpoint was not found');
      const page = await response.json();
      for (const attempt of page.items || []) {
        const source = tracked.get(attempt.attempt_id);
        if (!source) continue;
        const result = await save(attempt, source);
        if (result === 'pending') continue;
        if (result === 'added') saved += 1;
        verified += 1;
        tracked.delete(attempt.attempt_id);
        stored.add(attempt.attempt_id);
      }
      if (!page.next_page_uri) break;
    }
    return { saved, verified, pending: tracked.size };
  }

  return { track, sync };
}

module.exports = { archiveCalls };
