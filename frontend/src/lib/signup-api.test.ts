import { afterEach, describe, expect, it, vi } from 'vitest';
import { signupApi, type SignupInput } from '@/lib/signup-api';

const input: SignupInput = {
  name: 'Signup Owner',
  email: 'owner@example.com',
  password: 'Signup-Password-2026!',
  organizationName: 'NorthStar Academy',
  termsAccepted: true,
  privacyAccepted: true,
};

const serverSession = {
  accessToken: 'access-token',
  refreshToken: 'refresh-token-must-not-persist',
  expiresAt: '2026-09-11T00:00:00.000Z',
  user: {
    id: 'user-1',
    name: 'Signup Owner',
    email: 'owner@example.com',
    role: 'owner' as const,
    emailVerified: false,
  },
};

describe('signupApi', () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it('persists a successful backend session without exposing the refresh token to storage', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(serverSession), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    })));

    const session = await signupApi.signup(input);
    if (isMFAEnrollment(session)) throw new Error('Unexpected enrollment challenge');

    expect(session.refreshToken).toBeUndefined();
    expect(session.user.emailVerified).toBe(false);
    const persisted = JSON.parse(localStorage.getItem('northstar.session') ?? '{}') as Record<string, unknown>;
    expect(persisted.accessToken).toBe('access-token');
    expect(persisted.refreshToken).toBeUndefined();
  });

  it('surfaces an actionable duplicate-account response instead of falling back to demo mode', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { message: 'An account with this email already exists' },
    }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    })));

    await expect(signupApi.signup(input)).rejects.toThrow('An account with this email already exists');
    expect(localStorage.getItem('northstar.session')).toBeNull();
  });

  it('fails closed when the production-connected API is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    await expect(signupApi.signup(input)).rejects.toThrow('offline');
    expect(localStorage.getItem('northstar.session')).toBeNull();
  });
});
import { isMFAEnrollment } from '@/lib/mfa-api';
