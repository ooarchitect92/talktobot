import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules(); localStorage.clear(); });

describe('production session boundary', () => {
  it('authenticates organization and CRM reads using memory without persisting credentials', async () => {
    vi.stubEnv('PROD', true);
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.resetModules();
    const storage = await import('@/lib/storage');
    const { apiConfig } = await import('@/lib/api');
    expect(apiConfig.demoMode).toBe(false);
    const session = { accessToken: 'synthetic-access', expiresAt: '2026-10-12T00:00:00Z', user: { id: 'owner-1', name: 'Owner', email: 'owner@example.com', role: 'owner', emailVerified: true } };
    localStorage.setItem('northstar.session', JSON.stringify({ accessToken: 'legacy-access' }));
    storage.writeStorage('northstar.session', session);
    expect(localStorage.getItem('northstar.session')).toBeNull();
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (url) => new Response(
      JSON.stringify(String(url).includes('/me/organizations') ? { organizations: [], nextCursor: null } : []),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ));
    vi.stubGlobal('fetch', fetchMock);
    const { organizationApi } = await import('@/lib/organization-api');
    const { crmOneClickApi } = await import('@/lib/crm-one-click-api');
    const { leadCrmApi } = await import('@/lib/lead-crm-api');
    await organizationApi.list();
    await crmOneClickApi.providers();
    await leadCrmApi.connections();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const [, options] of fetchMock.mock.calls) {
      expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer synthetic-access');
    }
    expect(localStorage.getItem('northstar.session')).toBeNull();
    storage.removeStorage('northstar.session');
    await expect(organizationApi.list()).rejects.toThrow('Sign in');
  });
});
