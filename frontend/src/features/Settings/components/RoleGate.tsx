import { ReactNode } from 'react';
import { Lock } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';

import { useCurrentUser } from '../hooks/useCurrentUser';
import type { UserRole } from '../types';

interface RoleGateProps {
  children: ReactNode;
  requiredRole: UserRole;
  fallback?: ReactNode;
  className?: string;
}

const ROLE_HIERARCHY: Record<UserRole, number> = {
  member: 1,
  admin: 2,
  owner: 3,
};

const ROLE_LABELS: Record<UserRole, string> = {
  member: 'Lid',
  admin: 'Beheerder',
  owner: 'Eigenaar',
};

export default function RoleGate({
  children,
  requiredRole,
  fallback,
  className = '',
}: RoleGateProps) {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading) {
    return <div className={`opacity-50 ${className}`}>{children}</div>;
  }

  const userRole = user?.role || 'member';
  const hasAccess = ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];

  if (hasAccess) {
    return <div className={className}>{children}</div>;
  }

  if (fallback) {
    return <div className={className}>{fallback}</div>;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Disabled children */}
      <div className="opacity-50 pointer-events-none">{children}</div>

      {/* Access denied prompt */}
      <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/20">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="border-red-300 text-red-700 dark:border-red-700 dark:text-red-300"
                >
                  Toegang geweigerd
                </Badge>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        <Lock className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs">
                      <div className="space-y-2">
                        <p className="font-medium">Onvoldoende rechten</p>
                        <div className="text-xs space-y-1">
                          <p>
                            <strong>Uw rol:</strong> {ROLE_LABELS[userRole]}
                          </p>
                          <p>
                            <strong>Vereiste rol:</strong> {ROLE_LABELS[requiredRole]}
                          </p>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Neem contact op met een beheerder om toegang te krijgen.
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              <p className="text-sm text-red-700 dark:text-red-300">
                U heeft onvoldoende rechten om deze functie te gebruiken.
                {requiredRole === 'owner' && ' Alleen de eigenaar heeft toegang tot deze functie.'}
                {requiredRole === 'admin' &&
                  ' Alleen beheerders en eigenaren hebben toegang tot deze functie.'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
