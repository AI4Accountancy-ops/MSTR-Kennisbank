import { PlanPriceIds } from './types';

export const planPriceIds: PlanPriceIds = {
  instap: import.meta.env.VITE_STRIPE_PRICE_INSTAP as string | undefined,
  groei: import.meta.env.VITE_STRIPE_PRICE_GROEI as string | undefined,
  pro: import.meta.env.VITE_STRIPE_PRICE_PRO as string | undefined,
  enterprise: import.meta.env.VITE_STRIPE_PRICE_ENTERPRISE as string | undefined,
};
