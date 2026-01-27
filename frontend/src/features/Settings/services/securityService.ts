import http, { getJson, postJson, putJson, deleteJson } from '~/services/http';
import { simulateNetworkDelay, securitySettingsFixture } from '../fixtures';
import type { SecuritySettings } from '../types';

let settings: SecuritySettings = { ...securitySettingsFixture };

const BASE = '/api/security';

export const securityService = {
  async getSettings(): Promise<SecuritySettings> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return settings;
    }
    return getJson<SecuritySettings>(`${BASE}/settings`);
  },

  async updateSettings(payload: Partial<SecuritySettings>): Promise<SecuritySettings> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      settings = { ...settings, ...payload };
      return settings;
    }
    return putJson<Partial<SecuritySettings>, SecuritySettings>(`${BASE}/settings`, payload);
  },

  async testSAML(payload: {
    entityId?: string;
    acsUrl?: string;
    metadataUrl?: string;
  }): Promise<{ ok: boolean; message: string }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return { ok: true, message: 'Verbinding geslaagd (mock).' };
    }
    return postJson<typeof payload, { ok: boolean; message: string }>(`${BASE}/saml/test`, payload);
  },

  async exportMyData(): Promise<Blob> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const mock = { exportAt: new Date().toISOString(), items: securitySettingsFixture } as const;
      return new Blob([JSON.stringify(mock, null, 2)], { type: 'application/json' });
    }
    const res = await http.get(`${BASE}/export-data`, { responseType: 'blob' });
    return res.data as Blob;
  },

  async deleteMyData(): Promise<{ ok: boolean }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return { ok: true };
    }
    return deleteJson<{ ok: boolean }>(`${BASE}/delete-data`);
  },
};
export type SecurityService = typeof securityService;
