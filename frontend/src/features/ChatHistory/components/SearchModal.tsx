import React, { useCallback, useMemo, useState } from 'react';
import { Loader2, Search as SearchIcon } from 'lucide-react';
import { Input } from '~/components/ui/input';
import { Button } from '~/components/ui/button';
import { useDebounceString } from '~/hooks/useDebounce';
import { useQuery } from '@tanstack/react-query';
import { getUserId } from '@features/Authentication/utils';
import { searchChatHistory } from '../api';
import { useChatHistory } from '../context/ChatHistoryContext';

import type { ChatHistoryItem } from '../types';

type SearchModalProps = {
  onClose: () => void;
};

export default function SearchModal({ onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const userId = getUserId();
  const { history, isLoading: isHistoryLoading } = useChatHistory();

  const debounced = useDebounceString((q: string) => {
    setQuery(q);
  }, 250);

  const [inputValue, setInputValue] = useState('');

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const q = e.target.value;
      setInputValue(q);
      debounced(q);
    },
    [debounced],
  );

  const { data, isLoading } = useQuery({
    queryKey: ['chatHistory', 'search', query],
    queryFn: () => searchChatHistory(userId, query),
    enabled: query.length > 0,
    staleTime: 1000 * 60 * 5,
  });

  const grouped = useMemo(() => {
    const results = data?.results ?? [];
    const bySection: Record<string, ChatHistoryItem[]> = {
      Vandaag: [],
      Gisteren: [],
      'Vorige 7 dagen': [],
      Chats: [],
    };

    // We don't have section info in results; approximate by createdAt age
    const now = new Date();
    for (const item of results) {
      const created = new Date(item.createdAt);
      const diffDays = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
      if (diffDays === 0) bySection['Vandaag'].push(item);
      else if (diffDays === 1) bySection['Gisteren'].push(item);
      else if (diffDays <= 7) bySection['Vorige 7 dagen'].push(item);
      else bySection['Chats'].push(item);
    }
    return bySection;
  }, [data]);

  const recentFive = useMemo<ChatHistoryItem[]>(() => {
    const all: ChatHistoryItem[] = [
      ...history.today,
      ...history.yesterday,
      ...history.previous_7_days,
      ...history.older,
    ];
    return all.slice().slice(0, 5);
  }, [history]);

  const onSelect = (chatId: string) => {
    // Navigate by pushing location to chat route and close
    window.location.href = `/chatbot/${chatId}`;
    onClose();
  };

  const Section = ({ title, items }: { title: string; items: ChatHistoryItem[] }) => {
    if (items.length === 0) return null;
    return (
      <div>
        <p className="pl-1 sm:pl-2 py-1 block text-brand-400 font-medium text-xs">{title}</p>
        <ul className="space-y-0.5">
          {items.map(item => (
            <li key={item.id}>
              <button
                type="button"
                className="w-full rounded py-2 px-2 sm:px-3 text-left hover:bg-muted/60"
                onClick={() => onSelect(item.id)}
              >
                <span className="block truncate text-sm">{item.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          autoFocus
          placeholder="Zoeken in chats..."
          value={inputValue}
          onChange={onChange}
          className="pl-9 pr-16 h-10 text-sm"
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="absolute right-2 top-1/2 -translate-y-1/2 h-7 px-2"
        >
          X
        </Button>
        {isLoading && (
          <Loader2 className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      <div className="max-h-[60vh] overflow-auto pr-1">
        {query.length === 0 ? (
          isHistoryLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Laden…
            </div>
          ) : recentFive.length > 0 ? (
            <div className="space-y-3">
              <Section title="Recente chats" items={recentFive} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Geen recente chats gevonden</p>
          )
        ) : data?.results?.length ? (
          <div className="space-y-3">
            <Section title="Vandaag" items={grouped['Vandaag']} />
            <Section title="Gisteren" items={grouped['Gisteren']} />
            <Section title="Vorige 7 dagen" items={grouped['Vorige 7 dagen']} />
            <Section title="Chats" items={grouped['Chats']} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Geen resultaten gevonden</p>
        )}
      </div>
    </div>
  );
}
