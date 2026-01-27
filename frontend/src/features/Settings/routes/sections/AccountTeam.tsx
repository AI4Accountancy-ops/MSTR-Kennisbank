import { useEffect, useState } from 'react';
import { CopyIcon, CheckIcon, RefreshCcwIcon, TrashIcon } from 'lucide-react';
import { z } from 'zod';

import LoadingState from '@features/Settings/components/LoadingState';
import ErrorState from '@features/Settings/components/ErrorState';
import { orgProfileSchema } from '@features/Settings/schemas';
import { useZodForm } from '@features/Settings/hooks/useZodForm';
import {
  useMembers,
  useOrg,
  useMyOrganizations,
  useCreateOrganization,
  useActiveOrganizationDetails,
} from '@features/Settings/hooks/useSettingsQueries';

import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';
import { Separator } from '~/components/ui/separator';
import { useToast } from '~/context/ToastContext';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';

const formSchema = orgProfileSchema.pick({ name: true, vatNumber: true, billingAddress: true });

export default function AccountTeam() {
  const { showToast } = useToast();
  const myOrgs = useMyOrganizations();
  const createOrg = useCreateOrganization();
  const activeOrg = useActiveOrganizationDetails();
  const { org, updateOrg } = useOrg();
  const { list: members, invite, regenerateInvite, changeRole, remove } = useMembers();
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteLink, setInviteLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');

  const form = useZodForm<{ name: string; vatNumber?: string; billingAddress?: string }>({
    schema: formSchema as z.ZodType<{ name: string; vatNumber?: string; billingAddress?: string }>,
    defaultValues: { name: '', vatNumber: '', billingAddress: '' },
    mode: 'onChange',
  });

  useEffect(() => {
    if (org.data) {
      form.reset({
        name: org.data.name,
        vatNumber: '',
        billingAddress: '',
      });
    }
    // If orgService data isn’t ready but activeOrg from backend exists, use that for name
    if (!org.data && activeOrg.data) {
      form.reset({
        name: activeOrg.data.name ?? '',
        vatNumber: '',
        billingAddress: '',
      });
    }
  }, [org.data, activeOrg.data, form]);

  const onSubmit = form.handleSubmit(() => {
    // Placeholder: backend update endpoint not available yet; show toast only
    showToast('Organisatie bijgewerkt', 'success');
  });

  // If user has no organizations yet, show create organization form
  if (!myOrgs.isLoading && (myOrgs.data?.length ?? 0) === 0) {
    return (
      <section className="space-y-4">
        <div>
          <h3 className="text-xl font-semibold">Organisatie aanmaken</h3>
          <p className="text-muted-foreground">Maak je eerste organisatie aan om te starten.</p>
        </div>

        <Card>
          <CardContent>
            <form
              className="grid gap-4 max-w-lg"
              onSubmit={e => {
                e.preventDefault();
                if (newOrgName.trim().length === 0) return;
                createOrg.mutate(newOrgName, {
                  onSuccess: () => {
                    setNewOrgName('');
                    showToast('Organisatie aangemaakt', 'success');
                    myOrgs.refetch();
                  },
                });
              }}
            >
              <div className="grid gap-2">
                <Label htmlFor="orgName">Organisatienaam</Label>
                <Input
                  id="orgName"
                  placeholder="Mijn Organisatie"
                  value={newOrgName}
                  onChange={e => setNewOrgName(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button type="submit" disabled={createOrg.isPending}>
                  Aanmaken
                </Button>
                {createOrg.isPending && (
                  <span className="text-sm text-muted-foreground">Bezig met aanmaken…</span>
                )}
              </div>
            </form>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-xl font-semibold">Account & Team</h3>
        <p className="text-muted-foreground">Beheer organisatieprofiel en teamleden.</p>
      </div>

      <Card>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-4">
            <div className="grid grid-cols-2 gap-2">
              <Label htmlFor="name">Organisatienaam</Label>
              <Input id="name" {...form.register('name')} placeholder="Exactify B.V." />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
              )}
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-2">
              <Label htmlFor="vatNumber">BTW-nummer</Label>
              <Input id="vatNumber" {...form.register('vatNumber')} placeholder="NL123456789B01" />
              {form.formState.errors.vatNumber && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.vatNumber.message}
                </p>
              )}
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-2">
              <Label htmlFor="billingAddress">Factuuradres</Label>
              <Input
                id="billingAddress"
                {...form.register('billingAddress')}
                placeholder="Straat 1, Plaats"
              />
              {form.formState.errors.billingAddress && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.billingAddress.message}
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-2">
              <Button type="submit" size="sm" disabled={updateOrg.isPending || org.isLoading}>
                Opslaan
              </Button>
              {updateOrg.isPending && (
                <span className="text-sm text-muted-foreground">Bezig met opslaan…</span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <div>
        <h4 className="text-lg font-semibold">Teamleden</h4>
        <p className="text-muted-foreground text-sm">
          Nodig leden uit, wijzig rollen of verwijder toegang.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3">
          <div className="flex items-end gap-2">
            <div className="grid gap-2 w-full max-w-md">
              <Label htmlFor="inviteEmail">E-mailadres uitnodigen</Label>
              <Input
                id="inviteEmail"
                type="email"
                placeholder="naam@example.nl"
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)}
              />
            </div>
            <Button
              type="button"
              size="sm"
              disabled={invite.isPending || inviteEmail.trim().length === 0}
              onClick={() =>
                invite.mutate(inviteEmail, {
                  onSuccess: () => {
                    setInviteEmail('');
                    showToast('Uitnodiging verzonden', 'success');
                    // Maak een mock uitnodigingslink (fase 1)
                    const link = `${window.location.origin}/uitnodigen?email=${encodeURIComponent(
                      inviteEmail,
                    )}`;
                    setInviteLink(link);
                    setCopied(false);
                    setInviteOpen(true);
                    members.refetch();
                  },
                  onError: err =>
                    showToast(
                      String((err as { message?: string }).message ?? 'Uitnodigen mislukt'),
                      'error',
                    ),
                })
              }
            >
              Uitnodigen
            </Button>
          </div>

          <Separator />

          <div className="overflow-x-auto">
            {members.isLoading ? (
              <LoadingState message="Teamleden laden..." skeletonLines={2} />
            ) : members.isError ? (
              <ErrorState onRetry={() => members.refetch()} />
            ) : members.data && members.data.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nog geen teamleden gevonden.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-muted-foreground">
                  <tr>
                    <th className="py-2 pr-4">Naam</th>
                    <th className="py-2 pr-4">E-mail</th>
                    <th className="py-2 pr-4">Rol</th>
                    <th className="py-2 pr-4 text-right">Acties</th>
                  </tr>
                </thead>
                <tbody>
                  {members.data?.map(m => (
                    <tr key={m.id} className="border-t">
                      <td className="py-2 pr-4">—</td>
                      <td className="py-2 pr-4">—</td>
                      <td className="py-2 pr-4">
                        <Select
                          value={m.role}
                          onValueChange={val =>
                            changeRole.mutate(
                              { memberId: m.id, role: val === 'admin' ? 'admin' : 'user' },
                              {
                                onSuccess: () => showToast('Rol bijgewerkt', 'success'),
                                onError: err =>
                                  showToast(
                                    String(
                                      (err as { message?: string }).message ?? 'Bijwerken mislukt',
                                    ),
                                    'error',
                                  ),
                              },
                            )
                          }
                        >
                          <SelectTrigger className="w-[140px]">
                            <SelectValue placeholder="Rol" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Beheerder</SelectItem>
                            <SelectItem value="user">Lid</SelectItem>
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="py-2 pr-4 text-right space-x-2">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() =>
                            regenerateInvite.mutate(m.id, {
                              onSuccess: () => showToast('Uitnodiging vernieuwd', 'success'),
                              onError: err =>
                                showToast(
                                  String(
                                    (err as { message?: string }).message ?? 'Vernieuwen mislukt',
                                  ),
                                  'error',
                                ),
                            })
                          }
                        >
                          <RefreshCcwIcon className="size-4" />
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() =>
                            remove.mutate(m.id, {
                              onSuccess: () => showToast('Lid verwijderd', 'success'),
                              onError: err =>
                                showToast(
                                  String(
                                    (err as { message?: string }).message ?? 'Verwijderen mislukt',
                                  ),
                                  'error',
                                ),
                            })
                          }
                        >
                          <TrashIcon className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Uitnodiging verstuurd</DialogTitle>
            <DialogDescription>
              Kopieer de uitnodigingslink en deel deze met de nieuwe gebruiker.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-2">
            <Label htmlFor="inviteLink">Uitnodigingslink</Label>
            <div className="flex items-center gap-2">
              <Input id="inviteLink" value={inviteLink} readOnly className="flex-1" />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(inviteLink);
                    setCopied(true);
                    showToast('Link gekopieerd', 'success');
                  } catch {
                    showToast('Kopiëren mislukt', 'error');
                  }
                }}
                aria-label="Kopieer link"
              >
                {copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" onClick={() => setInviteOpen(false)}>
              Sluiten
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
