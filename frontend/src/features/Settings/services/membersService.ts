import { getJson, postJson, deleteJson } from '~/services/http';
import { simulateNetworkDelay, membersFixture } from '../fixtures';
import type { Member, Role } from '../types';

let members: Member[] = membersFixture.map(m => ({ ...m }));

const BASE = '/api/members';

export const membersService = {
  async listMembers(): Promise<ReadonlyArray<Member>> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return members;
    }
    return getJson<Member[]>(BASE);
  },

  async invite(email: string): Promise<Member> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const m: Member = {
        id: `mem_${Math.random().toString(36).slice(2, 8)}`,
        name: email.split('@')[0],
        email,
        role: 'member',
        invitedAt: new Date().toISOString(),
        lastActiveAt: undefined,
      };
      members = [...members, m];
      return m;
    }
    return postJson<{ email: string }, Member>(`${BASE}/invite`, { email });
  },

  async regenerateInvite(memberId: string): Promise<{ memberId: string; invitedAt: string }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const idx = members.findIndex(m => m.id === memberId);
      if (idx >= 0) {
        members[idx] = { ...members[idx], invitedAt: new Date().toISOString() };
      }
      return { memberId, invitedAt: members[idx]?.invitedAt ?? new Date().toISOString() };
    }
    return postJson<undefined, { memberId: string; invitedAt: string }>(
      `${BASE}/${memberId}/regenerate-invite`,
      undefined as unknown as undefined,
    );
  },

  async changeRole(memberId: string, role: Role): Promise<Member> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      const idx = members.findIndex(m => m.id === memberId);
      if (idx >= 0) {
        members[idx] = { ...members[idx], role };
        return members[idx];
      }
      throw new Error('Lid niet gevonden');
    }
    return postJson<{ role: Role }, Member>(`${BASE}/${memberId}/role`, { role });
  },

  async remove(memberId: string): Promise<{ removed: true }> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      members = members.filter(m => m.id !== memberId);
      return { removed: true } as const;
    }
    return deleteJson<{ removed: true }>(`${BASE}/${memberId}`);
  },
};

export type MembersService = typeof membersService;
