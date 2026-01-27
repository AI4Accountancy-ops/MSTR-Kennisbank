import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { useMsal } from '@azure/msal-react';
import { Loader2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { getPriceIdForTier, getTierByPriceId } from '@features/Billing/utils';
import LoginCard from '@features/Authentication/components/LoginCard';

type TierMeta = {
  label: string;
  price: string;
  period: string;
  description: string;
  features: string[];
};

const TIER_META: Record<'instap' | 'groei' | 'pro' | 'enterprise', TierMeta> = {
  instap: {
    label: 'Instap',
    price: '€49',
    period: 'maand',
    description: 'Voor zelfstandige fiscalisten en kleine kantoren',
    features: [
      '250 vragen per maand',
      'Onbeperkt aantal gebruikers in je organisatie',
      'Actuele kennisbank (Belastingdienst & Wetten.overheid)',
      'Basis support',
    ],
  },
  groei: {
    label: 'Groei',
    price: '€149',
    period: 'maand',
    description: 'Voor groeiende kantoren en MKB-adviseurs',
    features: [
      'Alles uit Instap',
      '1.000 vragen per maand',
      'Toegang tot de websearch feature',
      'Uitgebreide support',
    ],
  },
  pro: {
    label: 'Pro',
    price: '€349',
    period: 'maand',
    description: 'Voor middelgrote kantoren met meerdere teams',
    features: [
      'Alles uit Groei',
      '2.500 vragen per maand',
      'Toegang tot beta features & nieuwe innovaties',
      'Premium support',
    ],
  },
  enterprise: {
    label: 'Enterprise',
    price: '€899',
    period: 'vanaf',
    description: 'Voor grotere organisaties en adviesketens',
    features: [
      'Alles uit Pro',
      '7.500+ vragen per maand',
      'Eigen beveiligde omgeving (dedicated)',
      'Volledige compliance & logging',
    ],
  },
};

export default function SignupPage() {
  const navigate = useNavigate();
  const { instance } = useMsal();
  const [selectedPriceId, setSelectedPriceId] = useState<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('selected_price_id') : null,
  );

  // Resolve tier from price id; fall back to popular tier 'groei'
  const selectedTier = useMemo(() => {
    const tier = getTierByPriceId(selectedPriceId);
    return tier ?? 'groei';
  }, [selectedPriceId]);

  // Keep selection in sync with storage changes (e.g., from pricing page)
  useEffect(() => {
    const handler = () => setSelectedPriceId(localStorage.getItem('selected_price_id'));
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const handleChooseDifferent = (tier: 'instap' | 'groei' | 'pro' | 'enterprise') => {
    const priceId = getPriceIdForTier(tier);
    if (priceId) {
      localStorage.setItem('selected_price_id', priceId);
      setSelectedPriceId(priceId);
    }
  };

  const handleBackToPricing = () => navigate('/pricing');

  const hasManualToken = !!localStorage.getItem('b2c_token');
  const msalAccounts = instance.getAllAccounts();
  const isAuthenticated = hasManualToken || msalAccounts.length > 0;

  // If already authenticated, send the user to app or pricing depending on backend logic
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/home', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const tierMeta = TIER_META[selectedTier];

  return (
    <div className="container mx-auto px-4 md:px-6 py-10">
      <div className="mx-auto grid w-full max-w-5xl gap-8 md:grid-cols-2">
        <Card className="order-2 md:order-1">
          <CardHeader>
            <CardTitle>Inloggen en starten</CardTitle>
            <CardDescription>
              Meld je aan met je zakelijke account. We koppelen je proef aan het gekozen pakket.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <LoginCard />
          </CardContent>
          <CardFooter className="flex items-center justify-between">
            <Button variant="ghost" onClick={handleBackToPricing}>
              Terug naar prijzen
            </Button>
            <div className="text-muted-foreground text-sm">
              Al een account? Log in om door te gaan.
            </div>
          </CardFooter>
        </Card>

        <Card className="order-1 md:order-2 border-brand">
          <CardHeader className="pb-2">
            <Badge className="w-max bg-brand text-white">Geselecteerd pakket</Badge>
            <CardTitle className="mt-2">{tierMeta.label}</CardTitle>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-4xl font-bold">{tierMeta.price}</span>
              <span className="text-muted-foreground text-sm">/ {tierMeta.period}</span>
            </div>
            <CardDescription>{tierMeta.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <Separator className="my-3" />
            <ul className="space-y-2 text-sm">
              {tierMeta.features.map(feature => (
                <li key={feature} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
            <Separator className="my-4" />
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant={selectedTier === 'instap' ? 'default' : 'outline'}
                onClick={() => handleChooseDifferent('instap')}
                aria-pressed={selectedTier === 'instap'}
              >
                Instap
              </Button>
              <Button
                className={selectedTier === 'groei' ? 'bg-brand text-white' : ''}
                variant={selectedTier === 'groei' ? 'default' : 'outline'}
                onClick={() => handleChooseDifferent('groei')}
                aria-pressed={selectedTier === 'groei'}
              >
                Groei
              </Button>
              <Button
                variant={selectedTier === 'pro' ? 'default' : 'outline'}
                onClick={() => handleChooseDifferent('pro')}
                aria-pressed={selectedTier === 'pro'}
              >
                Pro
              </Button>
              <Button
                variant={selectedTier === 'enterprise' ? 'default' : 'outline'}
                onClick={() => handleChooseDifferent('enterprise')}
                aria-pressed={selectedTier === 'enterprise'}
              >
                Enterprise
              </Button>
            </div>
          </CardContent>
          <CardFooter>
            <div className="text-muted-foreground text-xs">
              Alle pakketten starten met een gratis proefperiode. Je kunt altijd wisselen.
            </div>
          </CardFooter>
        </Card>
      </div>

      {/* Fallback spinner while MSAL initializes on very first load */}
      {!instance && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      )}
    </div>
  );
}
