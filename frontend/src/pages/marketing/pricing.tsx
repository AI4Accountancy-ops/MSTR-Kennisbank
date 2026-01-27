import { CheckIcon } from 'lucide-react';
import { useNavigate } from 'react-router';
import { useState } from 'react';

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
import HomePageFaq from '@/features/Marketing/components/Homepage/HomePageFaq';

import { startTrialCheckout } from '@features/Billing/services/subscriptionFlow';
import { normalizePlanNameToTier } from '@features/Billing/utils';

export default function PricingSectionCards() {
  const navigate = useNavigate();
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handleSelectPlan = async (planName: string) => {
    if (loadingPlan) return;
    setLoadingPlan(planName);
    try {
      const tier = normalizePlanNameToTier(planName);
      if (!tier) {
        setLoadingPlan(null);
        return;
      }
      await startTrialCheckout(tier);
    } catch {
      setLoadingPlan(null);
    }
  };

  return (
    <>
      {/* Pricing */}
      <div className="container mx-auto px-4 md:px-6 py-8 md:py-16 lg:py-20 ">
        <div className="flex flex-col items-center text-center gap-2 xl:gap-4">
          <h1 className="text-primary leading-tighter max-w-4xl text-4xl font-semibold tracking-tight text-balance lg:leading-[1.1] lg:font-semibold xl:text-5xl xl:tracking-tighter">
            Eenvoudige & transparante tarieven
          </h1>
          <p className="text-foreground max-w-4xl text-base text-balance sm:text-lg">
            Alle abonnementen starten met 7 dagen gratis proef. Geen match = geen abonnement.
          </p>
        </div>

        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-6 items-start">
          {/* Instap */}
          <Card className="flex flex-col lg:self-center lg:min-h-[560px]">
            <CardHeader className="text-center pb-2">
              <CardTitle className="!mb-7">Instap</CardTitle>
              <span className="font-bold text-5xl">€49</span>
              <div className="text-muted-foreground text-sm mt-1">/ maand</div>
            </CardHeader>
            <CardDescription className="text-center w-11/12 mx-auto">
              Voor zelfstandige fiscalisten en kleine kantoren
            </CardDescription>
            <CardContent className="flex-1">
              <ul className="mt-7 space-y-2.5 text-sm">
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">250 vragen per maand</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">
                    Onbeperkt aantal gebruikers in je organisatie
                  </span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">
                    Actuele kennisbank (Belastingdienst & Wetten.overheid)
                  </span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Basis support</span>
                </li>
              </ul>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                variant={'outline'}
                disabled={Boolean(loadingPlan)}
                aria-busy={loadingPlan === 'Instap'}
                onClick={() => void handleSelectPlan('Instap')}
              >
                {loadingPlan === 'Instap' ? 'Even geduld...' : 'Start gratis proef'}
              </Button>
            </CardFooter>
          </Card>
          {/* Groei (meest gekozen) */}
          <Card className="border-brand flex flex-col lg:min-h-[600px]">
            <CardHeader className="text-center pb-2">
              <Badge className="uppercase w-max self-center mb-3 bg-brand text-white">
                Meest gekozen
              </Badge>
              <CardTitle className="!mb-7">Groei</CardTitle>
              <span className="font-bold text-5xl">€149</span>
              <div className="text-muted-foreground text-sm mt-1">/ maand</div>
            </CardHeader>
            <CardDescription className="text-center w-11/12 mx-auto">
              Voor groeiende kantoren en MKB-adviseurs
            </CardDescription>
            <CardContent className="flex-1">
              <ul className="mt-7 space-y-2.5 text-sm">
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Alles uit Instap</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">1.000 vragen per maand</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Toegang tot de websearch feature</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Uitgebreide support</span>
                </li>
              </ul>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full bg-brand text-white"
                disabled={Boolean(loadingPlan)}
                aria-busy={loadingPlan === 'Groei'}
                onClick={() => void handleSelectPlan('Groei')}
              >
                {loadingPlan === 'Groei' ? 'Even geduld...' : 'Start gratis proef'}
              </Button>
            </CardFooter>
          </Card>
          {/* Pro */}
          <Card className="flex flex-col lg:self-center lg:min-h-[560px]">
            <CardHeader className="text-center pb-2">
              <CardTitle className="!mb-7">Pro</CardTitle>
              <span className="font-bold text-5xl">€349</span>
              <div className="text-muted-foreground text-sm mt-1">/ maand</div>
            </CardHeader>
            <CardDescription className="text-center w-11/12 mx-auto">
              Voor middelgrote kantoren met meerdere teams
            </CardDescription>
            <CardContent className="flex-1">
              <ul className="mt-7 space-y-2.5 text-sm">
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Alles uit Groei</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">2.500 vragen per maand</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">
                    Toegang tot beta features & nieuwe innovaties
                  </span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Premium support</span>
                </li>
              </ul>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                variant={'outline'}
                disabled={Boolean(loadingPlan)}
                aria-busy={loadingPlan === 'Pro'}
                onClick={() => void handleSelectPlan('Pro')}
              >
                {loadingPlan === 'Pro' ? 'Even geduld...' : 'Start gratis proef'}
              </Button>
            </CardFooter>
          </Card>
          {/* Enterprise */}
          <Card className="flex flex-col lg:self-center lg:min-h-[560px]">
            <CardHeader className="text-center pb-2">
              <CardTitle className="!mb-7">Enterprise</CardTitle>
              <span className="font-bold text-5xl">€899</span>
              <div className="text-muted-foreground text-sm mt-1">/ vanaf</div>
            </CardHeader>
            <CardDescription className="text-center w-11/12 mx-auto">
              Voor grotere organisaties en adviesketens
            </CardDescription>
            <CardContent className="flex-1">
              <ul className="mt-7 space-y-2.5 text-sm">
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Alles uit Pro</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">7.500+ vragen per maand</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">
                    Eigen beveiligde omgeving (dedicated)
                  </span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Volledige compliance & logging</span>
                </li>
                <li className="flex space-x-2">
                  <CheckIcon className="flex-shrink-0 mt-0.5 h-4 w-4" />
                  <span className="text-muted-foreground">Persoonlijke accountmanager</span>
                </li>
              </ul>
            </CardContent>
            <CardFooter>
              <Button className="w-full" variant={'outline'} onClick={() => navigate('/contact')}>
                Plan een demo
              </Button>
            </CardFooter>
          </Card>
        </div>

        <HomePageFaq />
      </div>
    </>
  );
}
