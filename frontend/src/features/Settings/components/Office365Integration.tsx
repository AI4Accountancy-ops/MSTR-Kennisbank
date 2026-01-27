import { useEffect, useState } from 'react';
import { ExternalLink, Mail } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';

import outlookSvg from '@assets/icons/outlook.svg';
import { office365StringsNl as t } from '@features/Settings/locales/office365.nl';
import { m365Service } from '../services/m365Service';
import AutoDrafterToggle from './AutoDrafterToggle';

interface PersistedState {
  connected: boolean;
  email?: string;
  connectedAt?: number;
  user_id?: string;
}

export default function Office365Integration() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [email, setEmail] = useState<string>('gebruiker@bedrijf.nl');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('office365_integration_state');
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<PersistedState>;
      if (parsed.connected === true) {
        setConnected(true);
        if (typeof parsed.email === 'string' && parsed.email.length > 0) {
          setEmail(parsed.email);
        }
      }
    } catch {
      /* ignore */
    }
  }, []);

  const persist = (state: PersistedState) => {
    try {
      localStorage.setItem('office365_integration_state', JSON.stringify(state));
    } catch {
      /* ignore */
    }
  };

  // Removed staged modal emulation. Connect now redirects immediately.

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      const successUrl = `${window.location.origin}/settings/integrations/outlook/success`;
      const auth = await m365Service.authenticate({ redirect_uri: successUrl });
      window.location.assign(auth.auth_url);
    } catch {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await m365Service.clearUsers();
    } finally {
      setConnected(false);
      persist({ connected: false });
      window.dispatchEvent(new Event('office365IntegrationChanged'));
    }
  };

  return (
    <Card className="border-none shadow-none">
      <CardContent className="p-0">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <img src={outlookSvg} alt="Outlook" className="h-6 w-6" />
            <div>
              <h3 className="font-medium">{t.integration.title}</h3>
              <p className="text-sm text-muted-foreground">{t.integration.subtitle}</p>
            </div>
          </div>
          {connected ? (
            <Badge className="bg-green-100 text-green-800">{t.integration.status.connected}</Badge>
          ) : (
            <Badge variant="outline">{t.integration.status.disconnected}</Badge>
          )}
        </div>

        <Separator className="my-4" />

        {!connected ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="md:col-span-2 space-y-4">
              <div>
                <h4 className="text-sm font-medium">{t.integration.expectations.title}</h4>
                <p className="text-sm text-muted-foreground">
                  {t.integration.expectations.description}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-md border p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <Mail className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium">
                      {t.integration.scopes.outlook.title}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t.integration.scopes.outlook.description}
                  </p>
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                <p>
                  {t.integration.consentNote}
                  <a
                    className="underline"
                    href="https://learn.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t.integration.docsLinkText} <ExternalLink className="inline h-3 w-3" />
                  </a>
                  .
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <Button className="w-full" onClick={handleConnect} disabled={isConnecting}>
                {isConnecting ? 'Verbinden…' : t.integration.connect}
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="md:col-span-2 space-y-3">
              <div className="rounded-md border p-3">
                <div className="mb-1 text-sm">{t.integration.connectedAsTitle}</div>
                <div className="text-sm font-medium">{email}</div>
                <div className="text-xs text-muted-foreground">{t.integration.connectedAsNote}</div>
              </div>
              <div className="flex items-center gap-3">
                <AutoDrafterToggle />
                <Button variant="outline" onClick={handleDisconnect} disabled={isConnecting}>
                  {t.integration.buttons.disconnect}
                </Button>
              </div>
            </div>
            <div className="space-y-3">
              <div className="rounded-md border p-3 text-xs text-muted-foreground">
                Tip: beheer rechten in het Microsoft Entra-beheercentrum. Intrekken is direct van
                kracht.
              </div>
            </div>
          </div>
        )}
        {/* Removed staged modal UI */}
      </CardContent>
    </Card>
  );
}
