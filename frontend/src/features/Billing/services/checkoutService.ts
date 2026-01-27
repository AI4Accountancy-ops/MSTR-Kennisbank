import { postJson } from '~/services/http';

interface CreateCheckoutPayload {
  readonly user_id: string;
  readonly organization_id: string;
  readonly price_id: string;
  readonly success_url: string;
  readonly cancel_url: string;
  readonly trial_days?: number;
  readonly overage_price_id?: string;
}

interface CreateCheckoutResponse {
  readonly status: string;
  readonly url: string;
}

export async function createCheckoutSession(payload: CreateCheckoutPayload): Promise<string> {
  const response = await postJson<CreateCheckoutPayload, CreateCheckoutResponse>(
    '/billing/create_checkout_session',
    payload,
  );
  if (
    response.status !== 'success' ||
    typeof response.url !== 'string' ||
    response.url.length === 0
  ) {
    throw new Error('Kon Stripe Checkout niet starten. Probeer het opnieuw.');
  }
  return response.url;
}
