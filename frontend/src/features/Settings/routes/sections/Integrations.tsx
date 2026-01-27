import { useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import Office365Integration from '../../components/Office365Integration';

import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

export default function Integrations() {
  const [isLoading] = useState(false);
  const [error] = useState<string | null>(null);

  if (isLoading) {
    return <LoadingState message="Integraties laden..." skeletonLines={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Fout bij laden"
        description="Er ging iets mis bij het laden van de integraties."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integraties</h1>
        <p className="text-muted-foreground">
          Beheer uw integraties met externe services en configureer verbindingen.
        </p>
      </div>

      {/* Office 365 Integration */}
      <Card>
        <CardHeader>
          <CardTitle>Office 365 Integratie</CardTitle>
          <CardDescription>
            Verbind uw workspace met Office 365 voor naadloze toegang tot uw Microsoft services en
            gegevens.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Office365Integration />
        </CardContent>
      </Card>
    </div>
  );
}
