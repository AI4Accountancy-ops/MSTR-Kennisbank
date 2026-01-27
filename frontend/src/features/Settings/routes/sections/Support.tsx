import { useState } from 'react';
import { Mail, Phone, User } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';

import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import { usePlanQuery } from '../../hooks/useSettingsQueries';

export default function Support() {
  const [isLoading] = useState(false);
  const [error] = useState<string | null>(null);
  const { data: plan } = usePlanQuery();

  if (isLoading) {
    return <LoadingState message="Support informatie laden..." skeletonLines={3} />;
  }

  if (error) {
    return (
      <ErrorState
        title="Fout bij laden"
        description="Er ging iets mis bij het laden van de support informatie."
      />
    );
  }

  const isEnterprise = plan?.tier === 'enterprise';
  const isProOrHigher = plan?.tier === 'pro' || plan?.tier === 'enterprise';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Support</h1>
        <p className="text-muted-foreground">
          Krijg hulp en ondersteuning voor uw AI4Accountancy workspace.
        </p>
      </div>

      {/* Support Channels */}
      <Card>
        <CardHeader>
          <CardTitle>Support Kanalen</CardTitle>
          <CardDescription>
            Kies de beste manier om contact op te nemen met ons support team.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Email Support - Available to all */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-blue-100 rounded flex items-center justify-center">
                <Mail className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <h3 className="font-medium">E-mail Support</h3>
                <p className="text-sm text-muted-foreground">
                  Stuur een e-mail naar ons support team
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-green-100 text-green-800">Beschikbaar</Badge>
              <Button variant="outline" size="sm">
                Contact opnemen
              </Button>
            </div>
          </div>

          {/* Phone Support - Enterprise only */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-purple-100 rounded flex items-center justify-center">
                <Phone className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <h3 className="font-medium">Telefoon Support</h3>
                <p className="text-sm text-muted-foreground">Bel ons support team direct</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isEnterprise ? (
                <>
                  <Badge className="bg-green-100 text-green-800">Beschikbaar</Badge>
                  <Button variant="outline" size="sm">
                    Bel nu
                  </Button>
                </>
              ) : (
                <>
                  <Badge variant="outline">Enterprise vereist</Badge>
                  <Button variant="outline" size="sm" disabled>
                    Upgrade vereist
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Account Manager - Enterprise only */}
      {isEnterprise && (
        <Card>
          <CardHeader>
            <CardTitle>Persoonlijke Account Manager</CardTitle>
            <CardDescription>
              Uw toegewezen account manager voor persoonlijke ondersteuning.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 p-4 border rounded-lg">
              <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center">
                <User className="h-6 w-6 text-gray-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium">Jan de Vries</h3>
                <p className="text-sm text-muted-foreground">Senior Account Manager</p>
                <p className="text-sm text-muted-foreground">jan.devries@ai4accountancy.nl</p>
              </div>
              <Button variant="outline" size="sm">
                Contact opnemen
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* SLA Information */}
      <Card>
        <CardHeader>
          <CardTitle>Service Level Agreement (SLA)</CardTitle>
          <CardDescription>
            Onze toezeggingen voor response tijden en beschikbaarheid.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-blue-600">24/7</div>
                <div className="text-sm text-muted-foreground">Systeem beschikbaarheid</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {isProOrHigher ? '< 2 uur' : '< 24 uur'}
                </div>
                <div className="text-sm text-muted-foreground">Response tijd</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-purple-600">99.9%</div>
                <div className="text-sm text-muted-foreground">Uptime garantie</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
