import { Link, useNavigate } from 'react-router';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { CheckIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { startTrialCheckout } from '@features/Billing/services/subscriptionFlow';
import { normalizePlanNameToTier } from '@features/Billing/utils';

// Strongly type each pricing plan for clarity and safety
type PricingPlan = {
  name: string;
  price: string;
  description: string;
  features: string[];
  cta: string;
  ctaLink: string;
  popular: boolean;
  type: 'maand' | 'vanaf';
};

// Updated pricing plans (Dutch content)
const plans: PricingPlan[] = [
  {
    name: 'Instap',
    price: '€49',
    description: 'Voor zelfstandige fiscalisten en kleine kantoren',
    features: [
      '250 vragen per maand',
      'Direct toegang tot de AI-chat',
      'Actuele kennisbank (Belastingdienst & Wetten.overheid)',
      'Basis support (e-mail)',
    ],
    cta: 'Start gratis proef',
    ctaLink: '/signup',
    popular: false,
    type: 'maand',
  },
  {
    name: 'Groei',
    price: '€149',
    description: 'Voor groeiende kantoren en MKB-adviseurs',
    features: [
      '1.000 vragen per maand',
      'Slimme assistent voor dagelijkse fiscale vragen',
      'Snelle toegang tot bronnen en uitleg',
      'Uitgebreide support (e-mail + chat)',
    ],
    cta: 'Start gratis proef',
    ctaLink: '/signup',
    popular: true,
    type: 'maand',
  },
  {
    name: 'Pro',
    price: '€349',
    description: 'Voor middelgrote kantoren met meerdere teams',
    features: [
      '2.500 vragen per maand',
      'Extra functies voor grotere teams',
      'Meer inzicht in gebruik & rapportage',
      'Premium support',
    ],
    cta: 'Start gratis proef',
    ctaLink: '/signup',
    popular: false,
    type: 'maand',
  },
  {
    name: 'Enterprise',
    price: '€899',
    description: 'Voor grotere organisaties en adviesketens',
    features: [
      '7.500+ vragen per maand',
      'Eigen beveiligde omgeving (dedicated)',
      'Volledige compliance & logging',
      'Persoonlijke accountmanager',
    ],
    cta: 'Plan een demo',
    ctaLink: '/demo',
    popular: false,
    type: 'vanaf',
  },
];

export default function HomePagePricing() {
  const navigate = useNavigate();
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handleSelectPlan = async (planName: string) => {
    setLoadingPlan(planName);
    try {
      const tier = normalizePlanNameToTier(planName);
      if (!tier) {
        setLoadingPlan(null);
        navigate('/pricing');
        return;
      }
      await startTrialCheckout(tier);
    } catch {
      setLoadingPlan(null);
      navigate('/pricing');
    }
  };

  return (
    <section className="w-full py-12 md:py-24 bg-muted/30">
      <div className="container mx-auto px-4 md:px-6 2xl:max-w-[1400px]">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <h2 className="text-4xl font-semibold tracking-tight text-pretty text-primary sm:text-5xl mb-2">
              Eenvoudige, transparante prijzen
            </h2>
            <p className="text-foreground mx-auto pt-2 text-base max-w-[700px] sm:text-lg">
              Kies het pakket dat het beste bij je past.
            </p>
          </div>
        </div>
        <div className="mx-auto mt-12 grid max-w-5xl gap-8 md:grid-cols-2 lg:grid-cols-4">
          {plans.map(plan => (
            <div
              key={plan.name}
              className={`relative flex flex-col rounded-xl border p-6 ${
                plan.popular ? 'border-brand' : 'border-border'
              }`}
            >
              {plan.popular && (
                <div className="bg-brand text-primary-foreground absolute -top-3 right-0 left-0 mx-auto w-fit rounded-full px-3 py-1 text-xs font-medium">
                  Meest gekozen
                </div>
              )}
              <div className="mb-4">
                <h3 className="text-xl font-bold">{plan.name}</h3>
                <p className="text-muted-foreground text-sm">{plan.description}</p>
              </div>
              <div className="mb-4 flex items-baseline">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-muted-foreground ml-1 text-sm">/ {plan.type}</span>
              </div>
              <Separator className="my-4" />
              <ul className="mb-8 space-y-3 text-sm">
                {plan.features.map(feature => (
                  <li key={feature} className="flex items-start gap-2">
                    <span className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center text-primary">
                      <CheckIcon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <span className="flex-1">{feature}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-auto">
                <Button
                  className={cn('w-full', plan.popular && 'bg-brand')}
                  variant={plan.popular ? 'default' : 'outline'}
                  disabled={loadingPlan === plan.name}
                  aria-busy={loadingPlan === plan.name}
                  onClick={() => void handleSelectPlan(plan.name)}
                >
                  {loadingPlan === plan.name ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Even geduld...
                    </span>
                  ) : (
                    plan.cta
                  )}
                </Button>
              </div>
            </div>
          ))}
        </div>
        <div className="text-muted-foreground mt-12 text-center text-sm">
          Alle pakketten bevatten een gratis proefperiode van 7 dagen. Geen creditcard vereist.{' '}
          <Link to="/pricing" className="underline underline-offset-4">
            Bekijk alle prijsdetails
          </Link>
        </div>
      </div>
    </section>
  );
}
