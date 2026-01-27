import { z } from 'zod';
import { useCallback, useEffect, useMemo } from 'react';
import { useMsal } from '@azure/msal-react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import LogoutButton from '@features/Authentication/components/LogoutButton';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/context/ToastContext';
import { useAccessCheck } from '~/hooks/useAccessCheck';
import { organizationService } from '@/services/organizationService';
import BrandIcon from '@/assets/icons/brand-icon';
import { useZodForm } from '@features/Settings/hooks/useZodForm';
import { startCheckoutWithBackendDecision } from '@features/Billing/services/subscriptionFlow';
import { useOrganizations } from '~/hooks/useOrganizations';

const orgSchema = z.object({
  name: z
    .string()
    .min(2, { message: 'De naam moet minimaal 2 tekens bevatten.' })
    .max(80, { message: 'De naam mag maximaal 80 tekens bevatten.' })
    .trim(),
});

type OrgFormValues = z.infer<typeof orgSchema>;

export default function CreateOrganizationPage() {
  const { instance } = useMsal();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const account = instance.getAllAccounts()[0];
  const userId: string = useMemo(() => {
    if (account?.localAccountId) return account.localAccountId;
    try {
      const raw = localStorage.getItem('b2c_user');
      if (!raw) return '';
      const parsed: { user_id?: string } = JSON.parse(raw);
      return parsed.user_id || '';
    } catch {
      return '';
    }
  }, [account]);

  const { hasAccess, isLoading: accessLoading } = useAccessCheck(userId);
  const { data: myOrgs, isLoading: isOrganizationsLoading } = useOrganizations(userId);

  // Derive best-available email from MSAL, stored user, or token claims
  const derivedEmail: string = useMemo(() => {
    const msalEmail = (account?.username || '').trim();
    if (msalEmail.length > 0) return msalEmail;
    try {
      const raw = localStorage.getItem('b2c_user');
      if (raw) {
        const parsed: { email?: string } = JSON.parse(raw);
        if (parsed.email && parsed.email.trim().length > 0) return parsed.email.trim();
      }
    } catch {
      /* ignore */
    }
    try {
      const idToken = localStorage.getItem('b2c_token');
      if (idToken) {
        const parts = idToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1])) as { email?: string; emails?: string[] };
          const fromClaim = (
            payload.email ||
            (Array.isArray(payload.emails) ? payload.emails[0] : '') ||
            ''
          ).trim();
          if (fromClaim.length > 0) return fromClaim;
        }
      }
    } catch {
      /* ignore */
    }
    return '';
  }, [account]);

  // Derive a reasonable display name
  const derivedName: string = useMemo(() => {
    const msalName = (account?.name || '').trim();
    if (msalName.length > 0) return msalName;
    try {
      const raw = localStorage.getItem('b2c_user');
      if (raw) {
        const parsed: { name?: string; email?: string } = JSON.parse(raw);
        if (parsed.name && parsed.name.trim().length > 0) return parsed.name.trim();
        if (parsed.email && parsed.email.trim().length > 0) return parsed.email.trim();
      }
    } catch {
      /* ignore */
    }
    return 'User';
  }, [account]);

  useEffect(() => {
    const run = async () => {
      if (!userId) return;
      if (accessLoading || isOrganizationsLoading) {
        return;
      }
      const selectedPriceId = localStorage.getItem('selected_price_id') || undefined;
      const authProvider: 'microsoft' | 'google' = account ? 'microsoft' : 'google';

      if (hasAccess) {
        if (myOrgs?.organizations.length && myOrgs.organizations.length > 0) {
          navigate('/chatbot', { replace: true });
        }

        return;
      }

      if (!hasAccess && selectedPriceId) {
        const origin = window.location.origin;
        if (!derivedEmail || derivedEmail.length === 0) {
          showToast('E-mailadres ontbreekt. Log opnieuw in.', 'error');
          navigate('/login', { replace: true });
          return;
        }
        await startCheckoutWithBackendDecision({
          user_id: userId,
          email: derivedEmail,
          name: derivedName,
          auth_provider: authProvider,
          is_subscribed: false,
          selected_price_id: selectedPriceId,
          success_url: `${origin}/billing/success`,
          cancel_url: `${origin}/billing/cancel`,
        });
        return; // navigation handled inside
      }

      if (!selectedPriceId) {
        console.log('No selected price id, redirecting to pricing');
        navigate('/pricing', { replace: true });
        return;
      }
    };
    void run();
  }, [userId, account, navigate, hasAccess, accessLoading, derivedEmail, derivedName, showToast]);

  const form = useZodForm<OrgFormValues>({
    schema: orgSchema,
    defaultValues: { name: '' },
    mode: 'onChange',
  });

  const onSubmit = useCallback(
    async (values: OrgFormValues) => {
      if (!userId) {
        showToast('Gebruiker niet gevonden. Log opnieuw in.', 'error');
        return;
      }
      try {
        const res = await organizationService.createOrganization({
          owner_user_id: userId,
          name: values.name.trim(),
        });
        if (res.status === 'success') {
          // Ensure all dependent views see the new organization immediately
          await queryClient.invalidateQueries({ queryKey: ['organizations', 'mine', userId] });
          await queryClient.invalidateQueries({ queryKey: ['access', 'check', userId] });

          if (hasAccess) {
            navigate('/chatbot', { replace: true });
            return;
          }

          // After org creation: if a plan was pre-selected, continue checkout; otherwise go to pricing
          const selectedPriceId = localStorage.getItem('selected_price_id') || undefined;
          if (selectedPriceId) {
            const origin = window.location.origin;
            if (!derivedEmail || derivedEmail.length === 0) {
              showToast('E-mailadres ontbreekt. Log opnieuw in.', 'error');
              navigate('/login', { replace: true });
              return;
            }
            await startCheckoutWithBackendDecision({
              user_id: userId,
              email: derivedEmail,
              name: derivedName,
              auth_provider: 'microsoft',
              is_subscribed: false,
              selected_price_id: selectedPriceId,
              success_url: `${origin}/billing/success`,
              cancel_url: `${origin}/billing/cancel`,
            });
            return; // navigation handled inside
          }
          navigate('/pricing', { replace: true });
          return;
        }
        showToast('Aanmaken van organisatie mislukt.', 'error');
      } catch {
        showToast('Aanmaken van organisatie mislukt.', 'error');
      }
    },
    [userId, showToast, navigate, account],
  );

  const {
    handleSubmit,
    register,
    formState: { isSubmitting, errors },
  } = form;

  return (
    <>
      <div className="flex items-center gap-2 p-4">
        <LogoutButton />
        <BrandIcon className="size-8" />
        <span className="sr-only">AI4Accountancy</span>
      </div>
      <div className="container mx-auto min-h-screen p-6">
        <div className="flex min-h-[70vh] items-center justify-center">
          {accessLoading ? (
            <div className="text-muted-foreground">Bezig met controleren…</div>
          ) : (
            <Card className="w-full max-w-lg">
              <CardHeader>
                <CardTitle>Organisatie aanmaken</CardTitle>
                <CardDescription>
                  Welkom! Laten we je organisatie aanmaken zodat je direct aan de slag kunt.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
                  <div className="space-y-2">
                    <Label htmlFor="org-name">Naam van de organisatie</Label>
                    <Input id="org-name" placeholder="Bijv. Fiscus Advies" {...register('name')} />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name.message}</p>
                    )}
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => navigate('/home')}>
                      Annuleren
                    </Button>
                    <Button type="submit" disabled={isSubmitting}>
                      {isSubmitting ? 'Bezig…' : 'Aanmaken'}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
