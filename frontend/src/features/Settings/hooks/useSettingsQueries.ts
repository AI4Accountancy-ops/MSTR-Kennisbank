import { useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '~/context/ToastContext';
import { extractErrorMessage } from '../utils/error';
// orgService replaced by organizationsService-backed hooks
import { organizationsService } from '../services/organizationsService';
import { getUserId } from '@features/Authentication/utils';
import { billingService } from '../services/billingService';
import { usageService } from '../services/usageService';
import { securityService } from '../services/securityService';
import { integrationsService } from '../services/integrationsService';
import { auditService } from '../services/auditService';
import type { Invoice, InvoiceStatus, UsagePeriod } from '../types';

export function useOrg() {
  const { showToast } = useToast();
  const { data: myOrgs } = useMyOrganizations();
  const orgId = myOrgs && myOrgs.length > 0 ? myOrgs[0].id : '';
  const org = useQuery({
    queryKey: ['org', orgId],
    queryFn: () => organizationsService.getOrganization(orgId),
    enabled: orgId.length > 0,
  });
  // Update via legacy endpoint not available; if needed, wire a backend update route later
  const updateOrg = useMutation({
    mutationFn: async () => org.data,
    onSuccess: data => {
      if (data) useQueryClient().setQueryData(['org', orgId], data);
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  return { org, updateOrg };
}

export function useMembers() {
  const { showToast } = useToast();
  // Backend-integrated members: load via organization details
  const { data: myOrgs } = useMyOrganizations();
  const orgId = myOrgs && myOrgs.length > 0 ? myOrgs[0].id : '';

  const list = useQuery({
    queryKey: ['members', orgId],
    queryFn: async () => {
      if (!orgId) return [] as { id: string; role: 'admin' | 'user' }[];
      const org = await organizationsService.getOrganization(orgId);
      return (org.members ?? []).map(m => ({ id: m.user_id, role: m.role }));
    },
    enabled: orgId.length > 0,
  });

  const invite = useMutation({
    mutationFn: async (userId: string) => {
      const actingUserId = getUserId();
      return organizationsService.addMember(orgId, actingUserId, userId, 'user');
    },
    onSuccess: () => useQueryClient().invalidateQueries({ queryKey: ['members', orgId] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  const changeRole = useMutation({
    mutationFn: async ({ memberId, role }: { memberId: string; role: 'admin' | 'user' }) => {
      const actingUserId = getUserId();
      return organizationsService.updateMemberRole(orgId, actingUserId, memberId, role);
    },
    onSuccess: () => useQueryClient().invalidateQueries({ queryKey: ['members', orgId] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  const remove = useMutation({
    mutationFn: async (memberId: string) => {
      const actingUserId = getUserId();
      return organizationsService.removeMember(orgId, actingUserId, memberId);
    },
    onSuccess: () => useQueryClient().invalidateQueries({ queryKey: ['members', orgId] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  // Not used with backend-based flow
  const regenerateInvite = useMutation({
    mutationFn: async (_memberId: string) => ({
      memberId: _memberId,
      invitedAt: new Date().toISOString(),
    }),
  });

  return { list, invite, regenerateInvite, changeRole, remove };
}

export function usePlan() {
  const plan = useQuery({ queryKey: ['plan'], queryFn: billingService.getPlan });
  const { data: myOrgs } = useMyOrganizations();
  const orgId = myOrgs && myOrgs.length > 0 ? myOrgs[0].id : '';
  const currentOrg = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsService.getOrganization(orgId),
    enabled: orgId.length > 0,
  });
  const invoices = useQuery({ queryKey: ['invoices'], queryFn: billingService.getInvoices });
  return { plan, invoices, currentOrg };
}

export function useUsage() {
  const usage = useQuery({ queryKey: ['usage'], queryFn: usageService.getUsage });
  return { usage };
}

export function usePerUserUsage(period: UsagePeriod) {
  const perUserUsage = useQuery({
    queryKey: ['perUserUsage', period],
    queryFn: () => usageService.getPerUserUsage(period),
  });
  return { perUserUsage };
}

export function useThresholdSettings() {
  const { showToast } = useToast();
  const qc = useQueryClient();
  const thresholds = useQuery({
    queryKey: ['thresholdSettings'],
    queryFn: usageService.getThresholdSettings,
  });
  const update = useMutation({
    mutationFn: usageService.updateThresholdSettings,
    onSuccess: data => {
      qc.setQueryData(['thresholdSettings'], data);
      showToast('Waarschuwingsdrempels bijgewerkt', 'success');
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  return { thresholds, update };
}

/**
 * Standalone plan query hook (without coupled mutations).
 */
export function usePlanQuery() {
  return useQuery({ queryKey: ['plan'], queryFn: billingService.getPlan });
}

/**
 * Invoices hook with client-side sort/filter/search + pagination.
 */
export function useInvoices(options?: {
  page?: number;
  pageSize?: number;
  sortBy?: 'date' | 'amount' | 'status';
  sortDir?: 'asc' | 'desc';
  status?: InvoiceStatus | 'all';
  search?: string;
}) {
  const query = useQuery({ queryKey: ['invoices'], queryFn: billingService.getInvoices });
  const page = options?.page ?? 1;
  const pageSize = options?.pageSize ?? 10;
  const sortBy = options?.sortBy ?? 'date';
  const sortDir = options?.sortDir ?? 'desc';
  const status = options?.status ?? 'all';
  const search = (options?.search ?? '').trim().toLowerCase();

  const processed = useMemo<ReadonlyArray<Invoice>>(() => {
    const base = (query.data ?? []).filter(inv => {
      const statusOk = status === 'all' ? true : inv.status === status;
      if (!statusOk) return false;
      if (search.length === 0) return true;
      const hay = `${inv.id} ${inv.currency} ${inv.status}`.toLowerCase();
      return hay.includes(search);
    });

    const sorted = [...base].sort((a, b) => {
      let cmp = 0;
      if (sortBy === 'date') cmp = new Date(a.date).getTime() - new Date(b.date).getTime();
      else if (sortBy === 'amount') cmp = a.amountCents - b.amountCents;
      else cmp = a.status.localeCompare(b.status);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [query.data, status, search, sortBy, sortDir]);

  const pagination = useMemo(() => {
    const total = processed.length;
    const start = (page - 1) * pageSize;
    const items = processed.slice(start, start + pageSize);
    return { total, page, pageSize, items } as const;
  }, [processed, page, pageSize]);

  return { invoices: query, pagination };
}

/**
 * Plan management: portal-only entrypoint.
 */
export function usePlanManagement() {
  const { showToast } = useToast();
  const openPortal = useMutation({
    mutationFn: async () => {
      const url = await billingService.openCustomerPortal(window.location.href);
      window.location.assign(url);
      return { ok: true } as const;
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  return { openPortal };
}

/**
 * Coupons management: stub implementation for future use.
 * Currently, all plan and subscription management is handled via Stripe Customer Portal.
 */
export function useCoupons() {
  const { showToast } = useToast();

  const applyCoupon = useMutation({
    mutationFn: async (couponCode: string) => {
      void couponCode; // Coupon functionality to be implemented
      return { success: true } as const;
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  const removeCoupon = useMutation({
    mutationFn: async () => {
      // Coupon removal to be implemented
      return { success: true } as const;
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  return { applyCoupon, removeCoupon };
}

/**
 * Organizations & subscription helpers (backend-integrated)
 */
export function useMyOrganizations() {
  const userId = getUserId();
  return useQuery({
    queryKey: ['myOrganizations', userId],
    queryFn: () => organizationsService.listMine(userId),
    enabled: userId.length > 0,
  });
}

export function useSubscriptionRefresh() {
  const { showToast } = useToast();
  const userId = getUserId();
  return useMutation({
    mutationFn: (organizationId: string) =>
      organizationsService.refreshSubscription(organizationId, userId),
    onSuccess: () => showToast('Abonnement gesynchroniseerd met Stripe', 'success'),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
}

export function useCreateOrganization() {
  const { showToast } = useToast();
  const qc = useQueryClient();
  const userId = getUserId();
  return useMutation({
    mutationFn: (name: string) => organizationsService.createOrganization(userId, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['myOrganizations', userId] });
      qc.invalidateQueries({ queryKey: ['org'] });
      showToast('Organisatie aangemaakt', 'success');
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
}

/**
 * Active organization details using the first organization for the user.
 */
export function useActiveOrganizationDetails() {
  const { data: myOrgs } = useMyOrganizations();
  const orgId = myOrgs && myOrgs.length > 0 ? myOrgs[0].id : '';
  return useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsService.getOrganization(orgId),
    enabled: orgId.length > 0,
  });
}

export function useSecurity() {
  const { showToast } = useToast();
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ['security'], queryFn: securityService.getSettings });
  const updateSettings = useMutation({
    mutationFn: securityService.updateSettings,
    onSuccess: data => qc.setQueryData(['security'], data),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const testSAML = useMutation({
    mutationFn: securityService.testSAML,
    onSuccess: res => showToast(res.message || 'Verbinding geslaagd', 'success'),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const exportMyData = useMutation({
    mutationFn: securityService.exportMyData,
    onSuccess: blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const ts = new Date().toISOString().replace(/[:]/g, '-');
      a.href = url;
      a.download = `mijn-gegevens-${ts}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Gegevens geëxporteerd', 'success');
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const deleteMyData = useMutation({
    mutationFn: securityService.deleteMyData,
    onSuccess: () => {
      useQueryClient().invalidateQueries({ queryKey: ['security'] });
      useQueryClient().invalidateQueries({ queryKey: ['audit'] });
      showToast('Gegevens verwijderd', 'success');
    },
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  return { settings, updateSettings, testSAML, exportMyData, deleteMyData };
}

export function useIntegrations() {
  const { showToast } = useToast();
  const qc = useQueryClient();
  const emailDomain = useQuery({
    queryKey: ['integrations', 'email-domain'],
    queryFn: integrationsService.getEmailDomain,
  });
  const webhooks = useQuery({
    queryKey: ['integrations', 'webhooks'],
    queryFn: integrationsService.getWebhooks,
  });
  const slack = useQuery({
    queryKey: ['integrations', 'slack'],
    queryFn: integrationsService.getSlack,
  });
  const teams = useQuery({
    queryKey: ['integrations', 'teams'],
    queryFn: integrationsService.getTeams,
  });

  const startDomainVerification = useMutation({
    mutationFn: integrationsService.startDomainVerification,
    onSuccess: data => qc.setQueryData(['integrations', 'email-domain'], data),
  });
  const createWebhook = useMutation({
    mutationFn: integrationsService.createWebhook,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'webhooks'] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const updateWebhook = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Parameters<typeof integrationsService.updateWebhook>[1];
    }) => integrationsService.updateWebhook(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'webhooks'] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const deleteWebhook = useMutation({
    mutationFn: integrationsService.deleteWebhook,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'webhooks'] }),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const testWebhook = useMutation({
    mutationFn: integrationsService.testWebhook,
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  const connectSlack = useMutation({
    mutationFn: integrationsService.connectSlack,
    onSuccess: data => qc.setQueryData(['integrations', 'slack'], data),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const disconnectSlack = useMutation({
    mutationFn: integrationsService.disconnectSlack,
    onSuccess: data => qc.setQueryData(['integrations', 'slack'], data),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  const connectTeams = useMutation({
    mutationFn: integrationsService.connectTeams,
    onSuccess: data => qc.setQueryData(['integrations', 'teams'], data),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });
  const disconnectTeams = useMutation({
    mutationFn: integrationsService.disconnectTeams,
    onSuccess: data => qc.setQueryData(['integrations', 'teams'], data),
    onError: err => showToast(extractErrorMessage(err), 'error'),
  });

  return {
    emailDomain,
    webhooks,
    slack,
    teams,
    startDomainVerification,
    createWebhook,
    updateWebhook,
    deleteWebhook,
    testWebhook,
    connectSlack,
    disconnectSlack,
    connectTeams,
    disconnectTeams,
  };
}

export function useAudit(page: number, pageSize: number) {
  const audit = useQuery({
    queryKey: ['audit', { page, pageSize }],
    queryFn: () => auditService.list(page, pageSize),
  });
  return { audit };
}
