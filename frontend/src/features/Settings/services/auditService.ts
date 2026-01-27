import { getJson } from '~/services/http';
import { simulateNetworkDelay, auditLogsFixture } from '../fixtures';
import type { AuditLogEntry } from '../types';

export const auditService = {
  async list(
    page: number,
    pageSize: number,
  ): Promise<{ rows: ReadonlyArray<AuditLogEntry>; total: number }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const start = (page - 1) * pageSize;
      const end = start + pageSize;
      return { rows: auditLogsFixture.slice(start, end), total: auditLogsFixture.length };
    }
    return getJson<{ rows: AuditLogEntry[]; total: number }>(
      `/api/audit?page=${page}&pageSize=${pageSize}`,
    );
  },
};

export type AuditService = typeof auditService;
