import { useState, useMemo, useCallback } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, AlertTriangle, CheckCircle } from 'lucide-react';

import { Button } from '~/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';
import { Badge } from '~/components/ui/badge';
// import { Alert, AlertDescription } from '~/components/ui/alert';
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
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableCaption,
} from '~/components/ui/table';

import LoadingState from '../../components/LoadingState';
import ErrorState from '../../components/ErrorState';
import PlanGate from '../../components/PlanGate';
import { usePerUserUsage, useUsage, useThresholdSettings } from '../../hooks/useSettingsQueries';
import type { UsagePeriod, ThresholdSettings } from '../../types';

type SortField =
  | 'userName'
  | 'userEmail'
  | 'messagesSent'
  | 'tokensUsed'
  | 'attachmentsUploaded'
  | 'lastActivityDate';
type SortDirection = 'asc' | 'desc';

export default function UsageQuotas() {
  const [period, setPeriod] = useState<UsagePeriod>('month');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('userName');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Data fetching
  const { perUserUsage } = usePerUserUsage(period);
  const { usage } = useUsage();
  const { thresholds: thresholdQuery, update: updateThresholds } = useThresholdSettings();

  // Local state for threshold changes before saving
  const [localThresholds, setLocalThresholds] = useState<ThresholdSettings | null>(null);
  const [thresholdErrors, setThresholdErrors] = useState<Partial<ThresholdSettings>>({});

  // Use local state if available, otherwise use server data
  const thresholds = localThresholds ||
    thresholdQuery.data || {
      messages: 80,
      attachments: 70,
      tokens: 90,
    };

  const isLoading = perUserUsage.isLoading || usage.isLoading || thresholdQuery.isLoading;
  const hasError = perUserUsage.error || usage.error || thresholdQuery.error;

  // Filtered and sorted data
  const filteredAndSortedData = useMemo(() => {
    const data = perUserUsage.data || [];

    // Filter by search term
    const filtered = data.filter(
      user =>
        user.userName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.userEmail.toLowerCase().includes(searchTerm.toLowerCase()),
    );

    // Sort data
    const sorted = [...filtered].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortField) {
        case 'userName':
          aValue = a.userName;
          bValue = b.userName;
          break;
        case 'userEmail':
          aValue = a.userEmail;
          bValue = b.userEmail;
          break;
        case 'messagesSent':
          aValue = a.messagesSent;
          bValue = b.messagesSent;
          break;
        case 'tokensUsed':
          aValue = a.tokensUsed;
          bValue = b.tokensUsed;
          break;
        case 'attachmentsUploaded':
          aValue = a.attachmentsUploaded;
          bValue = b.attachmentsUploaded;
          break;
        case 'lastActivityDate':
          aValue = new Date(a.lastActivityDate).getTime();
          bValue = new Date(b.lastActivityDate).getTime();
          break;
        default:
          aValue = a.userName;
          bValue = b.userName;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });

    return sorted;
  }, [perUserUsage.data, searchTerm, sortField, sortDirection]);

  // Workspace totals calculation
  const workspaceTotals = useMemo(() => {
    const data = perUserUsage.data || [];
    return {
      totalMessages: data.reduce((sum, user) => sum + user.messagesSent, 0),
      totalTokens: data.reduce((sum, user) => sum + user.tokensUsed, 0),
      activeUsers: data.length,
    };
  }, [perUserUsage.data]);

  // Threshold comparison logic
  const thresholdStatus = useMemo(() => {
    const usageData = usage.data || [];
    const status = {
      messages: { exceeded: false, percentage: 0 },
      attachments: { exceeded: false, percentage: 0 },
      tokens: { exceeded: false, percentage: 0 },
    };

    usageData.forEach(metric => {
      if (metric.limit && metric.limit > 0) {
        const percentage = (metric.used / metric.limit) * 100;
        const threshold = thresholds[metric.metric as keyof ThresholdSettings] || 0;

        if (metric.metric === 'messages') {
          status.messages = { exceeded: percentage > threshold, percentage };
        } else if (metric.metric === 'attachments') {
          status.attachments = { exceeded: percentage > threshold, percentage };
        } else if (metric.metric === 'seats') {
          // Map seats to tokens for threshold comparison
          status.tokens = { exceeded: percentage > threshold, percentage };
        }
      }
    });

    return status;
  }, [usage.data, thresholds]);

  // Check if any thresholds are exceeded
  const hasExceededThresholds = useMemo(() => {
    return Object.values(thresholdStatus).some(status => status.exceeded);
  }, [thresholdStatus]);

  const hasUnsavedThresholdChanges = localThresholds !== null;

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDirection('asc');
      }
    },
    [sortField],
  );

  const handleThresholdChange = useCallback(
    (metric: keyof ThresholdSettings, value: string) => {
      const numValue = parseInt(value, 10);

      // Clear any existing error for this metric
      setThresholdErrors(prev => ({ ...prev, [metric]: undefined }));

      // Validate input
      if (isNaN(numValue)) {
        setThresholdErrors(prev => ({ ...prev, [metric]: 'Voer een geldig getal in' }));
        return;
      }

      if (numValue < 0 || numValue > 100) {
        setThresholdErrors(prev => ({ ...prev, [metric]: 'Waarde moet tussen 0 en 100 liggen' }));
        return;
      }

      // Update local state
      setLocalThresholds(prev => ({
        ...(prev || thresholds),
        [metric]: numValue,
      }));
    },
    [thresholds],
  );

  const handleSaveThresholds = useCallback(() => {
    if (localThresholds) {
      updateThresholds.mutate(localThresholds, {
        onSuccess: () => {
          setLocalThresholds(null);
          setThresholdErrors({});
        },
      });
    }
  }, [localThresholds, updateThresholds]);

  const handleResetThresholds = useCallback(() => {
    setLocalThresholds(null);
    setThresholdErrors({});
  }, []);

  const exportToCSV = useCallback(() => {
    const headers = [
      'Naam',
      'Email',
      'Berichten verzonden',
      'Tokens gebruikt',
      'Bijlagen geüpload',
      'Laatste activiteit',
    ];
    const csvContent = [
      headers.join(','),
      ...filteredAndSortedData.map(user =>
        [
          `"${user.userName}"`,
          `"${user.userEmail}"`,
          user.messagesSent,
          user.tokensUsed,
          user.attachmentsUploaded,
          `"${new Date(user.lastActivityDate).toLocaleString('nl-NL')}"`,
        ].join(','),
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute(
      'download',
      `gebruik-${period}-${new Date().toISOString().split('T')[0]}.csv`,
    );
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [filteredAndSortedData, period]);

  if (isLoading) {
    return <LoadingState message="Gebruiksgegevens laden..." skeletonLines={4} />;
  }

  if (hasError) {
    return (
      <ErrorState
        title="Fout bij laden"
        description="Er ging iets mis bij het laden van de gebruiksgegevens."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Gebruik & Quota's</h1>
        <p className="text-muted-foreground">
          Bekijk en beheer het gebruik van uw workspace en stel waarschuwingsdrempels in.
        </p>
      </div>

      {/* Periode selector */}
      <Card>
        <CardHeader>
          <CardTitle>Periode</CardTitle>
          <CardDescription>Selecteer de periode voor de gebruiksgegevens.</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={period} onValueChange={(value: UsagePeriod) => setPeriod(value)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="day">Vandaag</SelectItem>
              <SelectItem value="week">Deze week</SelectItem>
              <SelectItem value="month">Deze maand</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Gebruikersoverzicht */}
      <Card>
        <CardHeader>
          <CardTitle>Gebruikersoverzicht</CardTitle>
          <CardDescription>
            Gebruiksgegevens per gebruiker voor de geselecteerde periode.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search and filter controls */}
          <div className="flex items-center gap-4">
            <Input
              placeholder="Zoeken op naam of email..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
            <div className="text-sm text-muted-foreground">
              {filteredAndSortedData.length} van {perUserUsage.data?.length || 0} gebruikers
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('userName')}
                    className="h-auto p-0 font-semibold"
                  >
                    Naam
                    {sortField === 'userName' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'userName' && <ArrowUpDown className="ml-1 h-4 w-4" />}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('userEmail')}
                    className="h-auto p-0 font-semibold"
                  >
                    Email
                    {sortField === 'userEmail' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'userEmail' && <ArrowUpDown className="ml-1 h-4 w-4" />}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('messagesSent')}
                    className="h-auto p-0 font-semibold"
                  >
                    Berichten
                    {sortField === 'messagesSent' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'messagesSent' && <ArrowUpDown className="ml-1 h-4 w-4" />}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('tokensUsed')}
                    className="h-auto p-0 font-semibold"
                  >
                    Tokens
                    {sortField === 'tokensUsed' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'tokensUsed' && <ArrowUpDown className="ml-1 h-4 w-4" />}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('attachmentsUploaded')}
                    className="h-auto p-0 font-semibold"
                  >
                    Bijlagen
                    {sortField === 'attachmentsUploaded' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'attachmentsUploaded' && (
                      <ArrowUpDown className="ml-1 h-4 w-4" />
                    )}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('lastActivityDate')}
                    className="h-auto p-0 font-semibold"
                  >
                    Laatste activiteit
                    {sortField === 'lastActivityDate' &&
                      (sortDirection === 'asc' ? (
                        <ArrowUp className="ml-1 h-4 w-4" />
                      ) : (
                        <ArrowDown className="ml-1 h-4 w-4" />
                      ))}
                    {sortField !== 'lastActivityDate' && <ArrowUpDown className="ml-1 h-4 w-4" />}
                  </Button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedData.map(user => (
                <TableRow key={user.userId}>
                  <TableCell className="font-medium">{user.userName}</TableCell>
                  <TableCell>{user.userEmail}</TableCell>
                  <TableCell>{user.messagesSent}</TableCell>
                  <TableCell>{user.tokensUsed.toLocaleString('nl-NL')}</TableCell>
                  <TableCell>{user.attachmentsUploaded}</TableCell>
                  <TableCell>
                    {new Date(user.lastActivityDate).toLocaleString('nl-NL', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableCaption>
              {filteredAndSortedData.length === 0
                ? 'Geen gebruikers gevonden voor de geselecteerde criteria.'
                : `Totaal ${filteredAndSortedData.length} gebruikers actief in de geselecteerde periode.`}
            </TableCaption>
          </Table>
        </CardContent>
      </Card>

      {/* Workspace Totalen */}
      <Card>
        <CardHeader>
          <CardTitle>Workspace Totalen</CardTitle>
          <CardDescription>Overzicht van het totale gebruik van uw workspace.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 border rounded-lg">
            <div className="text-2xl font-bold">{workspaceTotals.totalMessages}</div>
            <div className="text-sm text-muted-foreground">Totaal berichten</div>
          </div>
          <div className="text-center p-4 border rounded-lg">
            <div className="text-2xl font-bold">
              {workspaceTotals.totalTokens.toLocaleString('nl-NL')}
            </div>
            <div className="text-sm text-muted-foreground">Totaal tokens</div>
          </div>
          <div className="text-center p-4 border rounded-lg">
            <div className="text-2xl font-bold">{workspaceTotals.activeUsers}</div>
            <div className="text-sm text-muted-foreground">Actieve gebruikers</div>
          </div>
        </CardContent>
      </Card>

      {/* Threshold Alert */}
      {hasExceededThresholds && (
        <div className="relative w-full rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          <AlertTriangle className="absolute left-4 top-4 h-4 w-4" />
          <div className="pl-7">
            <strong>Waarschuwing:</strong> U heeft de ingestelde drempels overschreden voor{' '}
            {Object.entries(thresholdStatus)
              .filter(([, status]) => status.exceeded)
              .map(([metric, status]) => {
                const labels = { messages: 'Berichten', attachments: 'Bijlagen', tokens: 'Tokens' };
                return `${labels[metric as keyof typeof labels]} (${status.percentage.toFixed(1)}%)`;
              })
              .join(', ')}
            .
          </div>
        </div>
      )}

      {/* Waarschuwingsdrempels */}
      <Card>
        <CardHeader>
          <CardTitle>Waarschuwingsdrempels</CardTitle>
          <CardDescription>
            Stel drempels in voor waarschuwingen wanneer het gebruik bepaalde percentages bereikt.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="messages-threshold">Berichten (%)</Label>
                {thresholdStatus.messages.exceeded ? (
                  <Badge variant="destructive" className="text-xs">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Overschreden
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    OK
                  </Badge>
                )}
              </div>
              <Input
                id="messages-threshold"
                type="number"
                min="0"
                max="100"
                value={thresholds.messages}
                onChange={e => handleThresholdChange('messages', e.target.value)}
                className={thresholdErrors.messages ? 'border-red-500' : ''}
              />
              {thresholdErrors.messages && (
                <p className="text-sm text-red-500">{thresholdErrors.messages}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Huidig gebruik: {thresholdStatus.messages.percentage.toFixed(1)}%
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="attachments-threshold">Bijlagen (%)</Label>
                {thresholdStatus.attachments.exceeded ? (
                  <Badge variant="destructive" className="text-xs">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Overschreden
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    OK
                  </Badge>
                )}
              </div>
              <Input
                id="attachments-threshold"
                type="number"
                min="0"
                max="100"
                value={thresholds.attachments}
                onChange={e => handleThresholdChange('attachments', e.target.value)}
                className={thresholdErrors.attachments ? 'border-red-500' : ''}
              />
              {thresholdErrors.attachments && (
                <p className="text-sm text-red-500">{thresholdErrors.attachments}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Huidig gebruik: {thresholdStatus.attachments.percentage.toFixed(1)}%
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="tokens-threshold">Tokens (%)</Label>
                {thresholdStatus.tokens.exceeded ? (
                  <Badge variant="destructive" className="text-xs">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Overschreden
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    OK
                  </Badge>
                )}
              </div>
              <Input
                id="tokens-threshold"
                type="number"
                min="0"
                max="100"
                value={thresholds.tokens}
                onChange={e => handleThresholdChange('tokens', e.target.value)}
                className={thresholdErrors.tokens ? 'border-red-500' : ''}
              />
              {thresholdErrors.tokens && (
                <p className="text-sm text-red-500">{thresholdErrors.tokens}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Huidig gebruik: {thresholdStatus.tokens.percentage.toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Save/Reset buttons */}
          {hasUnsavedThresholdChanges && (
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button
                variant="outline"
                onClick={handleResetThresholds}
                disabled={updateThresholds.isPending}
              >
                Annuleren
              </Button>
              <Button onClick={handleSaveThresholds} disabled={updateThresholds.isPending}>
                {updateThresholds.isPending ? 'Opslaan...' : 'Opslaan'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export knop */}
      <div className="flex justify-end">
        <PlanGate
          requiredPlan="pro"
          featureName="CSV Export"
          featureDescription="Exporteer gebruiksgegevens naar CSV voor analyse en rapportage."
        >
          <Button onClick={exportToCSV} variant="outline">
            Exporteren als CSV
          </Button>
        </PlanGate>
      </div>
    </div>
  );
}
