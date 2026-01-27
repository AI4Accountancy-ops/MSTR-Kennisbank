import React, { useState, useCallback } from 'react';
import { Input } from '~/components/ui/input';
import { Button } from '~/components/ui/button';
import { Loader2, Search, X } from 'lucide-react';
import { useDebounceString } from '~/hooks/useDebounce';

interface SearchInputProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export const SearchInput: React.FC<SearchInputProps> = ({ onSearch, isLoading = false }) => {
  const [searchQuery, setSearchQuery] = useState('');

  const debouncedSearch = useDebounceString((query: string) => {
    onSearch(query);
  }, 300);

  const handleSearchChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const query = event.target.value;
      setSearchQuery(query);
      debouncedSearch(query);
    },
    [debouncedSearch],
  );

  const handleClear = useCallback(() => {
    setSearchQuery('');
    onSearch('');
  }, [onSearch]);

  return (
    <div className="px-3 sticky top-0 z-10 mb-2">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Zoeken in chats..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="pl-9 pr-9 h-9 text-sm"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : searchQuery ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleClear}
              aria-label="Wissen"
            >
              <X className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
};
