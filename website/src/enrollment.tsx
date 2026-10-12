import QRCode from 'qrcode';
import { useState, type FormEvent } from 'react';
import { api } from './api';

export interface Enrollment { enrollmentToken: string; expiresAt: string }
interface Material { secret: string; otpauthUri: string; recoveryCodes: string[] }
export function AuthenticatorEnrollment({ enrollment, onComplete, onCancel }: {
  enrollment: Enrollment; onComplete: (token: string) => Promise<void>; onCancel: () => void;
}) {
  const [material, setMaterial] = useState<Material | null>(null);
  const [qr, setQr] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const fields = new FormData(event.currentTarget);
    try {
      if (Date.parse(enrollment.expiresAt) <= Date.now()) throw new Error('Setup session expired. Cancel and sign in again.');
      const headers = { Authorization: `Bearer ${enrollment.enrollmentToken}` };
      if (!material) {
        const password = String(fields.get('password') || '');
        if (password.length < 8) throw new Error('Enter your full sign-in password, not an authenticator code.');
        const next = await api<Material>('/auth/mfa/setup', { method: 'POST', headers, body: JSON.stringify({ currentPassword: password }) });
        setMaterial(next);
        try { setQr(await QRCode.toDataURL(next.otpauthUri, { width: 240, margin: 4 })); }
        catch { setError('QR unavailable. Enter the setup key manually.'); }
      } else {
        if (!saved) throw new Error('Save your recovery codes first.');
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
    {!material ? <><label>Verify your sign-in password<input type="password" name="password" autoComplete="current-password" minLength={8} maxLength={256} required /></label><p>Enter your sign-in password. Your QR code appears after verification.</p></> : <>
      <p>In Google Authenticator, choose Add account → Scan a QR code. In Microsoft Authenticator, choose Add account → Other account → Scan a QR code.</p>
      {qr ? <img src={qr} alt="Scan to add TalkToBot to your authenticator" width={240} height={240} /> : null}
      <p style={{ overflowWrap: 'anywhere' }}>Manual setup key: <code>{material.secret}</code></p>
      <p>Save these ten recovery codes outside this browser. Each works once.</p>
      {material.recoveryCodes.map(value => <div key={value}><code>{value}</code></div>)}
      <button type="button" className="button" onClick={() => void navigator.clipboard.writeText(material.recoveryCodes.join('\n')).catch(() => setError('Copy unavailable. Save the codes manually.'))}>Copy recovery codes</button>
      <label><input type="checkbox" checked={saved} onChange={event => setSaved(event.target.checked)} /> I saved my recovery codes.</label>
      <label>Six-digit code<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>
    </>}
    {error ? <p className="error-message" role="alert">{error}</p> : null}
    <button className="button dark" disabled={busy || (!!material && !saved)}>{busy ? 'Please wait…' : material ? 'Confirm and continue' : 'Show authenticator QR code'}</button>
    <button type="button" className="text-link" disabled={busy} onClick={() => {
      setBusy(true);
      void api('/auth/mfa/enrollment/logout', { method: 'POST', headers: { Authorization: `Bearer ${enrollment.enrollmentToken}` } })
        .then(onCancel).catch(reason => setError(reason instanceof Error ? reason.message : 'Cancellation failed'))
        .finally(() => setBusy(false));
    }}>Cancel setup</button>
  </form>;
}
