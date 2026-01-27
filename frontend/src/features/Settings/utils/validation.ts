/**
 * Validation utilities for the Settings feature
 * - Generic helpers around Zod
 * - Model-specific type guards
 */

import { z } from 'zod';

import {
  orgProfileSchema,
  memberSchema,
  planInfoSchema,
  usageMetricSchema,
  invoiceSchema,
  securitySettingsSchema,
  emailDomainVerificationSchema,
  webhookSchema,
  slackIntegrationSchema,
  teamsIntegrationSchema,
  auditLogEntrySchema,
} from '../schemas';

import type {
  OrgProfile,
  Member,
  PlanInfo,
  UsageMetric,
  Invoice,
  SecuritySettings,
  EmailDomainVerification,
  Webhook,
  SlackIntegration,
  TeamsIntegration,
  AuditLogEntry,
} from '../types';

export type SafeParseSuccess<T> = { success: true; data: T };
export type SafeParseFailure = {
  success: false;
  errors: ReadonlyArray<string>;
  issues: ReadonlyArray<z.ZodIssue>;
};
export type SafeParseResult<T> = SafeParseSuccess<T> | SafeParseFailure;

/** Convert Zod issues into human-readable Dutch messages with dot-paths */
export function stringifyZodIssues(issues: ReadonlyArray<z.ZodIssue>): ReadonlyArray<string> {
  return issues.map(issue => {
    const path = issue.path.map(p => String(p)).join('.');
    const location = path.length > 0 ? `${path}: ` : '';
    return `${location}${issue.message}`;
  });
}

/** Create a type guard function for a Zod schema */
export function createTypeGuard<S extends z.ZodTypeAny>(
  schema: S,
): (value: unknown) => value is z.infer<S> {
  return (value: unknown): value is z.infer<S> => schema.safeParse(value).success;
}

/** Safe-parse data using a schema, returning a discriminated union */
export function safeParseSchema<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown,
): SafeParseResult<z.infer<S>> {
  const result = schema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }
  const issues = result.error.issues;
  return { success: false, errors: stringifyZodIssues(issues), issues };
}

/** Strictly parse data or throw an Error with labeled Dutch messages */
export function parseSchemaOrThrow<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown,
  label?: string,
): z.infer<S> {
  const parsed = safeParseSchema(schema, data);
  if (parsed.success) return parsed.data;
  const prefix =
    typeof label === 'string' && label.length > 0
      ? `Validatie mislukt voor ${label}: `
      : 'Validatie mislukt: ';
  throw new Error(prefix + parsed.errors.join('; '));
}

// Model-specific type guards
export const isOrgProfile = (value: unknown): value is OrgProfile =>
  createTypeGuard(orgProfileSchema)(value);
export const isMember = (value: unknown): value is Member => createTypeGuard(memberSchema)(value);
export const isPlanInfo = (value: unknown): value is PlanInfo =>
  createTypeGuard(planInfoSchema)(value);
export const isUsageMetric = (value: unknown): value is UsageMetric =>
  createTypeGuard(usageMetricSchema)(value);
export const isInvoice = (value: unknown): value is Invoice =>
  createTypeGuard(invoiceSchema)(value);
export const isSecuritySettings = (value: unknown): value is SecuritySettings =>
  createTypeGuard(securitySettingsSchema)(value);
export const isEmailDomainVerification = (value: unknown): value is EmailDomainVerification =>
  createTypeGuard(emailDomainVerificationSchema)(value);
export const isWebhook = (value: unknown): value is Webhook =>
  createTypeGuard(webhookSchema)(value);
export const isSlackIntegration = (value: unknown): value is SlackIntegration =>
  createTypeGuard(slackIntegrationSchema)(value);
export const isTeamsIntegration = (value: unknown): value is TeamsIntegration =>
  createTypeGuard(teamsIntegrationSchema)(value);
export const isAuditLogEntry = (value: unknown): value is AuditLogEntry =>
  createTypeGuard(auditLogEntrySchema)(value);
