import { useCallback, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Switch } from '~/components/ui/switch';
import { Label } from '~/components/ui/label';
import { m365Service, type M365Subscription } from '@features/Settings/services/m365Service';
import { toast } from 'sonner';

interface PersistedState {
  readonly connected: boolean;
  readonly email?: string;
  readonly connectedAt?: number;
  readonly user_id?: string;
  readonly subscription_id?: string;
}
const STORAGE_KEY = 'office365_integration_state';
const DEFAULT_RESOURCE = "me/mailFolders('Inbox')/messages";

function readPersistedState(): PersistedState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PersistedState) : null;
  } catch {
    return null;
  }
}

function writePersistedState(next: PersistedState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore storage errors */
  }
}

function mergePersisted(partial: Partial<PersistedState>): PersistedState {
  const current = readPersistedState() || { connected: false };
  const next: PersistedState = {
    connected: Boolean(partial.connected ?? current.connected),
    email: typeof partial.email === 'string' ? partial.email : current.email,
    connectedAt:
      typeof partial.connectedAt === 'number' ? partial.connectedAt : current.connectedAt,
    user_id: typeof partial.user_id === 'string' ? partial.user_id : current.user_id,
    subscription_id:
      typeof partial.subscription_id === 'string'
        ? partial.subscription_id
        : current.subscription_id,
  };
  writePersistedState(next);
  return next;
}

export default function AutoDrafterToggle() {
  const queryClient = useQueryClient();

  const { connected, userId } = useMemo(() => {
    const persisted = readPersistedState();
    return {
      connected: persisted?.connected === true,
      userId: persisted?.user_id ?? null,
    } as const;
  }, []);

  const queryKey = useMemo(() => ['m365', 'subscription', userId], [userId]);

  const subscriptionQuery = useQuery({
    queryKey,
    enabled: Boolean(connected && userId),
    queryFn: async (): Promise<M365Subscription | null> => {
      // Prefer cached id if present; validate by listing
      const persisted = readPersistedState();
      const cachedId = persisted?.subscription_id;
      try {
        const listing = await m365Service.listSubscriptions();
        if (cachedId) {
          const byId = listing.subscriptions.find(s => s.id === cachedId) ?? null;
          if (byId) return byId;
        }
        if (persisted?.user_id) {
          const byUser = listing.subscriptions.find(s => s.user_id === persisted.user_id) ?? null;
          if (byUser) {
            mergePersisted({ subscription_id: byUser.id });
          }
          return byUser;
        }
      } catch {
        // Surface no subscription on errors; mutations will report details
      }
      return null;
    },
  });

  const enableMutation = useMutation({
    mutationFn: async (): Promise<M365Subscription> => {
      if (!userId) throw new Error('Geen gebruiker gevonden.');
      const res = await m365Service.createSubscription({
        user_id: userId,
        resource: DEFAULT_RESOURCE,
      });
      mergePersisted({ subscription_id: res.subscription.id });
      return res.subscription;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
      toast.success('Auto-drafter ingeschakeld.');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Kon auto-drafter niet inschakelen.';
      toast.error(message);
    },
  });

  const disableMutation = useMutation({
    mutationFn: async (): Promise<void> => {
      const current = subscriptionQuery.data;
      if (current?.id) {
        await m365Service.deleteSubscription(current.id);
        mergePersisted({ subscription_id: undefined });
        return;
      }
      // Fallback: attempt to find by user_id
      const persisted = readPersistedState();
      const listing = await m365Service.listSubscriptions();
      const match = listing.subscriptions.find(s => s.user_id === persisted?.user_id);
      if (match) {
        await m365Service.deleteSubscription(match.id);
      }
      mergePersisted({ subscription_id: undefined });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
      toast.success('Auto-drafter uitgeschakeld.');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Kon auto-drafter niet uitschakelen.';
      toast.error(message);
    },
  });

  const checked = Boolean(subscriptionQuery.data);
  const disabled =
    !connected ||
    !userId ||
    subscriptionQuery.isLoading ||
    enableMutation.isPending ||
    disableMutation.isPending;

  const onCheckedChange = useCallback(
    (value: boolean) => {
      if (!connected || !userId) return;
      if (value) {
        enableMutation.mutate();
      } else {
        disableMutation.mutate();
      }
    },
    [connected, userId, enableMutation, disableMutation],
  );

  return (
    <div className="flex items-center gap-2">
      <Switch
        id="autoDrafterEnabled"
        checked={checked}
        disabled={disabled}
        onCheckedChange={v => onCheckedChange(Boolean(v))}
      />
      <div className="flex flex-col">
        <Label htmlFor="autoDrafterEnabled">Automatisch opstellen</Label>
        <span className="text-xs text-muted-foreground">
          Activeert de luisteraar voor nieuwe e-mails
        </span>
      </div>
    </div>
  );
}
