import { postJson } from '~/services/http';

export interface AccessCheckResponse {
  readonly status: 'success';
  readonly has_access: boolean;
}

export interface AccessCheckRequest {
  readonly user_id: string;
}

export const accessService = {
  async checkAccess(req: AccessCheckRequest): Promise<AccessCheckResponse> {
    return postJson<AccessCheckRequest, AccessCheckResponse>('/access/check', req);
  },
};
