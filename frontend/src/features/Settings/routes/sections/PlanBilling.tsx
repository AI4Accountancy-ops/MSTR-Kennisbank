import { useCallback, useEffect, useState } from 'react';
import { CheckIcon } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table';
import {
  usePlanQuery,
  useUsage,
  useInvoices,
  useCoupons,
  usePlanManagement,
} from '@features/Settings/hooks/useSettingsQueries';
import {
  useMyOrganizations,
  useSubscriptionRefresh,
} from '@features/Settings/hooks/useSettingsQueries';
import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import UsageMeter from '../../components/UsageMeter';
import { useSettingsLayout } from '../../components/SettingsLayout';
import { Badge } from '~/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select';
import { Separator } from '~/components/ui/separator';
import { useUsageSummary } from '~/hooks/useUsageSummary';
import { planPriceIds } from '@features/Billing/constants';

import type { InvoiceStatus, PlanTier } from '@features/Settings/types';

/**
 * Format a value in EUR using Dutch locale (e.g., €49,00)
 */
function formatCurrencyEUR(valueCents: number): string {
  const euros = valueCents / 100;
  return new Intl.NumberFormat('nl-NL', {
    style: 'currency',
    currency: 'EUR',
    currencyDisplay: 'symbol',
    maximumFractionDigits: 2,
  }).format(euros);
}

/**
 * Format ISO date string for Dutch locale (e.g., 1 oktober 2025)
 */
function formatDutchDate(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return new Intl.DateTimeFormat('nl-NL', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d);
}

