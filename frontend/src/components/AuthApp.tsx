import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { Landmark, ArrowRight, ShieldCheck } from 'lucide-react'
import { Dashboard } from '@/App'
import { getSupabaseClient } from '@/lib/supabaseClient'
import { Button } from './ui/button'
import { Input } from './ui/input'

export function AuthApp() {
  const [session, setSession] = useState<Session | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [mode, setMode] = useState(() => window.location.hash === '#/signup' ? 'signup' : 'login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  useEffect(() => {
    const sync = () => { setMode(window.location.hash === '#/signup' ? 'signup' : 'login'); setError(''); setMessage(''); setPassword(''); setConfirmPassword('') }
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])
  useEffect(() => {
    let active = true
    setInitializing(true)
    const client = getSupabaseClient()
    if (!client) { setSession(null); setInitializing(false); return }
    const { data: { subscription } } = client.auth.onAuthStateChange((_event, next) => {
      if (active) { setSession(next); setInitializing(false) }
    })
    client.auth.getSession().then(({ data, error }) => {
      if (active) { setSession(data.session); setInitializing(false); if (error) setError(error.message) }
    }).catch(() => { if (active) { setError('Could not restore your session. Please sign in again.'); setInitializing(false) } })
    return () => { active = false; subscription.unsubscribe() }
  }, [])
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError(''); setMessage('')
    const client = getSupabaseClient()
    if (!client) { setError('Connect your Supabase project below to continue.'); return }
    if (mode === 'signup' && password !== confirmPassword) { setError('Passwords do not match.'); return }
    setBusy(true)
    try {
      if (mode === 'signup') {
        const { data, error } = await client.auth.signUp({ email: email.trim(), password, options: { data: { full_name: name.trim() }, emailRedirectTo: window.location.origin + window.location.pathname } })
        if (error) throw error
        if (!data.session) { setMessage('Check your email to confirm your account, then sign in.'); setPassword(''); setConfirmPassword('') }
      } else {
        const { error } = await client.auth.signInWithPassword({ email: email.trim(), password })
        if (error) throw error
      }
    } catch (error) { setError(error instanceof Error ? error.message : 'Unable to authenticate. Please try again.') }
    finally { setBusy(false) }
  }
  const signOut = async () => {
    const client = getSupabaseClient()
    if (!client) return
    const { error } = await client.auth.signOut()
    if (error) { window.alert(error.message); return }
    setSession(null); setPassword(''); window.location.hash = '/login'
  }
  if (initializing) return <div className="auth-loading" role="status">Loading your workspace…</div>
  if (session) return <Dashboard key={session.user.id} onSignOut={signOut} accountName={session.user.user_metadata.full_name || session.user.email || 'Your account'}/>
  const signup = mode === 'signup'
  return <main className="auth-page">
    <section className="auth-story"><div className="brand"><Landmark size={32}/><span>cashfree<span className="brand-period">.</span></span></div><div className="auth-story-content"><span className="auth-eyebrow">YOUR COLLECTIONS WORKSPACE</span><h1>Better conversations.<br/>Stronger collections.</h1><p>Bring every borrower, payment commitment, and follow-up together in one clear workspace.</p><div className="auth-assurance"><ShieldCheck size={21}/>Secure accounts. All amounts in Indian rupees.</div></div></section>
    <section className="auth-form-panel"><div className="auth-form-wrap"><span className="auth-eyebrow">LET’S GET STARTED</span><h2>{signup ? 'Create your account' : 'Welcome back'}</h2><p>{signup ? 'Your next step toward a clearer portfolio.' : 'Sign in to your collections workspace.'}</p>
      <form onSubmit={submit} className="auth-form">
        {signup && <label htmlFor="full-name">Full name<Input id="full-name" autoComplete="name" required maxLength={100} value={name} onChange={e => setName(e.target.value)} disabled={busy}/></label>}
        <label htmlFor="auth-email">Email address<Input id="auth-email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} disabled={busy}/></label>
        <label htmlFor="auth-password">Password<Input id="auth-password" type="password" autoComplete={signup ? 'new-password' : 'current-password'} required minLength={signup ? 8 : undefined} value={password} onChange={e => setPassword(e.target.value)} disabled={busy}/></label>
        {signup && <><small>Use at least 8 characters.</small><label htmlFor="confirm-password">Confirm password<Input id="confirm-password" type="password" autoComplete="new-password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} disabled={busy}/></label></>}
        {error && <div className="auth-error" role="alert">{error}</div>}{message && <div className="auth-message" role="status">{message}</div>}
        <Button type="submit" disabled={busy}>{busy ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}<ArrowRight size={17}/></Button>
      </form>
      <p className="auth-switch">{signup ? 'Already have an account?' : 'New to Cashfree?'} <a href={signup ? '#/login' : '#/signup'}>{signup ? 'Sign in' : 'Create an account'}</a></p>
    </div></section>
  </main>
}
