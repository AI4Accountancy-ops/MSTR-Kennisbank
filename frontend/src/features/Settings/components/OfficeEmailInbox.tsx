import { useCallback, useEffect, useMemo, useState } from 'react';

import { Archive, Mail, MailOpen, RefreshCw, Search, Trash2 } from 'lucide-react';

import outlookSvg from '@assets/icons/outlook.svg';
import { office365StringsNl as t } from '@features/Settings/locales/office365.nl';
import { Button } from '~/components/ui/button';
import { Checkbox } from '~/components/ui/checkbox';
import { Input } from '~/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select';

import { m365Service, type M365EmailItem } from '../services/m365Service';

type EmailStatus = 'queued' | 'processing' | 'completed' | 'failed';

interface OfficeEmailItem {
  id: string;
  from: string;
  subject: string;
  receivedAt: string; // ISO
  status: EmailStatus;
  preview: string;
  bodyHtml: string;
  customer: string;
  fromName: string;
  fromEmail: string;
}

/**
 * Generates initials from a name (max 2 characters)
 */
function getInitials(name: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Generates a consistent color for an email address
 */
function getAvatarColor(email: string): string {
  const colors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
    'bg-orange-500',
    'bg-teal-500',
    'bg-cyan-500',
  ];
  const hash = email.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Formats date to relative time (e.g., "2h ago", "3d ago")
 */
function formatRelative(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffMs = Math.max(0, now - then);
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 1) {
    const hours = Math.max(1, Math.floor(diffMs / (1000 * 60 * 60)));
    return `${hours}u geleden`;
  }
  if (diffDays === 1) return 'Gisteren';
  if (diffDays < 7) return `${diffDays}d geleden`;
  if (diffDays < 14) return '1w geleden';
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks}w geleden`;
  }
  const months = Math.floor(diffDays / 30);
  return `${months}mo geleden`;
}

export default function OfficeEmailInbox() {
  const [items, setItems] = useState<ReadonlyArray<OfficeEmailItem>>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  /**
   * Load selected user_id from localStorage on mount
   */
  useEffect(() => {
    try {
      const raw = localStorage.getItem('office365_integration_state');
      if (raw) {
        const parsed = JSON.parse(raw) as { user_id?: string };
        if (parsed?.user_id) setSelectedUserId(parsed.user_id);
      }
    } catch {
      /* ignore */
    }
  }, []);

  /**
   * Fetch emails when we have a user_id
   */
  const fetchEmails = useCallback(async () => {
    if (!selectedUserId) return;

    setIsRefreshing(true);
    try {
      const res = await m365Service.getEmails({
        user_id: selectedUserId,
        folder: 'inbox',
        limit: 50,
      });

      const mapped: ReadonlyArray<OfficeEmailItem> = res.emails.map((e: M365EmailItem) => {
        const fromName = e.from_name || '';
        const fromAddr = e.from || '';
        const displayFrom = fromName ? `${fromName} <${fromAddr}>` : fromAddr;
        const status: EmailStatus = e.is_read ? 'completed' : 'queued';
        const customer = fromName || fromAddr || 'Onbekend';

        return {
          id: e.id,
          from: displayFrom,
          subject: e.subject,
          receivedAt: e.received_datetime,
          status,
          preview: e.body_preview,
          bodyHtml: `<p>${e.body_preview}</p>`,
          customer,
          fromName,
          fromEmail: fromAddr,
        };
      });

      setItems(mapped);
    } catch {
      setItems([]);
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedUserId]);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  /**
   * Filter emails based on search query and status
   */
  const filteredEmails = useMemo(() => {
    let filtered = [...items];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        email =>
          email.subject.toLowerCase().includes(query) ||
          email.from.toLowerCase().includes(query) ||
          email.preview.toLowerCase().includes(query),
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(email => email.status === statusFilter);
    }

    return filtered;
  }, [items, searchQuery, statusFilter]);

  /**
   * Handle select/deselect all emails
   */
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedEmails(new Set(filteredEmails.map(e => e.id)));
    } else {
      setSelectedEmails(new Set());
    }
  };

  /**
   * Handle individual email selection
   */
  const handleSelectEmail = (emailId: string, checked: boolean) => {
    const newSelected = new Set(selectedEmails);
    if (checked) {
      newSelected.add(emailId);
    } else {
      newSelected.delete(emailId);
    }
    setSelectedEmails(newSelected);
  };

  /**
   * Handle bulk actions (placeholder for now)
   */
  const handleBulkAction = (action: string) => {
    // TODO: Implement bulk actions
    console.log(`Bulk action: ${action}`, Array.from(selectedEmails));
  };

  const allSelected = filteredEmails.length > 0 && selectedEmails.size === filteredEmails.length;
  const someSelected = selectedEmails.size > 0 && selectedEmails.size < filteredEmails.length;

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="inline-flex size-10 items-center justify-center rounded-lg bg-accent">
            <img src={outlookSvg} alt="Outlook" className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-xl font-semibold">{t.inbox.headerTitle}</h2>
            <p className="text-sm text-muted-foreground">{t.inbox.headerSummary}</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchEmails}
          disabled={isRefreshing}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Vernieuwen
        </Button>
      </div>

      {/* Toolbar */}
      <div className="space-y-4">
        {/* Search and Filter */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Zoek in e-mails..."
              value={searchQuery}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle statussen</SelectItem>
              <SelectItem value="queued">In wachtrij</SelectItem>
              <SelectItem value="processing">Verwerken</SelectItem>
              <SelectItem value="completed">Voltooid</SelectItem>
              <SelectItem value="failed">Mislukt</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Action Buttons */}
        {selectedEmails.size > 0 && (
          <div className="flex items-center gap-2 rounded-lg border bg-muted/50 p-3">
            <span className="text-sm text-muted-foreground">
              {selectedEmails.size} {selectedEmails.size === 1 ? 'e-mail' : 'e-mails'} geselecteerd
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleBulkAction('markRead')}
                className="gap-2"
              >
                <MailOpen className="h-4 w-4" />
                Markeer als gelezen
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleBulkAction('archive')}
                className="gap-2"
              >
                <Archive className="h-4 w-4" />
                Archiveer
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleBulkAction('delete')}
                className="gap-2 text-destructive hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
                Verwijder
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Email List */}
      <div className="rounded-lg border bg-card">
        {/* List Header */}
        <div className="flex items-center gap-4 border-b bg-muted/30 px-4 py-3">
          <Checkbox
            checked={allSelected}
            onCheckedChange={handleSelectAll}
            aria-label="Selecteer alle e-mails"
            className={someSelected ? 'data-[state=checked]:bg-primary' : ''}
          />
          <div className="flex flex-1 items-center gap-2 text-sm font-medium text-muted-foreground">
            <Mail className="h-4 w-4" />
            <span>
              {filteredEmails.length} {filteredEmails.length === 1 ? 'bericht' : 'berichten'}
            </span>
          </div>
        </div>

        {/* Email Items */}
        <div className="max-h-[600px] overflow-y-auto">
          {filteredEmails.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Mail className="mb-4 h-12 w-12 text-muted-foreground/50" />
              <h3 className="mb-1 text-lg font-medium">Geen e-mails gevonden</h3>
              <p className="text-sm text-muted-foreground">
                {searchQuery || statusFilter !== 'all'
                  ? 'Probeer uw zoekopdracht of filter te wijzigen'
                  : 'Uw inbox is leeg'}
              </p>
            </div>
          ) : (
            filteredEmails.map(email => {
              const isSelected = selectedEmails.has(email.id);
              const isUnread = email.status === 'queued';

              return (
                <div
                  key={email.id}
                  className={`group flex items-start gap-4 border-b px-4 py-3 transition-colors hover:bg-muted/50 ${
                    isSelected ? 'bg-muted/30' : ''
                  } ${isUnread ? 'bg-background' : 'bg-muted/10'}`}
                >
                  {/* Checkbox */}
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={(checked: boolean) => handleSelectEmail(email.id, checked)}
                    aria-label={`Selecteer e-mail van ${email.fromName}`}
                    className="mt-1"
                  />

                  {/* Avatar */}
                  <div
                    className={`flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white ${getAvatarColor(email.fromEmail)}`}
                  >
                    {getInitials(email.fromName || email.fromEmail)}
                  </div>

                  {/* Email Content */}
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`truncate text-sm ${isUnread ? 'font-semibold' : 'font-medium'}`}
                          >
                            {email.fromName || email.fromEmail}
                          </span>
                        </div>
                        <h3
                          className={`mt-0.5 truncate text-sm ${isUnread ? 'font-semibold' : 'font-normal'}`}
                        >
                          {email.subject || '(Geen onderwerp)'}
                        </h3>
                      </div>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatRelative(email.receivedAt)}
                      </span>
                    </div>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{email.preview}</p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}
