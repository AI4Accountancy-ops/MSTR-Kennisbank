import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import outlookSvg from '@assets/icons/outlook.svg';
import { office365StringsNl as t } from '@features/Settings/locales/office365.nl';

interface FeatureNotificationProps {
  storageKey?: string;
  /** Number of days to hide the notification after action */
  ttlDays?: number;
}

interface StoredDismissal {
  dismissed: boolean;
  expiresAt: number; // epoch ms
}

/**
 * Small, dismissible feature notification targeted for the sidebar's lower-left area.
 * Promotes the new Microsoft 365 integration and links to settings/integrations.
 */
export default function FeatureNotification({
  storageKey = 'feature_ms365_notice_dismissed',
  ttlDays = 7,
}: FeatureNotificationProps) {
  const [dismissed, setDismissed] = useState<boolean>(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        setDismissed(false);
        return;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        // Backward compatible with previous boolean storage
        setDismissed(raw === 'true');
        return;
      }
      const data = parsed as Partial<StoredDismissal>;
      const now = Date.now();
      if (typeof data.expiresAt === 'number' && data.expiresAt > now && data.dismissed === true) {
        setDismissed(true);
      } else {
        // expired or malformed; clear and show again
        localStorage.removeItem(storageKey);
        setDismissed(false);
      }
    } catch {
      setDismissed(false);
    }
  }, [storageKey]);

  const setWithExpiry = useCallback(() => {
    const now = Date.now();
    const ttlMs = Math.max(1, Math.floor(ttlDays)) * 24 * 60 * 60 * 1000;
    const payload: StoredDismissal = { dismissed: true, expiresAt: now + ttlMs };
    try {
      localStorage.setItem(storageKey, JSON.stringify(payload));
    } catch {
      try {
        localStorage.setItem(storageKey, 'true');
      } catch {
        /* noop */
      }
    }
    setDismissed(true);
  }, [storageKey, ttlDays]);

  const handleDismiss = useCallback(() => {
    setWithExpiry();
  }, [setWithExpiry]);

  const handleSetupClick = useCallback(() => {
    setWithExpiry();
  }, [setWithExpiry]);

  const content = useMemo(
    () => (
      <div className="mx-1 mt-1 rounded-md border bg-card p-2 text-xs">
        <div className="mb-1 flex items-center gap-2">
          <Badge variant="secondary" className="px-1.5 py-0 text-[10px] leading-4">
            {t.notification.new}
          </Badge>
          <img src={outlookSvg} alt="Outlook" className="h-3.5 w-3.5" />
          <span className="font-medium">{t.notification.title}</span>
        </div>
        <p className="mb-2 text-muted-foreground">{t.notification.description}</p>
        <div className="flex items-center justify-between gap-2">
          <Button size="sm" className="h-7 px-2 text-xs" asChild onClick={handleSetupClick}>
            <Link to="/settings/integrations">{t.notification.setup}</Link>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-[11px]"
            onClick={handleDismiss}
          >
            {t.notification.hide}
          </Button>
        </div>
      </div>
    ),
    [handleDismiss, handleSetupClick],
  );

  if (dismissed) return null;

  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          <div className="px-1 pb-1">{content}</div>
        </TooltipTrigger>
        <TooltipContent side="right" align="start" className="max-w-[220px] text-xs">
          {t.notification.tooltip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
