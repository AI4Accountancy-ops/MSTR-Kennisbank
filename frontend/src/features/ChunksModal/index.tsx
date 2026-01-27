import React, { useEffect, useMemo, useState } from 'react';
import { Button } from '~/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '~/components/ui/dialog';
import { Loader2, ExternalLink } from 'lucide-react';
import { API_BASE_URL } from '~/config/environment';

// Global favicon cache to prevent duplicate requests
const globalFaviconCache = new Map<string, string | null>();
const pendingRequests = new Set<string>();
const requestQueue: string[] = [];
let requestTimeout: NodeJS.Timeout | null = null;

// Debounced favicon request function
const requestFaviconsDebounced = (urls: string[]) => {
  // Add new URLs to queue if not already cached or pending
  urls.forEach(url => {
    if (!globalFaviconCache.has(url) && !pendingRequests.has(url)) {
      requestQueue.push(url);
      pendingRequests.add(url);
    }
  });

  // Clear existing timeout
  if (requestTimeout) {
    clearTimeout(requestTimeout);
  }

  // Set new timeout for batch request
  requestTimeout = setTimeout(async () => {
    if (requestQueue.length === 0) return;

    const urlsToRequest = [...requestQueue];
    requestQueue.length = 0;

    try {
      const res = await fetch(`${API_BASE_URL}/favicons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: urlsToRequest }),
      });
      
      if (res.ok) {
        const data = await res.json();
        const favicons = data.favicons || {};
        
        // Update global cache
        urlsToRequest.forEach(url => {
          globalFaviconCache.set(url, favicons[url] || null);
          pendingRequests.delete(url);
        });

        // Trigger re-render for all components using these favicons
        window.dispatchEvent(new CustomEvent('faviconsUpdated', { 
          detail: { favicons: Object.keys(favicons) } 
        }));
      }
    } catch (error) {
      console.error('Favicon request failed:', error);
      // Mark as failed in cache
      urlsToRequest.forEach(url => {
        globalFaviconCache.set(url, null);
        pendingRequests.delete(url);
      });
    }
  }, 300); // 300ms debounce
};

export interface ChunkModal {
  id: string;
  title: string;
  source_url: string;
}

interface ChunksModalProps {
  chunks: ChunkModal[];
  loading?: boolean;
}

const ChunksModal: React.FC<ChunksModalProps> = ({ chunks, loading = false }) => {
  const [open, setOpen] = useState(false);
  const [favicons, setFavicons] = useState<Record<string, string | null>>({});
  const [updateTrigger, setUpdateTrigger] = useState(0);

  const handleOpen = () => setOpen(true);

  const sourceUrls = useMemo(() => (chunks || []).map(c => c.source_url).filter(Boolean), [chunks]);

  // Build a de-duplicated list of favicon URLs by site hostname
  const displayFavicons = useMemo(() => {
    const byHost = new Set<string>();
    const orderedFavicons: string[] = [];
    for (const url of sourceUrls) {
      try {
        const host = new URL(url).hostname;
        if (byHost.has(host)) continue;
        const src = favicons[url];
        if (src) {
          orderedFavicons.push(src);
          byHost.add(host);
        }
      } catch {
        // Ignore invalid URLs
      }
    }
    return orderedFavicons;
  }, [favicons, sourceUrls]);

  // Load favicons from global cache
  useEffect(() => {
    const cachedFavicons: Record<string, string | null> = {};
    sourceUrls.forEach(url => {
      cachedFavicons[url] = globalFaviconCache.get(url) || null;
    });
    setFavicons(cachedFavicons);
  }, [sourceUrls, updateTrigger]);

  // Request favicons using debounced function
  useEffect(() => {
    if (loading) return;
    if (!sourceUrls.length) return;
    
    requestFaviconsDebounced(sourceUrls);
  }, [loading, sourceUrls]);

  // Listen for global favicon updates
  useEffect(() => {
    const handleFaviconUpdate = () => {
      setUpdateTrigger(prev => prev + 1);
    };

    window.addEventListener('faviconsUpdated', handleFaviconUpdate);
    return () => window.removeEventListener('faviconsUpdated', handleFaviconUpdate);
  }, []);

  const showIcons = !loading && displayFavicons.length > 0;
  const showSpinner = loading;

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpen}
                className="rounded-2xl h-7 min-w-0 px-1 inline-flex items-center gap-1 text-sm leading-none text-brand-400 !border-brand-400"
              >
                {showSpinner ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : showIcons ? (
                  <span className="inline-flex items-center h-3.5">
                    {displayFavicons.slice(0, 3).map((src, i) => (
                      <span
                        key={`${src}_${i}`}
                        className="inline-block w-3.5 h-3.5 rounded-full overflow-hidden border border-border bg-background"
                        style={{ marginLeft: i === 0 ? 0 : -2 }}
                      >
                        <img
                          src={src}
                          alt="favicon"
                          width={14}
                          height={14}
                          style={{ display: 'block' }}
                        />
                      </span>
                    ))}
                  </span>
                ) : null}
                Bronnen
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            <p>{loading ? 'Bronnen laden…' : 'Bronnen bekijken'}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-xl bg-sidebar">
          <DialogHeader>
            <DialogTitle className="text-brand-400">Bronnen</DialogTitle>
          </DialogHeader>

          {chunks.length === 0 ? (
            <p className="text-center py-2">
              Er zijn geen bronnen gebruikt om uw vraag te beantwoorden.
            </p>
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-2">
                De volgende bronnen zijn gebruikt voor je antwoord:
              </p>
              <div className="w-full">
                {chunks.map((chunk, index) => {
                  const content = (
                    <div
                      key={index}
                      className="mb-2 bg-background rounded-lg overflow-hidden border border-border cursor-pointer"
                    >
                      <div className="py-3 px-3 hover:bg-muted/50">
                        <div className="flex items-center w-full justify-between">
                          <div className="flex items-center">
                            <span className="inline-block w-4 h-4 mr-2 rounded bg-muted overflow-hidden">
                              {chunk.source_url && favicons[chunk.source_url] ? (
                                <img
                                  src={favicons[chunk.source_url] as string}
                                  alt="favicon"
                                  width={16}
                                  height={16}
                                  style={{ display: 'block' }}
                                />
                              ) : null}
                            </span>
                            <span className="text-sm font-semibold text-muted-foreground mr-2">
                              {chunk.title ? chunk.title : `Bron ${index + 1}`}
                            </span>
                          </div>
                          <span className="text-muted-foreground">
                            <ExternalLink className="h-4 w-4 text-brand-400" />
                          </span>
                        </div>
                      </div>
                    </div>
                  );

                  return chunk.source_url ? (
                    <a
                      key={`link_${index}`}
                      href={chunk.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block no-underline text-foreground"
                    >
                      {content}
                    </a>
                  ) : (
                    content
                  );
                })}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ChunksModal;
