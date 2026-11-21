const { setTimeout: delay } = require('node:timers/promises');
const { chromium } = require(process.env.RELAY_PLAYWRIGHT_MODULE || 'playwright');

const relayApi = 'https://sandbox.cashfree.com/merchantuiapisvc/merchant/relay/v1';
const supabase = new URL(process.env.SUPABASE_URL);
const apiKey = process.env.SUPABASE_SECRET_KEY;
const agents = (process.env.RELAY_SANDBOX_AGENT_IDS || '').split(',');
const watch = process.argv.includes('--watch');
const completedRuns = new Set();

if (supabase.protocol !== 'https:' || !supabase.hostname.endsWith('.supabase.co') ||
    supabase.pathname !== '/' || supabase.username || supabase.password || !apiKey) {
  throw new Error('Set SUPABASE_URL to the project origin and provide SUPABASE_SECRET_KEY');
}
if (agents.some(agent => !/^\d+$/.test(agent))) {
  throw new Error('Set RELAY_SANDBOX_AGENT_IDS to the comma-separated sandbox workflow IDs');
}

async function relaySession(context) {
  const page = await context.newPage();
  try {
    const path = `/agents/${agents[0]}`;
    const [response] = await Promise.all([
      page.waitForResponse(result => result.url() === relayApi + path && result.ok(), { timeout: 12_000 }),
      page.goto(`https://merchant.cashfree.com/merchants/pg/relay/agent/${agents[0]}`, {
        timeout: 12_000, waitUntil: 'domcontentloaded',
      }),
    ]);
    const authorization = await response.request().headerValue('authorization');
    if (!authorization?.startsWith('Bearer ')) throw new Error('Sign in to Cashfree in Playwright');
    return { authorization };
  } finally {
    await page.close();
  }
}

async function getRelay(request, headers, path) {
  const response = await request.get(relayApi + path, { headers, timeout: 12_000, maxRedirects: 0 });
  if (!response.ok()) throw new Error(`Relay read returned ${response.status()}`);
  return response.json();
}

async function archiveLink(link) {
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(link.link_id) || typeof link.link_url !== 'string') {
    throw new Error('Unexpected Cashfree link response');
  }
  const checkout = new URL(link.link_url);
  if (checkout.origin !== 'https://payments-test.cashfree.com') {
    throw new Error('Unexpected sandbox checkout host');
  }

  const path = `payment-link-logs/sandbox/${link.link_id}.json`;
  const objects = `${supabase.origin}/storage/v1/object/`;
  const request = { headers: { apikey: apiKey }, redirect: 'error', signal: AbortSignal.timeout(12_000) };
  const existing = await fetch(`${objects}authenticated/${path}`, request);
  if (existing.ok) {
    const prior = await existing.json();
    if (prior.link_id !== link.link_id || prior.link_url !== link.link_url) {
      throw new Error('Stored link differs from the Cashfree result');
    }
    return false;
  }

  const missing = await existing.json().catch(() => ({}));
  if (existing.status !== 404 && !(existing.status === 400 && String(missing.statusCode) === '404')) {
    throw new Error(`Supabase object read returned ${existing.status}`);
  }
  const response = await fetch(objects + path, {
    ...request,
    method: 'POST',
    headers: { ...request.headers, 'Content-Type': 'application/json', 'x-upsert': 'true' },
    body: JSON.stringify({
      link_id: link.link_id,
      link_url: link.link_url,
      link_status: link.link_status,
      link_amount: link.link_amount,
      link_currency: link.link_currency,
      link_created_at: link.link_created_at,
      environment: 'sandbox',
      recorded_at: new Date().toISOString(),
    }),
  });
  if (!response.ok) throw new Error(`Supabase object write returned ${response.status}`);
  return true;
}

async function sync(request, headers) {
  let saved = 0;
  let verified = 0;
  const since = Date.now() - 60 * 60 * 1000;
  for (const agent of agents) {
    const list = await getRelay(request, headers, `/execution-records/agent/${agent}`);
    if (!Array.isArray(list.items)) throw new Error('Unexpected Relay run list');
    for (const run of list.items) {
      if (run.status !== 'COMPLETED' || Date.parse(run.startedAt) < since ||
          !Number.isSafeInteger(run.executionId) || completedRuns.has(run.executionId)) {
        continue;
      }
      const detail = await getRelay(request, headers, `/execution-records/${run.executionId}/nodes`);
      if (String(detail.workflowId) !== agent) throw new Error('Unexpected Relay workflow ID');
      for (const node of Object.values(detail.nodeWiseExecutionData || {})) {
        const link = node.output?.data;
        if (node.status === 'COMPLETED' && node.output?.success === true &&
            typeof node.input?.linkAmount === 'number' && link?.link_id && link?.link_url) {
          if (await archiveLink(link)) saved += 1;
          verified += 1;
        }
      }
      completedRuns.add(run.executionId);
    }
  }
  return { saved, verified };
}

async function main() {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9227', {
    timeout: 10_000, noDefaults: true,
  });
  try {
    const [context] = browser.contexts();
    if (!context) throw new Error('Open the signed-in Cashfree Playwright profile');
    let headers;
    do {
      try {
        headers ||= await relaySession(context);
        const result = await sync(context.request, headers);
        if (result.verified || !watch) console.log(JSON.stringify(result));
      } catch (error) {
        if (!watch) throw error;
        headers = undefined;
        console.error(`Retrying payment-link archive after ${error.name}`);
      }
      if (watch) await delay(20_000);
    } while (watch && browser.isConnected());
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(`Payment-link archive stopped: ${error.message}`);
  process.exitCode = 1;
});
