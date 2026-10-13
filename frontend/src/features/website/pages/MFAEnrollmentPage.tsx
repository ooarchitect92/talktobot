import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Brand } from '@/components/brand';
import { Button, Field } from '@/components/ui';
import { api, apiConfig } from '@/lib/api';
import type { MFASetupMaterial } from '@/lib/mfa-api';
import { clearEnrollmentPassword, clearPendingEnrollment, getEnrollmentPassword, getPendingEnrollment } from '@/lib/mfa-enrollment-state';
import { createQrAssets } from '@/lib/qr';
import type { Session } from '@/types';

export function MFAEnrollmentPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { from?: string } | null;
  const [enrollment] = useState(getPendingEnrollment);
  const [expired, setExpired] = useState(false);
  const [password, setPassword] = useState('');
  const [automaticPassword, setAutomaticPassword] = useState(getEnrollmentPassword);
  const automaticSetupStarted = useRef(false);
  const [material, setMaterial] = useState<MFASetupMaterial | null>(null);
  const [qr, setQr] = useState('');
  const [code, setCode] = useState('');
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!enrollment || !automaticPassword || automaticSetupStarted.current) return;
    automaticSetupStarted.current = true;
    clearEnrollmentPassword();
    setBusy(true);
    void fetch(`${apiConfig.baseUrl}/auth/mfa/setup`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${enrollment.enrollmentToken}` },
      body: JSON.stringify({ currentPassword: automaticPassword }),
    }).then(async response => {
      if (!response.ok) throw new Error('Unable to prepare your QR code. Verify your full sign-in password below or sign in again.');
      setMaterial(await response.json() as MFASetupMaterial);
    }).catch(reason => setError(reason instanceof Error ? reason.message : 'QR setup failed.'))
      .finally(() => { setAutomaticPassword(''); setBusy(false); });
  }, [enrollment, automaticPassword]);
  useEffect(() => {
    if (!material) return;
    let active = true;
    void createQrAssets(material.otpauthUri).then(value => { if (active) setQr(value.pngDataUrl); })
      .catch(() => { if (active) setError('QR code unavailable. Enter the setup key manually.'); });
    return () => { active = false; };
  }, [material]);
  useEffect(() => {
    if (!enrollment) return;
    const timer = window.setTimeout(() => { clearPendingEnrollment(); setExpired(true); }, Math.max(0, Date.parse(enrollment.expiresAt) - Date.now()));
    return () => window.clearTimeout(timer);
  }, [enrollment]);
  if (!enrollment || expired) return <Navigate to="/login" replace />;
  async function enrollmentRequest<T>(path: string, body: object): Promise<T> {
    const response = await fetch(`${apiConfig.baseUrl}/auth/mfa/${path}`, {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${enrollment!.enrollmentToken}` },
      body: JSON.stringify(body),
    });
    const value = await response.json();
    if (!response.ok) {
      if (response.status === 422) throw new Error('Enter your full sign-in password (at least eight characters). Then enter exactly six digits when confirming your authenticator.');
      throw new Error(value.error?.message || (typeof value.detail === 'string' ? value.detail : null) || 'Setup failed. Sign in again if your setup session expired.');
    }
    return value as T;
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      if (!material) {
        if (password.length < 8) throw new Error('Enter your full sign-in password, not an authenticator code.');
        setMaterial(await enrollmentRequest<MFASetupMaterial>('setup', { currentPassword: password }));
        setPassword('');
      } else {
        if (!saved || !/^\d{6}$/.test(code)) throw new Error('Check your recovery email and enter a six-digit code.');
        const session = await enrollmentRequest<Session>('confirm', { code });
        setMaterial(null); setQr('');
        api.auth.adopt(session);
        clearPendingEnrollment();
        const target = state?.from?.startsWith('/') && !state.from.startsWith('//') ? state.from : '/';
        navigate(session.user.emailVerified === false ? '/verify-email' : target, { replace: true });
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Authenticator setup failed.'); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-panel"><div className="login-panel__inner">
    <Brand /><h1>Set up your authenticator</h1>
    <p>Add TalkToBot to Google Authenticator or Microsoft Authenticator. Set up once, then enter a code when you sign in.</p>
    <form className="login-form" onSubmit={event => void submit(event)}>
      {!material ? <><Field label="Verify your sign-in password" htmlFor="enrollment-password"><input id="enrollment-password" type="password" autoComplete="current-password" required minLength={8} maxLength={256} value={password} onChange={event => setPassword(event.target.value)} /></Field><p>Enter the password you used to sign in. Your QR code appears after verification.</p></> : <>
        <p>In Google Authenticator, choose Add account → Scan a QR code. In Microsoft Authenticator, choose Add account → Other account → Scan a QR code.</p>
        {qr ? <img src={qr} alt="Scan to add TalkToBot to your authenticator" width={220} height={220} /> : <p role="status">Preparing your QR code. You can also use the manual setup key below.</p>}
        <p>Manual setup key: <code style={{ overflowWrap: 'anywhere' }}>{material.secret}</code></p>
        <p>Your recovery codes were sent to your account email. Check Inbox and Spam and keep them private.</p>
        <label><input type="checkbox" checked={saved} onChange={event => setSaved(event.target.checked)} /> I received my recovery codes by email.</label>
        <Field label="Six-digit authenticator code" htmlFor="enrollment-code"><input id="enrollment-code" inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" value={code} onChange={event => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} /></Field>
      </>}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <Button type="submit" disabled={busy || (!!material && !saved)}>{busy ? 'Please wait…' : material ? 'Confirm and continue' : 'Show authenticator QR code'}</Button>
    </form><Button type="button" variant="secondary" disabled={busy} onClick={() => {
      setBusy(true);
      void fetch(`${apiConfig.baseUrl}/auth/mfa/enrollment/logout`, {
        method: 'POST', credentials: 'include', headers: { Authorization: `Bearer ${enrollment.enrollmentToken}` },
      }).then(response => {
        if (!response.ok) throw new Error('Unable to cancel setup. Please retry.');
        clearPendingEnrollment(); setMaterial(null); setQr(''); navigate('/login', { replace: true, state: null });
      }).catch(reason => setError(reason instanceof Error ? reason.message : 'Cancellation failed'))
        .finally(() => setBusy(false));
    }}>Cancel and return to sign in</Button>
  </div></section></main>;
}
