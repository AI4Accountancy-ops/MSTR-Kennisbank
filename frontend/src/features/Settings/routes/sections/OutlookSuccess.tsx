import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Card, CardContent } from '~/components/ui/card';
import { Button } from '~/components/ui/button';
import { Badge } from '~/components/ui/badge';
import { Loader2, CheckCircle2, TriangleAlert } from 'lucide-react';
import { m365Service } from '@features/Settings/services/m365Service';

type Status = 'idle' | 'processing' | 'success' | 'error';

export default function OutlookSuccess() {
  const location = useLocation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Status>('idle');
  const [message, setMessage] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const hasFinalizedRef = useRef<boolean>(false);

  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const code = params.get('code') ?? '';
  const state = params.get('state') ?? '';

  useEffect(() => {
    const finalize = async () => {
      // Prevent duplicate calls due to React strict mode remounts or suspense
      if (hasFinalizedRef.current) {
        return;
      }
      hasFinalizedRef.current = true;

      if (!code || !state) {
        setStatus('error');
        setMessage('Ontbrekende parameters: code of state.');
        return;
      }

      // Idempotency: skip if this state was already processed in this session
      const sessionKey = `m365-callback-${state}`;
      try {
        if (sessionStorage.getItem(sessionKey) === 'done') {
          setStatus('success');
          setMessage('Microsoft 365 is al gekoppeld.');
          return;
        }
      } catch {
        // ignore sessionStorage errors
      }

      setStatus('processing');
      try {
        const res = await m365Service.callback({ code, state });

        try {
          const persisted = {
            connected: true,
            email: res.user.email,
            connectedAt: Date.now(),
            user_id: res.user.user_id,
          } as const;
          localStorage.setItem('office365_integration_state', JSON.stringify(persisted));
          window.dispatchEvent(new Event('office365IntegrationChanged'));
        } catch {
          /* ignore storage errors */
        }

        setEmail(res.user.email);
        setStatus('success');
        setMessage('Microsoft 365 is succesvol gekoppeld.');

        // Mark as completed for this session/state to avoid duplicate callback
        try {
          sessionStorage.setItem(sessionKey, 'done');
        } catch {
          // ignore sessionStorage errors
        }
      } catch {
        setStatus('error');
        setMessage('Koppeling mislukt. Probeer het opnieuw.');
      }
    };

    void finalize();
  }, [code, state]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Microsoft 365</h2>
          <p className="text-muted-foreground">Koppeling voltooid</p>
        </div>
        {status === 'success' ? (
          <Badge className="bg-green-100 text-green-800">Verbonden</Badge>
        ) : status === 'processing' ? (
          <Badge variant="outline">Bezig…</Badge>
        ) : status === 'error' ? (
          <Badge variant="destructive">Mislukt</Badge>
        ) : (
          <Badge variant="outline">Wachten…</Badge>
        )}
      </div>

      <Card className="border">
        <CardContent className="p-4">
          {status === 'processing' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Autorisatie voltooien…
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-sm font-medium">{message}</span>
              </div>
              {email && <div className="text-sm text-muted-foreground">Ingelogd als: {email}</div>}
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-red-700">
                <TriangleAlert className="h-5 w-5" />
                <span className="text-sm font-medium">{message}</span>
              </div>
              <div className="text-xs text-muted-foreground">
                Controleer of u toegang heeft gegeven in Microsoft en probeer opnieuw.
              </div>
              <div>
                <Button
                  variant="outline"
                  onClick={() => navigate('/settings/integrations/office365')}
                >
                  Terug naar integratie
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {status === 'success' && (
        <div className="flex gap-2">
          <Button onClick={() => navigate('/settings/integrations/office365')}>
            Ga naar integratie
          </Button>
        </div>
      )}
    </div>
  );
}
