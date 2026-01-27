import { getJson, postJson } from '~/services/http';
import { simulateNetworkDelay, planFixture, invoicesFixture } from '../fixtures';
import type { PlanInfo, Invoice } from '../types';
import { getUserId } from '@features/Authentication/utils';
import { organizationsService } from './organizationsService';

const currentPlan: PlanInfo = { ...planFixture };
const currentInvoices: Invoice[] = invoicesFixture.map(i => ({ ...i }));

export const billingService = {
  async getPlan(): Promise<PlanInfo> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return currentPlan;
    }
    return getJson<PlanInfo>('/api/plan');
  },

  async getInvoices(): Promise<ReadonlyArray<Invoice>> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return currentInvoices;
    }
    return getJson<Invoice[]>('/api/invoices');
  },

  async openCustomerPortal(returnUrl: string): Promise<string> {
    const actingUserId = getUserId();
    const my = await organizationsService.listMine(actingUserId);
    const organizationId = my && my.length > 0 ? my[0].id : '';
    if (!organizationId) {
      throw new Error('Geen aktive organisatie gevonden');
    }
    const payload = {
      acting_user_id: actingUserId,
      organization_id: organizationId,
      return_url: returnUrl,
    };
    const res = await postJson<typeof payload, { status: string; url: string }>(
      '/billing/customer_portal',
      payload,
    );
    if (res.status !== 'success' || !res.url) {
      throw new Error('Kon klantportaal niet openen');
    }
    return res.url;
  },
};

export type BillingService = typeof billingService;
