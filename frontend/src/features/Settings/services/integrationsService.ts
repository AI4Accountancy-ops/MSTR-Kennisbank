import { getJson, postJson, putJson, deleteJson } from '~/services/http';
import {
  simulateNetworkDelay,
  emailDomainVerificationFixture,
  webhooksFixture,
  slackIntegrationFixture,
  teamsIntegrationFixture,
} from '../fixtures';
import type {
  EmailDomainVerification,
  Webhook,
  SlackIntegration,
  TeamsIntegration,
} from '../types';

let emailDomain: EmailDomainVerification = { ...emailDomainVerificationFixture };
let webhooks: Webhook[] = webhooksFixture.map(w => ({ ...w }));
let slack: SlackIntegration = { ...slackIntegrationFixture };
let teams: TeamsIntegration = { ...teamsIntegrationFixture };

export const integrationsService = {
  // Email Domain
  async getEmailDomain(): Promise<EmailDomainVerification> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return emailDomain;
    }
    return getJson<EmailDomainVerification>('/api/integrations/email-domain');
  },
  async startDomainVerification(domain: string): Promise<EmailDomainVerification> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      emailDomain = { domain, status: 'pending', txtName: 'verify', txtValue: 'abc123' };
      return emailDomain;
    }
    return postJson<{ domain: string }, EmailDomainVerification>(
      '/api/integrations/email-domain/start',
      { domain },
    );
  },

  // Webhooks
  async getWebhooks(): Promise<ReadonlyArray<Webhook>> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return webhooks;
    }
    return getJson<Webhook[]>('/api/integrations/webhooks');
  },
  async createWebhook(payload: Omit<Webhook, 'id' | 'secretMasked'>): Promise<Webhook> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const created: Webhook = {
        id: `wh_${Math.random().toString(36).slice(2, 8)}`,
        secretMasked: 'sk_****9999',
        ...payload,
      };
      webhooks = [...webhooks, created];
      return created;
    }
    return postJson<typeof payload, Webhook>('/api/integrations/webhooks', payload);
  },
  async updateWebhook(id: string, payload: Partial<Webhook>): Promise<Webhook> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const idx = webhooks.findIndex(w => w.id === id);
      if (idx >= 0) {
        webhooks[idx] = { ...webhooks[idx], ...payload };
        return webhooks[idx];
      }
      throw new Error('Webhook niet gevonden');
    }
    return putJson<Partial<Webhook>, Webhook>(`/api/integrations/webhooks/${id}`, payload);
  },
  async deleteWebhook(id: string): Promise<{ removed: true }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      webhooks = webhooks.filter(w => w.id !== id);
      return { removed: true } as const;
    }
    return deleteJson<{ removed: true }>(`/api/integrations/webhooks/${id}`);
  },
  async testWebhook(id: string): Promise<{ ok: true }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return { ok: true } as const;
    }
    return postJson<undefined, { ok: true }>(
      `/api/integrations/webhooks/${id}/test`,
      undefined as unknown as undefined,
    );
  },

  // Slack
  async getSlack(): Promise<SlackIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return slack;
    }
    return getJson<SlackIntegration>('/api/integrations/slack');
  },
  async connectSlack(): Promise<SlackIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      slack = { connected: true, teamName: 'Exactify', defaultChannel: '#algemeen' };
      return slack;
    }
    return postJson<undefined, SlackIntegration>(
      '/api/integrations/slack/connect',
      undefined as unknown as undefined,
    );
  },
  async disconnectSlack(): Promise<SlackIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      slack = { connected: false };
      return slack;
    }
    return postJson<undefined, SlackIntegration>(
      '/api/integrations/slack/disconnect',
      undefined as unknown as undefined,
    );
  },

  // Teams
  async getTeams(): Promise<TeamsIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return teams;
    }
    return getJson<TeamsIntegration>('/api/integrations/teams');
  },
  async connectTeams(): Promise<TeamsIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      teams = { connected: true, teamName: 'Exactify', defaultChannel: 'Algemeen' };
      return teams;
    }
    return postJson<undefined, TeamsIntegration>(
      '/api/integrations/teams/connect',
      undefined as unknown as undefined,
    );
  },
  async disconnectTeams(): Promise<TeamsIntegration> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      teams = { connected: false };
      return teams;
    }
    return postJson<undefined, TeamsIntegration>(
      '/api/integrations/teams/disconnect',
      undefined as unknown as undefined,
    );
  },
};

export type IntegrationsService = typeof integrationsService;