export default function PlanBilling() {
  const { setContentWidthClass } = useSettingsLayout();
  // Expand content width on this page; restore default on unmount
  useEffect(() => {
    setContentWidthClass('w-[70%] max-w-6xl');
    return () => setContentWidthClass('w-[50%] max-w-5xl');
  }, [setContentWidthClass]);
  // Queries
  const { data: plan, isLoading: planLoading, error: planError } = usePlanQuery();
  const { usage } = useUsage();
  const myOrgs = useMyOrganizations();
  const refreshSub = useSubscriptionRefresh();

  // Backend-driven usage summary (monthly + optional trial daily)
  const account = ((): { user_id: string } | null => {
    try {
      const raw = localStorage.getItem('b2c_user');
      return raw ? (JSON.parse(raw) as { user_id: string }) : null;
    } catch {
      return null;
    }
  })();
  const userId = account?.user_id ?? '';
  const usageSummary = useUsageSummary(userId);

  // Invoices state & query with client-side controls
  const [invoicePage, setInvoicePage] = useState<number>(1);
  const [invoicePageSize] = useState<number>(10);
  const [invoiceSortBy, setInvoiceSortBy] = useState<'date' | 'amount' | 'status'>('date');
  const [invoiceSortDir, setInvoiceSortDir] = useState<'asc' | 'desc'>('desc');
  const [invoiceStatus, setInvoiceStatus] = useState<InvoiceStatus | 'all'>('all');
  const [invoiceSearch, setInvoiceSearch] = useState<string>('');
  const { invoices, pagination } = useInvoices({
    page: invoicePage,
    pageSize: invoicePageSize,
    sortBy: invoiceSortBy,
    sortDir: invoiceSortDir,
    status: invoiceStatus,
    search: invoiceSearch,
  });

  const { applyCoupon, removeCoupon } = useCoupons();
  const { openPortal } = usePlanManagement();

  const [couponCode, setCouponCode] = useState<string>('');

  const handleCouponSubmit = useCallback<React.FormEventHandler<HTMLFormElement>>(
    event => {
      event.preventDefault();
      if (couponCode.length === 0) return;
      applyCoupon.mutate(couponCode);
    },
    [applyCoupon, couponCode],
  );

  const handleRemoveCoupon = useCallback(() => {
    removeCoupon.mutate();
  }, [removeCoupon]);

  const pageCount = Math.max(1, Math.ceil(pagination.total / pagination.pageSize));
  const canPrev = invoicePage > 1;
  const canNext = invoicePage < pageCount;

  const renderStatusBadge = (status: InvoiceStatus) => {
    if (status === 'paid') return <Badge variant="secondary">Betaald</Badge>;
    if (status === 'open') return <Badge>Open</Badge>;
    return <Badge variant="outline">Geannuleerd</Badge>;
  };

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h3 className="text-xl font-semibold">Abonnement & Facturatie</h3>
        <p className="text-muted-foreground">
          Bekijk en beheer je abonnement, gebruik en facturen.
        </p>
        {/* Subscription status from backend orgs */}
        {myOrgs.data && myOrgs.data.length > 0 && (
          <div className="text-sm text-muted-foreground">
            <span className="mr-2">Status:</span>
            <span className="font-medium">{myOrgs.data[0].subscription_status ?? 'onbekend'}</span>
            {myOrgs.data[0].current_period_end && (
              <span className="ml-2">
                (tot {formatDutchDate(myOrgs.data[0].current_period_end)})
              </span>
            )}
            <Button
              className="ml-3"
              variant="outline"
              size="sm"
              onClick={() => refreshSub.mutate(myOrgs.data![0].id)}
              disabled={refreshSub.isPending}
            >
              Stripe synchroniseren
            </Button>
          </div>
        )}
      </header>

      {/* Acties: pauzeren / opzeggen */}
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          variant="outline"
          onClick={() => openPortal.mutate()}
          disabled={!plan || openPortal.isPending}
        >
          Abonnement beheren
        </Button>
      </div>

      {/* Plankaarten */}
      <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          {
            tier: 'instap' as PlanTier,
            name: 'Instap',
            price: '€49',
            description: 'Voor zelfstandige fiscalisten en kleine kantoren',
            features: [
              '250 vragen per maand',
              'Direct toegang tot de AI-chat',
              'Actuele kennisbank (Belastingdienst & Wetten.overheid)',
              'Basis support (e-mail)',
            ],
            type: 'maand' as const,
          },
          {
            tier: 'groei' as PlanTier,
            name: 'Groei',
            price: '€149',
            description: 'Voor groeiende kantoren en MKB-adviseurs',
            features: [
              '1.000 vragen per maand',
              'Slimme assistent voor dagelijkse fiscale vragen',
              'Snelle toegang tot bronnen en uitleg',
              'Uitgebreide support (e-mail + chat)',
            ],
            type: 'maand' as const,
          },
          {
            tier: 'pro' as PlanTier,
            name: 'Pro',
            price: '€349',
            description: 'Voor middelgrote kantoren met meerdere teams',
            features: [
              '2.500 vragen per maand',
              'Extra functies voor grotere teams',
              'Meer inzicht in gebruik & rapportage',
              'Premium support',
            ],
            type: 'maand' as const,
          },
          {
            tier: 'enterprise' as PlanTier,
            name: 'Enterprise',
            price: '€899',
            description: 'Voor grotere organisaties en adviesketens',
            features: [
              '7.500+ vragen per maand',
              'Eigen beveiligde omgeving (dedicated)',
              'Volledige compliance & logging',
              'Persoonlijke accountmanager',
            ],
            type: 'vanaf' as const,
          },
        ].map(card => {
          const isCurrent = myOrgs.data?.[0].stripe_price_id === planPriceIds[card.tier];
          const buttonLabel = isCurrent ? 'Huidig plan' : 'Kies plan';
          return (
            <div
              key={card.tier}
              className={`bg-background relative flex flex-col rounded-xl border p-6 ${
                isCurrent ? 'border-brand' : 'border-border'
              }`}
            >
              {isCurrent && (
                <div className="bg-brand text-primary-foreground absolute -top-3 right-0 left-0 mx-auto w-fit rounded-full px-3 py-1 text-xs font-medium">
                  Huidig plan
                </div>
              )}
              <div className="mb-4">
                <h4 className="text-lg font-bold">{card.name}</h4>
                <p className="text-muted-foreground text-sm">{card.description}</p>
              </div>
              <div className="mb-4 flex items-baseline">
                <span className="text-3xl font-bold">{card.price}</span>
                <span className="text-muted-foreground ml-1 text-sm">/ {card.type}</span>
              </div>
              <Separator className="my-3" />
              <ul className="mb-6 space-y-2 text-sm">
                {card.features.map(feature => (
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
                  className="w-full"
                  variant={isCurrent ? 'default' : 'outline'}
                  disabled={isCurrent || openPortal.isPending}
                  onClick={() => openPortal.mutate()}
                >
                  {buttonLabel}
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Loading & errors */}
      {planLoading || usage.isLoading || invoices.isLoading ? (
        <LoadingState message="Gegevens laden..." skeletonLines={3} />
      ) : null}
      {planError || usage.error || invoices.error ? (
        <ErrorState
          title="Fout bij laden"
          description="Er ging iets mis bij het laden van de gegevens."
        />
      ) : null}

      {/* Quota vanuit backend (abonnement) */}
      <Card>
        <CardHeader>
          <CardTitle>Quotagebruik (abonnement)</CardTitle>
          <CardDescription>
            Dagelijks tijdens proefperiode, maandelijks na activatie. Realtime vanuit server.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Monthly usage */}
          <UsageMeter
            label="Maandelijks"
            used={usageSummary.data?.monthly_used ?? 0}
            limit={usageSummary.data?.monthly_quota ?? 0}
            unit="vragen"
          />
          {/* Trial daily usage when applicable */}
          {usageSummary.data?.in_trial ? (
            <UsageMeter
              label="Dagelijks (proef)"
              used={usageSummary.data?.daily_used ?? 0}
              limit={usageSummary.data?.daily_quota ?? 0}
              unit="vragen"
            />
          ) : null}

          {/* Over quota prompts */}
          {usageSummary.data?.in_trial &&
          usageSummary.data.daily_quota !== undefined &&
          (usageSummary.data.daily_used ?? 0) > (usageSummary.data.daily_quota ?? 0) ? (
            <div className="text-sm text-red-600 dark:text-red-400">
              Dagquotum bereikt (proef). Probeer het morgen opnieuw of activeer een betaald plan.
            </div>
          ) : null}
          {!usageSummary.data?.in_trial && usageSummary.data?.over_quota ? (
            <div className="text-sm text-amber-700 dark:text-amber-400">
              Maandquotum overschreden. Gebruik gaat door en wordt afgerekend volgens je plan.
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Facturen */}
      <Card>
        <CardHeader>
          <CardTitle>Facturen</CardTitle>
          <CardDescription>Overzicht van recente facturen</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Zoeken op nummer/status..."
              value={invoiceSearch}
              onChange={e => {
                setInvoiceSearch(e.target.value);
                setInvoicePage(1);
              }}
              className="w-56"
            />
            <Select
              value={invoiceStatus}
              onValueChange={v => {
                setInvoiceStatus(v as InvoiceStatus | 'all');
                setInvoicePage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Alle statussen</SelectItem>
                <SelectItem value="paid">Betaald</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="void">Geannuleerd</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={`${invoiceSortBy}:${invoiceSortDir}`}
              onValueChange={v => {
                const [by, dir] = v.split(':') as [typeof invoiceSortBy, typeof invoiceSortDir];
                setInvoiceSortBy(by);
                setInvoiceSortDir(dir);
                setInvoicePage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sorteren" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date:desc">Datum (nieuwste)</SelectItem>
                <SelectItem value="date:asc">Datum (oudste)</SelectItem>
                <SelectItem value="amount:desc">Bedrag (hoog-laag)</SelectItem>
                <SelectItem value="amount:asc">Bedrag (laag-hoog)</SelectItem>
                <SelectItem value="status:asc">Status (A-Z)</SelectItem>
                <SelectItem value="status:desc">Status (Z-A)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Factuurnummer</TableHead>
                <TableHead>Datum</TableHead>
                <TableHead>Bedrag</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actie</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pagination.items.map(inv => (
                <TableRow key={inv.id}>
                  <TableCell className="font-medium">{inv.id}</TableCell>
                  <TableCell>{formatDutchDate(inv.date)}</TableCell>
                  <TableCell>{formatCurrencyEUR(inv.amountCents)}</TableCell>
                  <TableCell>{renderStatusBadge(inv.status)}</TableCell>
                  <TableCell>
                    <Button asChild variant="outline" size="sm">
                      <a href={inv.url} target="_blank" rel="noreferrer">
                        Download
                      </a>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableCaption>
              {pagination.total === 0
                ? 'Geen facturen gevonden'
                : 'Toekomstige facturen verschijnen hier automatisch.'}
            </TableCaption>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-xs text-muted-foreground">
              {pagination.total > 0
                ? `Pagina ${pagination.page} van ${pageCount} — ${pagination.total} totaal`
                : 'Geen resultaten'}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!canPrev}
                onClick={() => setInvoicePage(v => Math.max(1, v - 1))}
              >
                Vorige
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!canNext}
                onClick={() => setInvoicePage(v => Math.min(pageCount, v + 1))}
              >
                Volgende
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Kortingscode */}
      <Card>
        <CardHeader>
          <CardTitle>Kortingscode</CardTitle>
          <CardDescription>Pas een kortingscode toe op je abonnement</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex gap-2" onSubmit={handleCouponSubmit}>
            <Input
              aria-label="Kortingscode"
              placeholder="Voer kortingscode in"
              value={couponCode}
              onChange={e => setCouponCode(e.target.value)}
            />
            <Button type="submit" disabled={couponCode.length === 0 || applyCoupon.isPending}>
              Toepassen
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleRemoveCoupon}
              disabled={removeCoupon.isPending}
            >
              Verwijderen
            </Button>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
