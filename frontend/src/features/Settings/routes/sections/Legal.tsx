import { useEffect, useState } from 'react';
import { ExternalLink, FileText, Shield, CreditCard } from 'lucide-react';

import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';

import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import { useSettingsLayout } from '../../components/SettingsLayout';

export default function Legal() {
  const { setContentWidthClass } = useSettingsLayout();
  // Expand content width on this page; restore default on unmount
  useEffect(() => {
    setContentWidthClass('w-[70%] max-w-6xl');
    return () => setContentWidthClass('w-[50%] max-w-5xl');
  }, [setContentWidthClass]);

  const [isLoading] = useState(false);
  const [error] = useState<string | null>(null);

  if (isLoading) {
    return <LoadingState message="Juridische documenten laden..." skeletonLines={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Fout bij laden"
        description="Er ging iets mis bij het laden van de juridische documenten."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Juridisch</h1>
        <p className="text-muted-foreground">
          Toegang tot juridische documenten en factureringsinformatie.
        </p>
      </div>

      {/* Legal Documents */}
      <Card>
        <CardHeader>
          <CardTitle>Juridische Documenten</CardTitle>
          <CardDescription>Belangrijke juridische documenten en voorwaarden.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 bg-blue-100 rounded flex items-center justify-center">
                  <FileText className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium">Algemene Voorwaarden</h3>
                  <p className="text-sm text-muted-foreground">
                    Onze algemene voorwaarden en gebruiksvoorwaarden
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a href="/legal/terms" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Bekijken
                </a>
              </Button>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 bg-green-100 rounded flex items-center justify-center">
                  <Shield className="h-4 w-4 text-green-600" />
                </div>
                <div>
                  <h3 className="font-medium">Privacybeleid</h3>
                  <p className="text-sm text-muted-foreground">
                    Hoe wij uw gegevens beschermen en verwerken
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a href="/legal/privacy" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Bekijken
                </a>
              </Button>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 bg-purple-100 rounded flex items-center justify-center">
                  <FileText className="h-4 w-4 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-medium">Cookiebeleid</h3>
                  <p className="text-sm text-muted-foreground">
                    Informatie over het gebruik van cookies
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a href="/legal/cookies" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Bekijken
                </a>
              </Button>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 bg-orange-100 rounded flex items-center justify-center">
                  <FileText className="h-4 w-4 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-medium">SLA Document</h3>
                  <p className="text-sm text-muted-foreground">
                    Service Level Agreement en garanties
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <a href="/legal/sla" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Bekijken
                </a>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Billing Information */}
      <Card>
        <CardHeader>
          <CardTitle>Factureringsinformatie</CardTitle>
          <CardDescription>Belangrijke informatie over facturering en betalingen.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h3 className="font-medium">Bedrijfsgegevens</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Bedrijfsnaam:</span> AI4Accountancy B.V.
                </div>
                <div>
                  <span className="font-medium">KvK nummer:</span> 12345678
                </div>
                <div>
                  <span className="font-medium">BTW nummer:</span> NL123456789B01
                </div>
                <div>
                  <span className="font-medium">Adres:</span>
                  <br />
                  Keizersgracht 241
                  <br />
                  1016 EA Amsterdam
                  <br />
                  Nederland
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="font-medium">Factureringsgegevens</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Factuurperiode:</span> Maandelijks
                </div>
                <div>
                  <span className="font-medium">Betaaltermijn:</span> 14 dagen
                </div>
                <div>
                  <span className="font-medium">Betaalmethoden:</span> iDEAL, Creditcard, SEPA
                </div>
                <div>
                  <span className="font-medium">Valuta:</span> EUR (Euro)
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Facturen downloaden</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Download uw facturen en betalingsbewijzen via de{' '}
              <a href="/settings/plan-billing" className="text-blue-600 hover:underline">
                Plan & Facturering
              </a>{' '}
              sectie.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Data Processing */}
      <Card>
        <CardHeader>
          <CardTitle>Gegevensverwerking</CardTitle>
          <CardDescription>
            Informatie over hoe wij uw gegevens verwerken en beschermen.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h3 className="font-medium">Gegevenslocatie</h3>
                <p className="text-sm text-muted-foreground">
                  Uw gegevens worden opgeslagen in beveiligde datacenters binnen de Europese Unie,
                  met volledige GDPR compliance.
                </p>
              </div>
              <div className="space-y-2">
                <h3 className="font-medium">Gegevensbeveiliging</h3>
                <p className="text-sm text-muted-foreground">
                  Alle gegevens worden versleuteld in transit en at rest, met regelmatige
                  beveiligingsaudits en monitoring.
                </p>
              </div>
            </div>

            <div className="pt-4 border-t">
              <Button variant="outline" size="sm" asChild>
                <a href="/legal/data-processing" target="_blank" rel="noopener noreferrer">
                  <FileText className="h-4 w-4 mr-2" />
                  Volledige gegevensverwerkingsovereenkomst
                </a>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
