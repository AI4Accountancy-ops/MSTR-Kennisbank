import { postJson } from '~/services/http';

export interface MyOrgsRequest {
  readonly user_id: string;
}

export type OrgMemberRole = 'admin' | 'user';

export type StripeSubscriptionStatus =
  | 'incomplete'
  | 'incomplete_expired'
  | 'trialing'
  | 'active'
  | 'past_due'
  | 'canceled'
  | 'unpaid';

export interface MyOrgItem {
  readonly id: string;
  readonly name: string;
  readonly role: OrgMemberRole;
  readonly subscription_status?: StripeSubscriptionStatus | null;
  readonly current_period_end?: string | null;
}

export interface MyOrgsResponse {
  readonly status: 'success';
  readonly organizations: ReadonlyArray<MyOrgItem>;
}

export interface CreateOrganizationRequest {
  readonly owner_user_id: string;
  readonly name: string;
  readonly description?: string;
}

export interface CreateOrganizationResponse {
  readonly status: 'success';
  readonly organization_id: string;
}

export const organizationService = {
  async listMyOrganizations(payload: MyOrgsRequest): Promise<MyOrgsResponse> {
    return await postJson<MyOrgsRequest, MyOrgsResponse>('/organizations/mine', payload);
  },

  async createOrganization(
    payload: CreateOrganizationRequest,
  ): Promise<CreateOrganizationResponse> {
    return await postJson<CreateOrganizationRequest, CreateOrganizationResponse>(
      '/organizations',
      payload,
    );
  },
};

export type OrganizationService = typeof organizationService;

// ------------------------------
// Usage summary (backend-driven)
// ------------------------------
export interface UsageRequest {
  readonly organization_id?: string;
  readonly user_id?: string;
}

export interface UsageSummary {
  readonly organization_id: string;
  readonly status: StripeSubscriptionStatus;
  readonly in_trial: boolean;
  readonly monthly_used: number;
  readonly monthly_quota: number;
  readonly current_period_start: string | null;
  readonly current_period_end: string | null;
  readonly over_quota: boolean;
  readonly daily_used?: number;
  readonly daily_quota?: number;
}

export interface UsageSummaryResponse {
  readonly status: 'success';
  readonly usage: UsageSummary;
}

export async function getUsageSummary(body: UsageRequest): Promise<UsageSummary> {
  const res = await postJson<UsageRequest, UsageSummaryResponse>('/organizations/usage', body);
  return res.usage;
}
