import { postJson } from '~/services/http';
import { createCheckoutSession } from '@features/Billing/services/checkoutService';
import { organizationService } from '~/services/organizationService';
import { getPriceIdForTier } from '@features/Billing/utils';
import type { PlanTier } from '@features/Billing/types';
import { msalInstance } from '../../../msal';

interface LoginRequestBody {
  readonly user_id: string;
  readonly email: string;
  readonly name: string;
  readonly auth_provider: 'microsoft' | 'google';
  readonly is_subscribed: boolean;
  readonly selected_price_id?: string;
  readonly success_url?: string;
  readonly cancel_url?: string;
}

interface LoginResponseBody {
  readonly status: string;
  readonly next?: 'checkout' | 'choose_plan' | 'app';
  readonly checkout_url?: string;
}

export async function startCheckoutWithBackendDecision(
  payload: LoginRequestBody,
): Promise<'checkout' | 'app' | 'choose_plan'> {
  const data = await postJson<LoginRequestBody, LoginResponseBody>('/login', payload);
  if (data.status !== 'success') {
    return 'choose_plan';
  }
  if (
    data.next === 'checkout' &&
    typeof data.checkout_url === 'string' &&
    data.checkout_url.length > 0
  ) {
    // Safety: ensure user has at least one organization before Stripe redirect
    try {
      const myOrgs = await organizationService.listMyOrganizations({ user_id: payload.user_id });
      if (!Array.isArray(myOrgs.organizations) || myOrgs.organizations.length === 0) {
        window.location.href = `${window.location.origin}/onboarding/create-organization`;
        return 'choose_plan';
      }
    } catch {
      // On failure to check, send user to onboarding instead of checkout to be safe
      window.location.href = `${window.location.origin}/onboarding/create-organization`;
      return 'choose_plan';
    }
    window.location.replace(data.checkout_url);
    return 'checkout';
  }
  if (data.next === 'app') {
    window.location.href = `${window.location.origin}/home`;
    return 'app';
  }
  // If backend asks to choose plan but we have a preselected plan, try direct checkout creation as fallback
  if (payload.selected_price_id) {
    try {
      // Ensure user has an organization before creating checkout directly
      const myOrgs = await organizationService.listMyOrganizations({ user_id: payload.user_id });
      if (!Array.isArray(myOrgs.organizations) || myOrgs.organizations.length === 0) {
        window.location.href = `${window.location.origin}/onboarding/create-organization`;
        return 'choose_plan';
      }

      const firstOrg = myOrgs.organizations[0];
      const checkoutUrl = await createCheckoutSession({
        user_id: payload.user_id,
        organization_id: firstOrg.id,
        price_id: payload.selected_price_id,
        success_url: payload.success_url ?? `${window.location.origin}/billing/success`,
        cancel_url: payload.cancel_url ?? `${window.location.origin}/billing/cancel`,
      });
      window.location.replace(checkoutUrl);
      return 'checkout';
    } catch {
      // swallow and fall through to choose_plan
    }
  }
  // default: let the caller route to pricing
  return 'choose_plan';
}

/**
 * Start a Stripe Checkout session with a 7‑day trial for a given plan tier.
 * Handles authentication state, organization presence, and redirects accordingly.
 */
export async function startTrialCheckout(tier: PlanTier): Promise<void> {
  const priceId = getPriceIdForTier(tier);
  if (!priceId) {
    throw new Error('Ongeldig prijsplan.');
  }

  const origin = window.location.origin;
  const successUrl = `${origin}/billing/success`;
  const cancelUrl = `${origin}/billing/cancel`;

  // Resolve user id from MSAL or B2C local storage
  const accounts = msalInstance.getAllAccounts();
  const b2cRaw = localStorage.getItem('b2c_user');
  const b2c = b2cRaw ? (JSON.parse(b2cRaw) as { user_id?: string }) : {};
  const userId = b2c.user_id || (accounts[0]?.localAccountId ?? '');

  // If not authenticated, persist selected price and go to signup
  if (!userId) {
    localStorage.setItem('selected_price_id', priceId);
    window.location.href = `${origin}/signup`;
    return;
  }

  // Ensure at least one organization exists
  const myOrgs = await organizationService.listMyOrganizations({ user_id: userId });
  if (!Array.isArray(myOrgs.organizations) || myOrgs.organizations.length === 0) {
    localStorage.setItem('selected_price_id', priceId);
    window.location.href = `${origin}/onboarding/create-organization`;
    return;
  }
  const firstOrg = myOrgs.organizations[0];

  // Create checkout session with trial_days: 7 and redirect
  const checkoutUrl = await createCheckoutSession({
    user_id: userId,
    organization_id: firstOrg.id,
    price_id: priceId,
    success_url: successUrl,
    cancel_url: cancelUrl,
    trial_days: 7,
  });
  window.location.replace(checkoutUrl);
}
