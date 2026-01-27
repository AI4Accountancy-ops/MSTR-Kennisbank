/**
 * Zod validation schemas for Settings models
 * - Dutch validation messages
 * - Mirrors interfaces in ./index
 */

import { z } from 'zod';

// Enums and literals
export const roleSchema = z.union([z.literal('owner'), z.literal('admin'), z.literal('member')]);

export const planTierSchema = z.union([
  z.literal('free'),
  z.literal('pro'),
  z.literal('enterprise'),
]);

export const currencySchema = z.literal('EUR');

export const usageMetricNameSchema = z.union([
  z.literal('messages'),
  z.literal('attachments'),
  z.literal('seats'),
]);

export const usageUnitSchema = z.union([z.literal('count'), z.literal('bytes')]);

export const invoiceStatusSchema = z.union([
  z.literal('paid'),
  z.literal('open'),
  z.literal('void'),
]);

export const verificationStatusSchema = z.union([
  z.literal('unverified'),
  z.literal('pending'),
  z.literal('verified'),
]);

export const webhookEventSchema = z.union([
  z.literal('message.created'),
  z.literal('message.completed'),
  z.literal('user.invited'),
  z.literal('member.removed'),
]);

// Shared primitives
const nonEmptyString = z.string().min(1, 'Verplicht veld');
const isoDateTime = z.string().datetime({ message: 'Ongeldige datumtijd' });

// Schemas
export const orgProfileSchema = z.object({
  id: nonEmptyString,
  name: nonEmptyString,
  vatNumber: z.string().optional(),
  billingAddress: z.string().optional(),
});

export const memberSchema = z.object({
  id: nonEmptyString,
  name: nonEmptyString,
  email: z.string().email('Ongeldig e-mailadres'),
  role: roleSchema,
  invitedAt: isoDateTime.optional(),
  lastActiveAt: isoDateTime.optional(),
});

export const planInfoSchema = z.object({
  tier: planTierSchema,
  pricePerMonthCents: z
    .number({ message: 'Moet een getal zijn' })
    .int('Moet een geheel getal zijn')
    .nonnegative('Moet 0 of groter zijn'),
  nextRenewalDate: isoDateTime.optional(),
  currency: currencySchema,
  features: z.array(nonEmptyString).default([]),
});

export const usageMetricSchema = z.object({
  metric: usageMetricNameSchema,
  period: z.literal('month'),
  used: z.number({ message: 'Moet een getal zijn' }).nonnegative('Moet 0 of groter zijn'),
  limit: z
    .number({ message: 'Moet een getal zijn' })
    .nonnegative('Moet 0 of groter zijn')
    .optional(),
  forecast: z
    .number({ message: 'Moet een getal zijn' })
    .nonnegative('Moet 0 of groter zijn')
    .optional(),
  unit: usageUnitSchema,
});

export const invoiceSchema = z.object({
  id: nonEmptyString,
  date: isoDateTime,
  amountCents: z
    .number({ message: 'Moet een getal zijn' })
    .int('Moet een geheel getal zijn')
    .nonnegative('Moet 0 of groter zijn'),
  currency: currencySchema,
  status: invoiceStatusSchema,
  url: z.string().url('Ongeldige URL'),
});

export const securitySettingsSchema = z.object({
  twoFactorEnabled: z.literal(true), // Always enabled
  dataResidency: z.literal('eu'), // Always EU
  samlEnabled: z.boolean(),
  saml: z
    .object({
      entityId: z.string().optional(),
      acsUrl: z.string().url('Ongeldige URL').optional(),
      metadataUrl: z.string().url('Ongeldige URL').optional(),
    })
    .optional(),
});

export const emailDomainVerificationSchema = z.object({
  domain: nonEmptyString,
  status: verificationStatusSchema,
  txtName: z.string().optional(),
  txtValue: z.string().optional(),
});

export const webhookSchema = z.object({
  id: nonEmptyString,
  url: z.string().url('Ongeldige URL'),
  events: z.array(webhookEventSchema).default([]),
  secretMasked: nonEmptyString,
});

export const slackIntegrationSchema = z.object({
  connected: z.boolean(),
  teamName: z.string().optional(),
  defaultChannel: z.string().optional(),
});

export const teamsIntegrationSchema = z.object({
  connected: z.boolean(),
  teamName: z.string().optional(),
  defaultChannel: z.string().optional(),
});

export const auditLogEntrySchema = z.object({
  id: nonEmptyString,
  timestamp: isoDateTime,
  actorEmail: z.string().email('Ongeldig e-mailadres'),
  action: nonEmptyString,
  target: z.string().optional(),
  metadata: z.record(z.string(), z.string()).optional(),
});

// Inferred input types for forms
export type OrgProfileInput = z.infer<typeof orgProfileSchema>;
export type MemberInput = z.infer<typeof memberSchema>;
export type PlanInfoInput = z.infer<typeof planInfoSchema>;
export type UsageMetricInput = z.infer<typeof usageMetricSchema>;
export type InvoiceInput = z.infer<typeof invoiceSchema>;
export type SecuritySettingsInput = z.infer<typeof securitySettingsSchema>;
export type EmailDomainVerificationInput = z.infer<typeof emailDomainVerificationSchema>;
export type WebhookInput = z.infer<typeof webhookSchema>;
export type SlackIntegrationInput = z.infer<typeof slackIntegrationSchema>;
export type TeamsIntegrationInput = z.infer<typeof teamsIntegrationSchema>;
export type AuditLogEntryInput = z.infer<typeof auditLogEntrySchema>;
