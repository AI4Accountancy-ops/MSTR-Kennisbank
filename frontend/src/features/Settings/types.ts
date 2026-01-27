/**
 * Settings feature type models
 *
 * Strict TypeScript types for the Settings area. These mirror the PRD Appendix
 * and are consumed by validation schemas and forms.
 *
 * Conventions:
 * - Double quotes for strings
 * - No usage of `any` or non-null assertions
 * - Use `readonly` for identifiers and `ReadonlyArray<T>` for collections
 */

/** Role of a workspace member */
export type Role = 'owner' | 'admin' | 'member';
export type UserRole = Role; // Alias for consistency
export const ROLES = ['owner', 'admin', 'member'] as const;

/**
 * Current user information
 */
export interface User {
  readonly id: string;
  readonly email: string;
  readonly name: string;
  readonly role: UserRole;
  readonly avatarUrl?: string;
  readonly lastLoginAt?: string;
}

/** Subscription plan tier */
export type PlanTier = 'instap' | 'groei' | 'pro' | 'enterprise';
export const PLAN_TIERS = ['instap', 'groei', 'pro', 'enterprise'] as const;

/** Supported currency codes */
export type Currency = 'EUR';
export const CURRENCIES = ['EUR'] as const;

/**
 * Organization profile information
 */
export interface OrgProfile {
  readonly id: string;
  name: string;
  vatNumber?: string;
  billingAddress?: string;
}

/**
 * Organization member information
 */
export interface Member {
  readonly id: string;
  name: string;
  email: string;
  role: Role;
  invitedAt?: string;
  lastActiveAt?: string;
}

/**
 * Subscription plan information
 */
export interface PlanInfo {
  tier: PlanTier;
  pricePerMonthCents: number;
  nextRenewalDate?: string;
  currency: Currency;
  features: ReadonlyArray<string>;
}

/** Names of tracked usage metrics */
export type UsageMetricName = 'messages' | 'attachments' | 'seats';
export const USAGE_METRICS = ['messages', 'attachments', 'seats'] as const;

/** Unit of measure for usage metrics */
export type UsageUnit = 'count' | 'bytes';
export const USAGE_UNITS = ['count', 'bytes'] as const;

/**
 * Usage metric datapoint
 */
export interface UsageMetric {
  metric: UsageMetricName;
  period: 'month';
  used: number;
  limit?: number;
  forecast?: number;
  unit: UsageUnit;
}

/** Supported usage periods for per-user data */
export type UsagePeriod = 'day' | 'week' | 'month';
export const USAGE_PERIODS = ['day', 'week', 'month'] as const;

/**
 * Per-user usage data
 */
export interface UserUsageData {
  readonly userId: string;
  readonly userName: string;
  readonly userEmail: string;
  readonly messagesSent: number;
  readonly tokensUsed: number;
  readonly attachmentsUploaded: number;
  readonly lastActivityDate: string;
}

/**
 * Threshold settings for usage alerts
 */
export interface ThresholdSettings {
  messages: number;
  attachments: number;
  tokens: number;
}

/** Invoice status values */
export type InvoiceStatus = 'paid' | 'open' | 'void';
export const INVOICE_STATUSES = ['paid', 'open', 'void'] as const;

/**
 * Invoice information
 */
export interface Invoice {
  readonly id: string;
  date: string;
  amountCents: number;
  currency: Currency;
  status: InvoiceStatus;
  url: string;
}

/**
 * Backend billing endpoints (typings aligned with FastAPI models)
 */
export interface ChangeSubscriptionPayload {
  readonly acting_user_id: string;
  readonly organization_id: string;
  readonly price_id: string; // Stripe Price ID
}

export interface ChangeSubscriptionResponse {
  readonly status: 'success';
  readonly scheduled: boolean;
  readonly switches_on?: string; // ISO8601 timestamp
  readonly current_plan_price_id?: string;
  readonly new_plan_price_id?: string;
  readonly subscription_id?: string;
}

export interface CancelOrResumeSubscriptionPayload {
  readonly acting_user_id: string;
  readonly organization_id: string;
}

export interface CancelSubscriptionResponse {
  readonly status: 'success';
  readonly cancel_at_period_end: true;
  readonly ends_on?: string; // ISO8601 timestamp
  readonly subscription_id?: string;
}

export interface ResumeSubscriptionResponse {
  readonly status: 'success';
  readonly cancel_at_period_end: false;
  readonly subscription_id?: string;
}

/**
 * Security and compliance settings
 */
export interface SecuritySettings {
  readonly twoFactorEnabled: true; // Always enabled
  readonly dataResidency: 'eu'; // Always EU
  samlEnabled: boolean;
  saml?: {
    entityId?: string;
    acsUrl?: string;
    metadataUrl?: string;
  };
}

/** Verification status for email domain */
export type VerificationStatus = 'unverified' | 'pending' | 'verified';
export const VERIFICATION_STATUSES = ['unverified', 'pending', 'verified'] as const;

/**
 * Email domain verification information
 */
export interface EmailDomainVerification {
  domain: string;
  status: VerificationStatus;
  txtName?: string;
  txtValue?: string;
}

/** Supported webhook event names */
export type WebhookEvent =
  | 'message.created'
  | 'message.completed'
  | 'user.invited'
  | 'member.removed';
export const WEBHOOK_EVENTS = [
  'message.created',
  'message.completed',
  'user.invited',
  'member.removed',
] as const;

/**
 * Webhook configuration
 */
export interface Webhook {
  readonly id: string;
  url: string;
  events: ReadonlyArray<WebhookEvent>;
  secretMasked: string; // e.g., 'sk_****1234'
}

/**
 * Slack integration configuration
 */
export interface SlackIntegration {
  connected: boolean;
  teamName?: string;
  defaultChannel?: string;
}

/**
 * Teams integration configuration
 */
export interface TeamsIntegration {
  connected: boolean;
  teamName?: string;
  defaultChannel?: string;
}

/**
 * Audit log entry
 */
export interface AuditLogEntry {
  readonly id: string;
  timestamp: string;
  actorEmail: string;
  action: string;
  target?: string;
  metadata?: Record<string, string>;
}
