import type {
  OrgProfile,
  Member,
  PlanInfo,
  UsageMetric,
  UserUsageData,
  ThresholdSettings,
  Invoice,
  SecuritySettings,
  EmailDomainVerification,
  Webhook,
  SlackIntegration,
  TeamsIntegration,
  AuditLogEntry,
  User,
} from '../types';

export const orgFixture: OrgProfile = {
  id: 'org_0001',
  name: 'Exactify B.V.',
  vatNumber: 'NL123456789B01',
  billingAddress: 'Keizersgracht 1, 1015 CJ Amsterdam',
};

export const membersFixture: ReadonlyArray<Member> = [
  {
    id: 'mem_0001',
    name: 'Jan Jansen',
    email: 'jan.jansen@example.nl',
    role: 'owner',
    invitedAt: '2025-01-10T09:15:00Z',
    lastActiveAt: '2025-09-15T11:00:00Z',
  },
  {
    id: 'mem_0002',
    name: 'Sanne de Vries',
    email: 'sanne.vries@example.nl',
    role: 'admin',
    invitedAt: '2025-02-05T12:00:00Z',
    lastActiveAt: '2025-09-14T15:30:00Z',
  },
  {
    id: 'mem_0003',
    name: 'Karel Bakker',
    email: 'karel.bakker@example.nl',
    role: 'member',
    invitedAt: '2025-03-20T08:45:00Z',
    lastActiveAt: '2025-09-12T10:05:00Z',
  },
];

export const planFixture: PlanInfo = {
  tier: 'pro',
  pricePerMonthCents: 4900,
  nextRenewalDate: '2025-10-01T00:00:00Z',
  currency: 'EUR',
  features: ['websearch', 'beta', 'priority-support'],
};

export const usageFixture: ReadonlyArray<UsageMetric> = [
  { metric: 'messages', period: 'month', used: 2150, limit: 3000, forecast: 2900, unit: 'count' },
  { metric: 'attachments', period: 'month', used: 480, limit: 1000, forecast: 820, unit: 'count' },
  { metric: 'seats', period: 'month', used: 12, limit: 15, forecast: 12, unit: 'count' },
];

export const perUserUsageFixture: ReadonlyArray<UserUsageData> = [
  {
    userId: 'user_001',
    userName: 'Jan Jansen',
    userEmail: 'jan.jansen@example.nl',
    messagesSent: 45,
    tokensUsed: 12500,
    attachmentsUploaded: 8,
    lastActivityDate: '2025-09-15T11:00:00Z',
  },
  {
    userId: 'user_002',
    userName: 'Sanne de Vries',
    userEmail: 'sanne.vries@example.nl',
    messagesSent: 32,
    tokensUsed: 8900,
    attachmentsUploaded: 5,
    lastActivityDate: '2025-09-14T15:30:00Z',
  },
  {
    userId: 'user_003',
    userName: 'Karel Bakker',
    userEmail: 'karel.bakker@example.nl',
    messagesSent: 28,
    tokensUsed: 7200,
    attachmentsUploaded: 3,
    lastActivityDate: '2025-09-12T10:05:00Z',
  },
  {
    userId: 'user_004',
    userName: 'Lisa van der Berg',
    userEmail: 'lisa.berg@example.nl',
    messagesSent: 67,
    tokensUsed: 18900,
    attachmentsUploaded: 12,
    lastActivityDate: '2025-09-16T09:20:00Z',
  },
  {
    userId: 'user_005',
    userName: 'Tom de Wit',
    userEmail: 'tom.wit@example.nl',
    messagesSent: 19,
    tokensUsed: 4800,
    attachmentsUploaded: 2,
    lastActivityDate: '2025-09-10T14:45:00Z',
  },
];

export const thresholdSettingsFixture: ThresholdSettings = {
  messages: 80,
  attachments: 70,
  tokens: 90,
};

export const userFixture: User = {
  id: 'user_001',
  email: 'admin@example.nl',
  name: 'Jan Jansen',
  role: 'admin',
  avatarUrl: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Jan',
  lastLoginAt: '2025-01-15T10:30:00Z',
};

export const invoicesFixture: ReadonlyArray<Invoice> = [
  {
    id: 'inv_2025_08',
    date: '2025-08-01T00:00:00Z',
    amountCents: 4900,
    currency: 'EUR',
    status: 'paid',
    url: 'https://billing.example.com/invoices/inv_2025_08.pdf',
  },
  {
    id: 'inv_2025_09',
    date: '2025-09-01T00:00:00Z',
    amountCents: 4900,
    currency: 'EUR',
    status: 'open',
    url: 'https://billing.example.com/invoices/inv_2025_09.pdf',
  },
];

export const securitySettingsFixture: SecuritySettings = {
  twoFactorEnabled: true,
  dataResidency: 'eu',
  samlEnabled: false,
  saml: undefined,
};

export const emailDomainVerificationFixture: EmailDomainVerification = {
  domain: 'example.nl',
  status: 'pending',
  txtName: 'ai4accountancy._domainkey',
  txtValue: 'v=DKIM1; k=rsa; p=MIIBIjANBgkqh...',
};

export const webhooksFixture: ReadonlyArray<Webhook> = [
  {
    id: 'wh_0001',
    url: 'https://hooks.example.com/ai4accountancy',
    events: ['message.created', 'message.completed'],
    secretMasked: 'sk_****1234',
  },
];

export const slackIntegrationFixture: SlackIntegration = {
  connected: true,
  teamName: 'Exactify',
  defaultChannel: '#facturatie',
};

export const teamsIntegrationFixture: TeamsIntegration = {
  connected: false,
  teamName: undefined,
  defaultChannel: undefined,
};

export const auditLogsFixture: ReadonlyArray<AuditLogEntry> = [
  {
    id: 'log_0001',
    timestamp: '2025-09-10T09:00:00Z',
    actorEmail: 'jan.jansen@example.nl',
    action: 'role.changed',
    target: 'mem_0003',
    metadata: { role: 'member->admin' },
  },
  {
    id: 'log_0002',
    timestamp: '2025-09-12T14:20:00Z',
    actorEmail: 'sanne.vries@example.nl',
    action: 'org.updated',
    target: 'org_0001',
    metadata: { field: 'billingAddress' },
  },
];

export async function simulateNetworkDelay(ms: number = 400): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, ms));
}
