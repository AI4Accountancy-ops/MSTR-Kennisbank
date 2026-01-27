import { Link } from 'react-router';
import { Info, Lock } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';

import { useActiveOrganizationDetails, useMyOrganizations } from '../hooks/useSettingsQueries';
import { useUsageSummary } from '~/hooks/useUsageSummary';
import { getUserId } from '@features/Authentication/utils';
import { planPriceIds } from '@features/Billing/constants';

import type { PlanTier } from '../types';

interface PlanGateProps {
  children: React.ReactNode;
  requiredPlan: PlanTier;
  featureName: string;
  featureDescription?: string;
  currentUsage?: number;
  usageLimit?: number;
  className?: string;
}

const PLAN_HIERARCHY: Record<PlanTier, number> = {
  instap: 1,
  groei: 2,
  pro: 3,
  enterprise: 4,
};

const PLAN_LABELS: Record<PlanTier, string> = {
  instap: 'Instap',
  groei: 'Groei',
  pro: 'Pro',
  enterprise: 'Enterprise',
};

/**
 * Map Stripe price ID to plan tier using the actual price IDs from constants.
 * Returns null if the price ID is not recognized.
 */
const mapStripePriceIdToTier = (stripePriceId: string | undefined): PlanTier | null => {
  if (!stripePriceId) return null;
  // Map Stripe price IDs to plan tiers using actual constants
  if (stripePriceId === planPriceIds.instap) return 'instap';
  if (stripePriceId === planPriceIds.groei) return 'groei';
  if (stripePriceId === planPriceIds.pro) return 'pro';
  if (stripePriceId === planPriceIds.enterprise) return 'enterprise';
  return null;
};

export default function PlanGate({
  children,
  requiredPlan,
  featureName,
  featureDescription,
  currentUsage,
  usageLimit,
  className = '',
}: PlanGateProps) {
  const { data: org, isLoading: orgLoading } = useActiveOrganizationDetails();
  const { data: myOrgs, isLoading: myOrgsLoading } = useMyOrganizations();
  const userId = getUserId();
  const { data: usage } = useUsageSummary(userId, org?.id);

  if (orgLoading || myOrgsLoading) {
    return <div className={`opacity-50 ${className}`}>{children}</div>;
  }

  const mapQuotaToTier = (quota: number | undefined): PlanTier | null => {
    if (typeof quota !== 'number' || quota <= 0) return null;
    if (quota === 250) return 'instap';
    if (quota === 1000) return 'groei';
    if (quota === 2500) return 'pro';
    if (quota === 7500) return 'enterprise';
    return null;
  };

  // Get stripe_price_id from first organization
  const firstOrg = myOrgs && myOrgs.length > 0 ? myOrgs[0] : null;

  // Determine current plan tier: stripe_price_id > monthly_quota > default to instap
  const currentPlanTier: PlanTier =
    (firstOrg ? mapStripePriceIdToTier(firstOrg.stripe_price_id) : null) ||
    mapQuotaToTier(usage?.monthly_quota) ||
    'instap';

  const hasAccess = PLAN_HIERARCHY[currentPlanTier] >= PLAN_HIERARCHY[requiredPlan];
  const isUsageLimited = usageLimit && currentUsage && currentUsage >= usageLimit;

  // If user has access and no usage limits exceeded, render children normally
  if (hasAccess && !isUsageLimited) {
    return <div className={className}>{children}</div>;
  }

  // Determine the upgrade message
  const getUpgradeMessage = () => {
    if (isUsageLimited) {
      return `Gebruikslimiet bereikt (${currentUsage}/${usageLimit}). Upgrade voor hogere limieten.`;
    }

    if (requiredPlan === 'pro') {
      return 'Vereist Pro plan of hoger';
    } else if (requiredPlan === 'enterprise') {
      return 'Vereist Enterprise plan';
    }

    return `Vereist ${PLAN_LABELS[requiredPlan]} plan`;
  };

  const getUpgradeTarget = () => {
    if (isUsageLimited) {
      // If usage limited, suggest next tier up
      const currentTier = PLAN_HIERARCHY[currentPlanTier];
      if (currentTier < PLAN_HIERARCHY.pro) return 'pro';
      if (currentTier < PLAN_HIERARCHY.enterprise) return 'enterprise';
    }
    return requiredPlan;
  };

  const upgradeTarget = getUpgradeTarget();

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Disabled children */}
      <div className="opacity-50 pointer-events-none">{children}</div>

      {/* Upgrade prompt */}
      <Card className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-300"
                >
                  {isUsageLimited ? 'Limiet bereikt' : 'Upgrade vereist'}
                </Badge>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        <Info className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs">
                      <div className="space-y-2">
                        <p className="font-medium">{featureName}</p>
                        {featureDescription && <p className="text-sm">{featureDescription}</p>}
                        <div className="text-xs space-y-1">
                          <p>
                            <strong>Huidig plan:</strong> {PLAN_LABELS[currentPlanTier]}
                          </p>
                          <p>
                            <strong>Vereist plan:</strong> {PLAN_LABELS[upgradeTarget]}
                          </p>
                          {isUsageLimited && (
                            <p>
                              <strong>Gebruik:</strong> {currentUsage}/{usageLimit}
                            </p>
                          )}
                        </div>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              <p className="text-sm text-amber-700 dark:text-amber-300">{getUpgradeMessage()}</p>

              <Button asChild size="sm" className="bg-amber-600 hover:bg-amber-700 text-white">
                <Link to="/pricing">Upgrade naar {PLAN_LABELS[upgradeTarget]}</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
