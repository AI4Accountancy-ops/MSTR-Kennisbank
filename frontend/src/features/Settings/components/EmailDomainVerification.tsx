import { useState } from 'react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';

export default function EmailDomainVerification() {
  const [domain, setDomain] = useState('');
  const [verificationStatus, setVerificationStatus] = useState<'initial' | 'pending' | 'verified'>(
    'initial',
  );

  const handleVerifyDomain = () => {
    // TODO: Implement domain verification logic
    setVerificationStatus('pending');
  };

  const getStatusBadge = () => {
    switch (verificationStatus) {
      case 'verified':
        return <Badge className="bg-green-100 text-green-800">Geverifieerd</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">In behandeling</Badge>;
      default:
        return <Badge variant="outline">Niet geverifieerd</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Label htmlFor="domain-input">E-mail domein</Label>
          <p className="text-sm text-muted-foreground">Voer het domein in dat u wilt verifiëren</p>
        </div>
        {getStatusBadge()}
      </div>

      <div className="flex gap-2">
        <Input
          id="domain-input"
          placeholder="example.com"
          value={domain}
          onChange={e => setDomain(e.target.value)}
          className="flex-1"
        />
        <Button onClick={handleVerifyDomain} disabled={!domain || verificationStatus === 'pending'}>
          {verificationStatus === 'pending' ? 'Verifiëren...' : 'Verificeer'}
        </Button>
      </div>

      {verificationStatus === 'pending' && (
        <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/20">
          <CardHeader>
            <CardTitle className="text-sm">DNS Record Toevoegen</CardTitle>
            <CardDescription className="text-xs">
              Voeg de volgende TXT record toe aan uw DNS configuratie:
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-white dark:bg-gray-800 p-3 rounded border font-mono text-sm">
              <div className="space-y-1">
                <div>
                  <strong>Type:</strong> TXT
                </div>
                <div>
                  <strong>Name:</strong> @
                </div>
                <div>
                  <strong>Value:</strong> ai4accountancy-verification=abc123def456
                </div>
                <div>
                  <strong>TTL:</strong> 3600
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Het kan tot 24 uur duren voordat de verificatie is voltooid.
            </p>
          </CardContent>
        </Card>
      )}

      {verificationStatus === 'verified' && (
        <Card className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
              <p className="text-sm text-green-700 dark:text-green-300">
                Domein {domain} is succesvol geverifieerd
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
