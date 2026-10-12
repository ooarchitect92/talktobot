import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MFAEnrollmentPage } from './MFAEnrollmentPage';

const mocks = vi.hoisted(() => ({ fetch: vi.fn(), qr: vi.fn(), password: '' }));
vi.mock('@/components/brand', () => ({ Brand: () => <span>TalkToBot</span> }));
vi.mock('@/lib/api', () => ({ api: { auth: { adopt: vi.fn() } }, apiConfig: { baseUrl: '/api/v1' } }));
vi.mock('@/lib/qr', () => ({ createQrAssets: mocks.qr }));
vi.mock('@/lib/mfa-enrollment-state', () => ({
  getPendingEnrollment: () => ({ enrollmentToken: 'restricted-enrollment', expiresAt: new Date(Date.now() + 600000).toISOString() }),
  clearPendingEnrollment: vi.fn(),
  getEnrollmentPassword: () => mocks.password,
  clearEnrollmentPassword: vi.fn(),
}));
beforeEach(() => { vi.stubGlobal('fetch', mocks.fetch); mocks.fetch.mockReset(); mocks.qr.mockReset(); mocks.password = ''; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('shows an actionable validation error without exposing request inputs', async () => {
  mocks.fetch.mockResolvedValue(new Response(JSON.stringify({ error: { message: 'Request validation failed' } }), { status: 422 }));
  const user = userEvent.setup();
  render(<MemoryRouter><MFAEnrollmentPage /></MemoryRouter>);
  await user.type(screen.getByLabelText('Verify your sign-in password'), 'Password-2026!');
  await user.click(screen.getByRole('button', { name: 'Show authenticator QR code' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Enter your full sign-in password');
});

it('renders a scannable QR code and requires recovery-code acknowledgement before confirmation', async () => {
  const uri = 'otpauth://totp/TalkToBot:test?secret=JBSWY3DPEHPK3PXP&issuer=TalkToBot';
  mocks.fetch.mockResolvedValue(new Response(JSON.stringify({ secret: 'JBSWY3DPEHPK3PXP', otpauthUri: uri, recoveryCodes: ['TEST-CODE-ONLY'] }), { status: 200 }));
  mocks.qr.mockResolvedValue({ pngDataUrl: 'data:image/png;base64,qr' });
  const user = userEvent.setup();
  render(<MemoryRouter><MFAEnrollmentPage /></MemoryRouter>);
  await user.type(screen.getByLabelText('Verify your sign-in password'), 'Password-2026!');
  await user.click(screen.getByRole('button', { name: 'Show authenticator QR code' }));
  expect(await screen.findByAltText('Scan to add TalkToBot to your authenticator')).toHaveAttribute('src', 'data:image/png;base64,qr');
  expect(mocks.qr).toHaveBeenCalledWith(uri);
  expect(screen.getByRole('button', { name: 'Confirm and continue' })).toBeDisabled();
  await user.click(screen.getByLabelText('I saved my recovery codes.'));
  expect(screen.getByRole('button', { name: 'Confirm and continue' })).toBeEnabled();
});

it('automatically shows the QR after password login without asking for the password again', async () => {
  mocks.password = 'Recent-sign-in-password';
  mocks.fetch.mockResolvedValue(new Response(JSON.stringify({ secret: 'JBSWY3DPEHPK3PXP', otpauthUri: 'otpauth://totp/TalkToBot', recoveryCodes: ['TEST-CODE-ONLY'] }), { status: 200 }));
  mocks.qr.mockResolvedValue({ pngDataUrl: 'data:image/png;base64,qr' });
  render(<MemoryRouter><MFAEnrollmentPage /></MemoryRouter>);
  expect(await screen.findByAltText('Scan to add TalkToBot to your authenticator')).toBeInTheDocument();
  expect(screen.queryByLabelText('Verify your sign-in password')).not.toBeInTheDocument();
  expect(mocks.fetch).toHaveBeenCalledTimes(1);
});
