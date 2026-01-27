import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';

import { Button } from '@/components/ui/button';
import { postJson } from '~/services/http';
import { accessService } from '~/services/accessService';

interface CompleteCheckoutRequest {
  readonly user_id: string;
  readonly session_id: string;
}

interface CompleteCheckoutResponse {
  readonly status: string;
  readonly organization_id?: string;
}

export default function BillingSuccessPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const sessionId = params.get('session_id');
        const user = localStorage.getItem('b2c_user');
        const parsed = user ? (JSON.parse(user) as { user_id?: string }) : {};
        const userId = parsed.user_id ?? '';

        if (!sessionId || !userId) {
          setError('Ontbrekende gegevens om de betaling te voltooien.');
          setLoading(false);
          return;
        }

        const payload: CompleteCheckoutRequest = {
          user_id: userId,
          session_id: sessionId,
        };
        const res = await postJson<CompleteCheckoutRequest, CompleteCheckoutResponse>(
          '/billing/complete_checkout',
          payload,
        );
        if (res.status !== 'success') {
          setError('Onbekende fout bij het voltooien van de betaling.');
          return;
        }

        // Wacht tot toegang actief is om bouncing naar /pricing te voorkomen
        const maxAttempts = 10;
        const delayMs = 1000;
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
          try {
            const access = await accessService.checkAccess({ user_id: userId });
            if (access.status === 'success' && access.has_access) {
              navigate('/home', { replace: true });
              return;
            }
          } catch {
            // negeren en opnieuw proberen
          }
          await new Promise(r => setTimeout(r, delayMs));
        }

        // Als toegang nog niet actief is, toon vriendelijke melding
        setError(
          'Je betaling is verwerkt, maar de toegang is nog niet geactiveerd. Probeer het zo opnieuw.',
        );
      } catch {
        setError('Voltooien van betaling is mislukt. Probeer het opnieuw.');
      } finally {
        setLoading(false);
      }
    };
    void run();
  }, [navigate]);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <p>Betaling verwerken...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-16 space-y-6">
        <p className="text-red-600">{error}</p>
        <div className="flex gap-3">
          <Button onClick={() => window.location.reload()}>Opnieuw proberen</Button>
          <Button variant="outline" onClick={() => navigate('/home')}>
            Ga naar app
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
