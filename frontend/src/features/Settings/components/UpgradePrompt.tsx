import { Link } from 'react-router';
import { ArrowRight, Crown, Zap } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';

import type { PlanTier } from '../types';

interface UpgradePromptProps {
  requiredPlan: PlanTier;
  featureName: string;
  featureDescription?: string;
  currentUsage?: number;
  usageLimit?: number;
  variant?: 'badge' | 'card' | 'inline';
  className?: string;
}

const PLAN_LABELS: Record<PlanTier, string> = {
  instap: 'Instap',
  groei: 'Groei',
  pro: 'Pro',
  enterprise: 'Enterprise',
};

const PLAN_ICONS: Record<PlanTier, React.ComponentType<{ className?: string }>> = {
  instap: Crown,
  groei: Crown,
  pro: Zap,
  enterprise: Crown,
};

const PLAN_FEATURES: Record<PlanTier, string[]> = {
  instap: ['250 vragen per maand', 'Basis AI-chat', 'E-mail support'],
  groei: ['1.000 vragen per maand', 'Slimme assistent', 'E-mail + chat support'],
  pro: ['2.500 vragen per maand', 'Web zoeken', 'Premium support', 'Rapportage'],
  enterprise: ['7.500+ vragen per maand', 'Alle functies', 'Dedicated omgeving', 'Accountmanager'],
};

export default function UpgradePrompt({
  requiredPlan,
  featureName,
  featureDescription,
  currentUsage,
  usageLimit,
  variant = 'badge',
  className = '',
}: UpgradePromptProps) {
  const isUsageLimited = usageLimit && currentUsage && currentUsage >= usageLimit;
  const Icon = PLAN_ICONS[requiredPlan];

  const getUpgradeMessage = () => {
    if (isUsageLimited) {
      return `Limiet bereikt (${currentUsage}/${usageLimit})`;
    }
    return `Vereist ${PLAN_LABELS[requiredPlan]}`;
  };

  const getUpgradeDescription = () => {
    if (isUsageLimited) {
      return 'Upgrade voor hogere limieten';
    }
    return `Upgrade naar ${PLAN_LABELS[requiredPlan]} plan`;
  };

  if (variant === 'badge') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className={`cursor-pointer hover:bg-primary/10 ${className}`}>
              <Icon className="h-3 w-3 mr-1" />
              {getUpgradeMessage()}
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <div className="space-y-2">
              <p className="font-medium">{featureName}</p>
              {featureDescription && <p className="text-sm">{featureDescription}</p>}
              <div className="text-xs space-y-1">
                <p>
                  <strong>{PLAN_LABELS[requiredPlan]} plan bevat:</strong>
                </p>
                <ul className="list-disc list-inside space-y-0.5">
                  {PLAN_FEATURES[requiredPlan].slice(0, 3).map((feature, index) => (
                    <li key={index}>{feature}</li>
                  ))}
                </ul>
              </div>
              <Button asChild size="sm" className="w-full mt-2">
                <Link to="/pricing">
                  Bekijk prijzen
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              </Button>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (variant === 'card') {
    return (
      <Card
        className={`border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 ${className}`}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Icon className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-300"
                >
                  {getUpgradeMessage()}
                </Badge>
              </div>

              <p className="text-sm text-amber-700 dark:text-amber-300">
                {getUpgradeDescription()}
              </p>

              <Button asChild size="sm" className="bg-amber-600 hover:bg-amber-700 text-white">
                <Link to="/pricing">
                  Upgrade naar {PLAN_LABELS[requiredPlan]}
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Inline variant
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Badge variant="outline" className="text-xs">
        <Icon className="h-3 w-3 mr-1" />
        {getUpgradeMessage()}
      </Badge>
      <Button asChild variant="ghost" size="sm" className="h-6 px-2 text-xs">
        <Link to="/pricing">
          Upgrade
          <ArrowRight className="h-3 w-3 ml-1" />
        </Link>
      </Button>
    </div>
  );
}
