import QRCode from 'qrcode';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from './api';

export interface Enrollment { enrollmentToken: string; expiresAt: string }
interface Material { secret: string; otpauthUri: string; recoveryCodesEmailed: boolean }
export function AuthenticatorEnrollment({ enrollment, initialPassword = '', onPasswordConsumed, onComplete, onCancel }: {
  enrollment: Enrollment; onComplete: (token: string) => Promise<void>; onCancel: () => void;
  initialPassword?: string; onPasswordConsumed?: () => void;
}) {
  const [material, setMaterial] = useState<Material | null>(null);
  const [qr, setQr] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const automaticPassword = useRef(initialPassword);
  async function prepare(password: string) {
    if (!Number.isFinite(Date.parse(enrollment.expiresAt)) || Date.parse(enrollment.expiresAt) <= Date.now()) throw new Error('Setup session expired. Cancel and sign in again.');
    if (password.length < 8) throw new Error('Enter your full sign-in password, not an authenticator code.');
    const next = await api<Material>('/auth/mfa/setup', {
      method: 'POST', headers: { Authorization: `Bearer ${enrollment.enrollmentToken}` },
      body: JSON.stringify({ currentPassword: password }),
    });
    setMaterial(next);
    try { setQr(await QRCode.toDataURL(next.otpauthUri, { width: 240, margin: 4 })); }
    catch { setError('QR unavailable. Enter the setup key manually.'); }
  }
  useEffect(() => {
    // Use the password just verified by login once, in memory only. Clearing
    // the ref before starting also prevents duplicate setup in StrictMode.
    const password = automaticPassword.current;
    if (!password) return;
    automaticPassword.current = '';
    onPasswordConsumed?.();
    setBusy(true); setError('');
    void prepare(password).catch(reason => setError(reason instanceof Error ? reason.message : 'Setup failed'))
      .finally(() => setBusy(false));
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const fields = new FormData(event.currentTarget);
    try {
      if (Date.parse(enrollment.expiresAt) <= Date.now()) throw new Error('Setup session expired. Cancel and sign in again.');
      const headers = { Authorization: `Bearer ${enrollment.enrollmentToken}` };
      if (!material) {
        const password = String(fields.get('password') || '');
        await prepare(password);
      } else {
        if (!saved) throw new Error('Confirm that you received the recovery email first.');
        const session = await api<{ accessToken: string }>('/auth/mfa/confirm', { method: 'POST', headers, body: JSON.stringify({ code: fields.get('code') }) });
        setMaterial(null); setQr('');
        await onComplete(session.accessToken);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Setup failed'); }
    finally { setBusy(false); }
  }
  return <form onSubmit={event => void submit(event)}>
    <h2>Set up your authenticator</h2>
    <p>Use Google Authenticator or Microsoft Authenticator. Setup is required once; future sign-ins need a code.</p>
    {!material ? busy ? <p role="status">Preparing your authenticator QR code…</p> : <><label>Verify your sign-in password<input type="password" name="password" autoComplete="current-password" maxLength={256} required /></label><p>Enter your full sign-in password. Your QR code appears after verification.</p></> : <>
      <p>In Google Authenticator, choose Add account → Scan a QR code. In Microsoft Authenticator, choose Add account → Other account → Scan a QR code.</p>
      {qr ? <img src={qr} alt="Scan to add TalkToBot to your authenticator" width={240} height={240} /> : <p role="status">Preparing your QR code. You can also use the manual setup key below.</p>}
      <p style={{ overflowWrap: 'anywhere' }}>Manual setup key: <code>{material.secret}</code></p>
        <p>Your recovery codes were sent to your account email. Check Inbox and Spam and keep them private.</p>
        <label><input type="checkbox" checked={saved} onChange={event => setSaved(event.target.checked)} /> I received my recovery codes by email.</label>
      <label>Six-digit code<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
    </>}
    {error ? <p className="error-message" role="alert">{error}</p> : null}
    <button className="button dark" disabled={busy || (!!material && !saved)}>{busy ? 'Please wait…' : material ? 'Verify code and finish setup' : 'Show authenticator QR code'}</button>
    <button type="button" className="text-link" disabled={busy} onClick={() => {
      setBusy(true);
      void api('/auth/mfa/enrollment/logout', { method: 'POST', headers: { Authorization: `Bearer ${enrollment.enrollmentToken}` } })
        .then(onCancel).catch(reason => setError(reason instanceof Error ? reason.message : 'Cancellation failed'))
        .finally(() => setBusy(false));
    }}>Cancel setup</button>
  </form>;
}
