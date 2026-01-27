import { getJson, postJson, deleteJson } from '~/services/http';

// Strict Types for M365 Connector API (mocked on frontend in DEV)

export interface M365HealthResponse {
  readonly status: 'healthy' | 'degraded' | 'down';
  readonly service: 'm365-connector';
  readonly active_users: number;
  readonly active_subscriptions: number;
}

export interface M365AuthenticateResponse {
  readonly status: 'success';
  readonly auth_url: string;
  readonly message: string;
  readonly state: string;
}

export interface M365AuthenticateRequest {
  readonly redirect_uri?: string;
}

export interface M365UserProfile {
  readonly user_id: string;
  readonly name: string;
  readonly email: string;
}

export interface M365CallbackResponse {
  readonly status: 'success';
  readonly message: string;
  readonly user: M365UserProfile;
  readonly next_steps: string;
}

export interface M365RefreshTokenRequest {
  readonly user_id: string;
}

export interface M365RefreshTokenResponse {
  readonly status: 'success';
  readonly message: string;
  readonly user_id: string;
  readonly expires_in: number;
}

export interface M365UsersListResponse {
  readonly status: 'success';
  readonly count: number;
  readonly users: ReadonlyArray<{
    readonly user_id: string;
    readonly name: string;
    readonly email: string;
    readonly has_token: boolean;
    readonly token_expires_at: string | null;
  }>;
}

export interface M365GetEmailsRequest {
  readonly user_id: string;
  readonly folder?: string;
  readonly limit?: number;
}

export interface M365EmailItem {
  readonly id: string;
  readonly subject: string;
  readonly from: string;
  readonly from_name: string;
  readonly received_datetime: string;
  readonly is_read: boolean;
  readonly body_preview: string;
}

export interface M365GetEmailsResponse {
  readonly status: 'success';
  readonly count: number;
  readonly emails: ReadonlyArray<M365EmailItem>;
}

export interface M365Subscription {
  readonly id: string;
  readonly user_id: string;
  readonly resource: string;
  readonly expires_at: string;
  readonly notification_url: string;
  readonly created_at?: string;
}

export interface M365CreateSubscriptionRequest {
  readonly user_id: string;
  readonly resource?: string;
}

export interface M365CreateSubscriptionResponse {
  readonly status: 'success';
  readonly message: string;
  readonly subscription: M365Subscription;
}

export interface M365ListSubscriptionsResponse {
  readonly status: 'success';
  readonly count: number;
  readonly subscriptions: ReadonlyArray<M365Subscription>;
}

export interface M365DeleteSubscriptionResponse {
  readonly status: 'success';
  readonly message: string;
}

// Public service API
export const m365Service = {
  async health(): Promise<M365HealthResponse> {
    return getJson<M365HealthResponse>('/m365/health');
  },

  async authenticate(req?: M365AuthenticateRequest): Promise<M365AuthenticateResponse> {
    return postJson<M365AuthenticateRequest | undefined, M365AuthenticateResponse>(
      '/m365/auth/authenticate',
      req,
    );
  },

  async callback(payload: { code: string; state: string }): Promise<M365CallbackResponse> {
    const params = new URLSearchParams({ code: payload.code, state: payload.state });
    return getJson<M365CallbackResponse>(`/m365/auth/callback?${params.toString()}`);
  },

  async refreshToken(req: M365RefreshTokenRequest): Promise<M365RefreshTokenResponse> {
    return postJson<M365RefreshTokenRequest, M365RefreshTokenResponse>(
      '/m365/auth/refresh-token',
      req,
    );
  },

  async listUsers(): Promise<M365UsersListResponse> {
    return getJson<M365UsersListResponse>('/m365/auth/users');
  },

  async clearUsers(): Promise<{ status: 'success'; message: string }> {
    return postJson<undefined, { status: 'success'; message: string }>(
      '/m365/auth/users/clear',
      undefined as unknown as undefined,
    );
  },

  async getEmails(req: M365GetEmailsRequest): Promise<M365GetEmailsResponse> {
    return postJson<M365GetEmailsRequest, M365GetEmailsResponse>('/m365/mail/emails', req);
  },

  async createSubscription(
    req: M365CreateSubscriptionRequest,
  ): Promise<M365CreateSubscriptionResponse> {
    return postJson<M365CreateSubscriptionRequest, M365CreateSubscriptionResponse>(
      '/m365/mail/subscriptions',
      req,
    );
  },

  async listSubscriptions(): Promise<M365ListSubscriptionsResponse> {
    return getJson<M365ListSubscriptionsResponse>('/m365/mail/subscriptions');
  },

  async deleteSubscription(id: string): Promise<M365DeleteSubscriptionResponse> {
    return deleteJson<M365DeleteSubscriptionResponse>(`/m365/mail/subscriptions/${id}`);
  },

  async findSubscriptionByUserId(userId: string): Promise<M365Subscription | null> {
    const res = await this.listSubscriptions();
    const sub = res.subscriptions.find(s => s.user_id === userId) ?? null;
    return sub;
  },
};

export type M365Service = typeof m365Service;
