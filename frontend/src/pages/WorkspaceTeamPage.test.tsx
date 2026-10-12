import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { WorkspacePage } from '@/pages/WorkspacePage';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  getTeam: vi.fn(),
  inviteMember: vi.fn(),
  update: vi.fn(),
  pushToast: vi.fn(),
  listMembers: vi.fn(),
  listInvitations: vi.fn(),
  invite: vi.fn(),
  listAgents: vi.fn(),
}));

vi.mock('@/components/providers', () => ({
  useOptionalWorkspace: () => null,
  useAuth: () => ({
    session: {
      accessToken: 'access-token',
      expiresAt: '2026-09-11T00:00:00Z',
      user: {
        id: 'owner-user',
        name: 'Workspace Owner',
        email: 'owner@example.com',
        role: 'owner',
        emailVerified: true,
      },
    },
  }),
  useToast: () => ({ pushToast: mocks.pushToast }),
}));

vi.mock('@/lib/workspace-api', () => ({
  workspacePresentationKey: () => 'owner-user:workspace-1',
  workspaceApi: {
    get: mocks.get,
    getTeam: mocks.getTeam,
    inviteMember: mocks.inviteMember,
    update: mocks.update,
  },
}));

vi.mock('@/lib/api', () => ({ api: { agents: { list: mocks.listAgents } } }));
vi.mock('@/lib/workspace-team-api', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/lib/workspace-team-api')>(),
  workspaceTeamApi: {
    listMembers: mocks.listMembers,
    listInvitations: mocks.listInvitations,
    invite: mocks.invite,
  },
}));

const workspace = {
  id: 'workspace-1',
  name: 'Northstar Workspace',
  slug: 'northstar',
  plan: 'business',
  memberCount: 1,
  permissions: ['members.view', 'members.manage', 'members.invite'],
  preferences: { timezone: 'Asia/Calcutta', defaultLanguage: 'English', dateFormat: 'DD/MM/YYYY' as const },
  whiteLabel: {
    companyName: 'Northstar AI', logoDataUrl: '', faviconDataUrl: '', appIconDataUrl: '',
    primaryColor: '#146cf6', secondaryColor: '#705cf6', supportEmail: 'support@northstar.ai',
    supportUrl: 'https://northstar.ai/support', browserTitle: 'Northstar AI', customDomain: '',
    dnsStatus: 'not-configured' as const, brandedLogin: true, brandedDashboard: true, brandedWidget: true,
    brandedEmails: true, removePlatformBranding: false,
  },
};

const initialTeam = {
  members: [{
    id: 'owner-user',
    name: 'Workspace Owner',
    email: 'owner@example.com',
    role: 'workspace_admin' as const,
    tenantRole: 'owner' as const,
    status: 'active' as const,
  }],
  invitations: [],
};

describe('Workspace team section', () => {
  beforeEach(() => {
    mocks.listMembers.mockResolvedValue([{ userId: 'owner-user', name: 'Workspace Owner', email: 'owner@example.com', role: 'workspace_admin', allAgentsAccess: true, agentIds: [], isSelf: true, joinedAt: '2026-10-12T00:00:00Z' }]);
    mocks.listInvitations.mockResolvedValue([]);
    mocks.listAgents.mockResolvedValue([]);
    mocks.invite.mockResolvedValue({ id: 'invite-1', email: 'analyst@example.com', role: 'analyst', status: 'pending', allAgentsAccess: true, agentIds: [], deliveryState: 'sent', createdAt: '2026-10-12T00:00:00Z', expiresAt: '2026-10-19T00:00:00Z' });
    mocks.get.mockResolvedValue(workspace);
    mocks.getTeam.mockResolvedValue(initialTeam);
    mocks.inviteMember.mockResolvedValue({
      ...initialTeam,
      invitations: [{
        id: 'invite-1',
        email: 'analyst@example.com',
        role: 'analyst',
        status: 'invited',
        createdAt: '2026-09-10T10:00:00Z',
        expiresAt: '2026-09-17T10:00:00Z',
      }],
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('loads the server team and sends invitations through the workspace API', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={['/?section=team']}><WorkspacePage /></MemoryRouter>);

    expect(await screen.findByText('Workspace Owner (you)')).toBeInTheDocument();
    expect(mocks.listMembers).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'Invite member' }));
    await user.type(screen.getByLabelText('Email address'), 'ANALYST@EXAMPLE.COM');
    await user.selectOptions(screen.getByLabelText('Workspace role'), 'analyst');
    await user.click(screen.getByRole('button', { name: 'Send invitation' }));

    await waitFor(() => expect(mocks.invite).toHaveBeenCalledWith({ email: 'analyst@example.com', role: 'analyst', allAgentsAccess: true, agentIds: [] }));
    expect(await screen.findByText('analyst@example.com')).toBeInTheDocument();
    expect(mocks.pushToast).toHaveBeenCalledWith('Invitation sent to analyst@example.com', 'success');
  });
});
