import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { useSecurity, usePlanQuery, useAudit } from '@features/Settings/hooks/useSettingsQueries';
import { useSettingsLayout } from '../../components/SettingsLayout';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';

import { Button } from '~/components/ui/button';
import { Label } from '~/components/ui/label';
import { Switch } from '~/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';
import { Input } from '~/components/ui/input';

import { securitySettingsSchema, type SecuritySettingsInput } from '../../schemas';

export default function Security() {
  const { setContentWidthClass } = useSettingsLayout();
  useEffect(() => {
    setContentWidthClass('w-[70%] max-w-6xl');
    return () => setContentWidthClass('w-[50%] max-w-5xl');
  }, [setContentWidthClass]);

  // Data queries
  const { data: plan } = usePlanQuery();
  const { settings, updateSettings, testSAML, exportMyData, deleteMyData } = useSecurity();

  // RHF setup with schema and defaults
  const form = useForm<SecuritySettingsInput>({
    resolver: zodResolver(securitySettingsSchema),
    defaultValues: settings.data,
    mode: 'onChange',
  });

  // Keep form in sync with server data
  useEffect(() => {
    if (settings.data) {
      form.reset(settings.data);
    }
  }, [settings.data, form]);

  // Audit logs pagination
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;
  const { audit } = useAudit(page, pageSize);
  const [auditSearch, setAuditSearch] = useState<string>('');
  const [showDelete, setShowDelete] = useState<boolean>(false);
  const pageCount = useMemo(() => {
    const total = audit.data?.total ?? 0;
    return Math.max(1, Math.ceil(total / pageSize));
  }, [audit.data?.total]);
  const canPrev = page > 1;
  const canNext = page < pageCount;

  const isEnterprise = plan?.tier === 'enterprise';

  const onSubmit = form.handleSubmit(values => {
    updateSettings.mutate(values);
  });

  if (settings.isLoading) {
    return <LoadingState message="Gegevens laden..." skeletonLines={3} />;
  }
  if (settings.error) {
    return (
      <ErrorState
        title="Fout bij laden"
        description="Er ging iets mis bij het ophalen van de beveiligingsinstellingen."
      />
    );
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h3 className="text-xl font-semibold">Beveiliging & Compliance</h3>
        <p className="text-muted-foreground">
          Beheer aanmeldingsbeveiliging, gegevenslocatie, bewaartermijnen en SAML-instellingen.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Beveiligingsinstellingen</CardTitle>
          <CardDescription>Pas authenticatie en gegevensinstellingen aan.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={onSubmit} aria-label="Beveiligingsformulier">
            {/* 2FA - Always enabled */}
            <div className="flex items-center justify-between rounded-md border p-4">
              <div>
                <Label htmlFor="twoFactorEnabled">Tweefactorauthenticatie</Label>
                <p className="text-muted-foreground text-sm">
                  Extra beveiliging bij het inloggen voor alle gebruikers. (Altijd ingeschakeld)
                </p>
              </div>
              <Switch
                id="twoFactorEnabled"
                checked={true}
                disabled={true}
                aria-label="Tweefactorauthenticatie is altijd ingeschakeld"
              />
            </div>

            {/* Data residency - Always EU */}
            <div className="rounded-md border p-4">
              <Label>Gegevenslocatie</Label>
              <p className="text-muted-foreground mb-2 text-sm">
                Gegevens worden altijd opgeslagen in de EU. (Niet wijzigbaar)
              </p>
              <Select value="eu" disabled={true}>
                <SelectTrigger aria-label="Gegevenslocatie is altijd EU">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="eu">EU</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* SAML for Enterprise */}
            {isEnterprise ? (
              <div className="space-y-4 rounded-md border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="samlEnabled">SAML Single Sign-On</Label>
                    <p className="text-muted-foreground text-sm">
                      Configureer SAML SSO voor centrale toegang en beheer.
                    </p>
                  </div>
                  <Switch
                    id="samlEnabled"
                    checked={Boolean(settings.data?.samlEnabled)}
                    onCheckedChange={checked => updateSettings.mutate({ samlEnabled: checked })}
                    disabled={updateSettings.isPending}
                    aria-busy={updateSettings.isPending}
                    aria-label="Schakel SAML in of uit"
                  />
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <Label htmlFor="entityId">Entiteit-ID</Label>
                    <Input
                      id="entityId"
                      placeholder="urn:example:idp"
                      {...form.register('saml.entityId')}
                    />
                  </div>
                  <div>
                    <Label htmlFor="acsUrl">ACS URL</Label>
                    <Input
                      id="acsUrl"
                      placeholder="https://.../acs"
                      {...form.register('saml.acsUrl')}
                    />
                  </div>
                  <div>
                    <Label htmlFor="metadataUrl">Metadata URL</Label>
                    <Input
                      id="metadataUrl"
                      placeholder="https://.../metadata.xml"
                      {...form.register('saml.metadataUrl')}
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button
                    type="submit"
                    disabled={!form.formState.isDirty || updateSettings.isPending}
                  >
                    Opslaan
                  </Button>
                  <Button
                    type="button"
                    className="ml-2"
                    variant="outline"
                    onClick={() => {
                      const saml = form.getValues('saml') || {};
                      testSAML.mutate({
                        entityId: saml.entityId,
                        acsUrl: saml.acsUrl,
                        metadataUrl: saml.metadataUrl,
                      });
                    }}
                    disabled={testSAML.isPending}
                    aria-busy={testSAML.isPending}
                  >
                    {testSAML.isPending ? 'Verbinding testen…' : 'Test verbinding'}
                  </Button>
                </div>
              </div>
            ) : null}
          </form>
        </CardContent>
      </Card>

      {/* Audit logs */}
      <Card>
        <CardHeader>
          <CardTitle>Auditlogs</CardTitle>
          <CardDescription>Overzicht van recente acties binnen de organisatie.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Zoeken in audit (gebruiker/actie/doel)"
              value={auditSearch}
              onChange={e => setAuditSearch(e.target.value)}
              aria-label="Zoeken in audit"
              className="w-72"
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                const rows = audit.data?.rows ?? [];
                const headers = ['tijdstip', 'gebruiker', 'actie', 'doel'];
                const csvRows = rows.map(r => [
                  new Date(r.timestamp).toISOString(),
                  r.actorEmail,
                  r.action,
                  r.target ?? '',
                ]);
                const lines = [headers, ...csvRows]
                  .map(cols =>
                    cols
                      .map(c => {
                        const escaped = String(c).replace(/"/g, '""');
                        return `"${escaped}"`;
                      })
                      .join(','),
                  )
                  .join('\n');
                const blob = new Blob([lines], { type: 'text/csv;charset=utf-8;' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `auditlogs_pagina_${page}.csv`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Exporteer CSV (huidige pagina)
            </Button>
          </div>
          {audit.isLoading ? (
            <LoadingState message="Auditlogs laden..." skeletonLines={2} />
          ) : audit.error ? (
            <ErrorState title="Fout bij laden" description="Kon auditlogs niet laden." />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tijdstip</TableHead>
                    <TableHead>Gebruiker</TableHead>
                    <TableHead>Actie</TableHead>
                    <TableHead>Doel</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(audit.data?.rows ?? [])
                    .filter(row => {
                      const q = auditSearch.trim().toLowerCase();
                      if (q.length === 0) return true;
                      const hay =
                        `${row.actorEmail} ${row.action} ${row.target ?? ''}`.toLowerCase();
                      return hay.includes(q);
                    })
                    .map(row => (
                      <TableRow key={row.id}>
                        <TableCell>
                          {new Date(row.timestamp).toLocaleString('nl-NL', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </TableCell>
                        <TableCell>{row.actorEmail}</TableCell>
                        <TableCell>{row.action}</TableCell>
                        <TableCell>{row.target ?? '—'}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
                <TableCaption>
                  {(audit.data?.total ?? 0) === 0
                    ? 'Geen auditlogs gevonden'
                    : 'Voorbeeldgegevens — daadwerkelijke logs volgen later.'}
                </TableCaption>
              </Table>

              <div className="flex items-center justify-between">
                <div className="text-xs text-muted-foreground">
                  {(audit.data?.total ?? 0) > 0
                    ? `Pagina ${page} van ${pageCount} — ${audit.data?.total ?? 0} totaal`
                    : 'Geen resultaten'}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canPrev}
                    onClick={() => setPage(v => Math.max(1, v - 1))}
                  >
                    Vorige
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!canNext}
                    onClick={() => setPage(v => Math.min(pageCount, v + 1))}
                  >
                    Volgende
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Data beheer */}
      <Card>
        <CardHeader>
          <CardTitle>Gegevensbeheer</CardTitle>
          <CardDescription>Beheer uw persoonlijke gegevens conform AVG/GDPR.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => exportMyData.mutate()}
            disabled={exportMyData.isPending}
            aria-busy={exportMyData.isPending}
          >
            {exportMyData.isPending ? 'Exporteren…' : 'Download mijn gegevens'}
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowDelete(true)}
            disabled={deleteMyData.isPending}
          >
            Verwijder mijn gegevens
          </Button>
        </CardContent>
      </Card>

      {/* Delete confirm dialog */}
      <Dialog open={showDelete} onOpenChange={setShowDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Gegevens definitief verwijderen?</DialogTitle>
            <DialogDescription>
              Deze actie verwijdert permanent alle gegevens die aan uw account zijn gekoppeld. Dit
              kan niet ongedaan worden gemaakt.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDelete(false)}
              disabled={deleteMyData.isPending}
            >
              Annuleren
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                deleteMyData.mutate(undefined, { onSuccess: () => setShowDelete(false) })
              }
              disabled={deleteMyData.isPending}
              aria-busy={deleteMyData.isPending}
            >
              {deleteMyData.isPending ? 'Verwijderen…' : 'Definitief verwijderen'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
