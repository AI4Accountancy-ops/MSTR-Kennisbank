import { getJson, postJson, deleteWithBodyJson } from '~/services/http';

export interface MyOrganizationSummary {
  readonly id: string;
  readonly name: string;
  readonly role: 'admin' | 'user';
  readonly subscription_status?: string;
  readonly current_period_end?: string;
  readonly stripe_price_id?: string;
}

export interface ListMyOrganizationsResponse {
  readonly status: 'success' | 'error';
  readonly organizations: ReadonlyArray<MyOrganizationSummary>;
}

export interface RefreshSubscriptionResponse {
  readonly status: 'success';
}

export interface GetOrganizationResponse {
  readonly status: 'success';
  readonly organization: {
    readonly id: string;
    readonly name: string;
    readonly owner_user_id: string;
    readonly created_at?: string | null;
    readonly updated_at?: string | null;
    readonly members?: ReadonlyArray<{ user_id: string; role: 'admin' | 'user' }>;
  };
}

export interface AddMemberResponse {
  readonly status: 'success';
}
export interface UpdateMemberRoleResponse {
  readonly status: 'success';
}
export interface RemoveMemberResponse {
  readonly status: 'success';
}

export const organizationsService = {
  async createOrganization(
    ownerUserId: string,
    name: string,
  ): Promise<{ status: 'success'; organization_id: string }> {
    return postJson<
      { owner_user_id: string; name: string },
      { status: 'success'; organization_id: string }
    >('/organizations', { owner_user_id: ownerUserId, name });
  },

  async listMine(userId: string): Promise<ReadonlyArray<MyOrganizationSummary>> {
    const res = await postJson<{ user_id: string }, ListMyOrganizationsResponse>(
      '/organizations/mine',
      { user_id: userId },
    );
    return res.organizations;
  },

  async refreshSubscription(
    organizationId: string,
    actingUserId: string,
  ): Promise<RefreshSubscriptionResponse> {
    return postJson<
      { organization_id: string; acting_user_id: string },
      RefreshSubscriptionResponse
    >('/organizations/subscription/refresh', {
      organization_id: organizationId,
      acting_user_id: actingUserId,
    });
  },

  async getOrganization(organizationId: string): Promise<GetOrganizationResponse['organization']> {
    const res = await getJson<GetOrganizationResponse>(`/organizations/${organizationId}`);
    return res.organization;
  },

  async addMember(
    organizationId: string,
    actingUserId: string,
    userId: string,
    role: 'admin' | 'user',
  ): Promise<AddMemberResponse> {
    return postJson<
      { organization_id: string; user_id: string; role: 'admin' | 'user'; acting_user_id: string },
      AddMemberResponse
    >('/organizations/members', {
      organization_id: organizationId,
      user_id: userId,
      role,
      acting_user_id: actingUserId,
    });
  },

  async updateMemberRole(
    organizationId: string,
    actingUserId: string,
    userId: string,
    role: 'admin' | 'user',
  ): Promise<UpdateMemberRoleResponse> {
    return postJson<
      { organization_id: string; user_id: string; role: 'admin' | 'user'; acting_user_id: string },
      UpdateMemberRoleResponse
    >('/organizations/members/role', {
      organization_id: organizationId,
      user_id: userId,
      role,
      acting_user_id: actingUserId,
    });
  },

  async removeMember(
    organizationId: string,
    actingUserId: string,
    userId: string,
  ): Promise<RemoveMemberResponse> {
    return deleteWithBodyJson<
      { organization_id: string; user_id: string; acting_user_id: string },
      RemoveMemberResponse
    >('/organizations/members', {
      organization_id: organizationId,
      user_id: userId,
      acting_user_id: actingUserId,
    });
  },
};

export type OrganizationsService = typeof organizationsService;
