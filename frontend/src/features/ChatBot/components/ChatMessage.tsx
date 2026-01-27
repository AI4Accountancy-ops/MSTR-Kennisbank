import React, { useState, useRef, useEffect, useCallback, memo } from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import { toast } from 'sonner';
import { Copy, Loader2, MessageSquare } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import { Button } from '~/components/ui/button';

import ChunksModal from '@features/ChunksModal';
import Feedback from '@features/Feedback';
import MessageFeedback from '@features/Feedback/components/MessageFeedback';

import type { ChatMessageProps, BotMessageCompleteEventDetail } from '../types';

declare global {
  interface Window {
    testTriggerSave?: () => void;
  }
}

const AnimatedDots = memo(() => {
  const [dots, setDots] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => (prev + 1) % 4);
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <span className="inline-block min-w-[24px]">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className={[
            'transition-opacity duration-200',
            dots > i ? 'opacity-100' : 'opacity-0',
          ].join(' ')}
        >
          .
        </span>
      ))}
    </span>
  );
});

// Markdown element renderers to ensure proper formatting and spacing
const CodeRenderer = ({
  inline,
  children,
  ...props
}: { inline?: boolean; children?: React.ReactNode } & React.HTMLAttributes<HTMLElement>) => {
  return (
    <code
      {...props}
      className={['text-[0.95rem]', inline ? 'bg-muted rounded px-1 py-0.5' : 'block'].join(' ')}
    >
      {children}
    </code>
  );
};

const markdownComponents: Components = {
  a: ({ children, ...props }) => (
    <a
      {...props}
      className="text-[#257dff] no-underline hover:underline underline-offset-2 break-words inline-block max-w-full"
    >
      {children}
    </a>
  ),
  p: ({ children, ...props }) => (
    <p {...props} className="break-words whitespace-pre-wrap my-4 mx-2 text-[0.975rem] leading-6">
      {children}
    </p>
  ),
  pre: ({ children, ...props }) => (
    <pre
      {...props}
      className="overflow-x-auto whitespace-pre break-words max-w-full text-[0.95rem] mx-2 mb-4 bg-muted rounded-md p-3"
    >
      {children}
    </pre>
  ),
  code: CodeRenderer,
  ul: ({ children, ...props }) => (
    <ul {...props} className="list-disc pl-6 my-3 space-y-2">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol {...props} className="list-decimal pl-6 my-3 space-y-2">
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li {...props} className="text-[0.975rem]">
      {children}
    </li>
  ),
  blockquote: ({ children, ...props }) => (
    <blockquote
      {...props}
      className="border-l-4 border-border pl-3 italic text-muted-foreground my-3"
    >
      {children}
    </blockquote>
  ),
  hr: props => <hr {...props} className="border-0 h-px bg-border w-full my-6" />,
  h1: ({ children, ...props }) => (
    <h1 {...props} className="text-2xl font-semibold my-3">
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 {...props} className="text-xl font-semibold my-3">
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 {...props} className="text-lg font-semibold my-2">
      {children}
    </h3>
  ),
  h4: ({ children, ...props }) => (
    <h4 {...props} className="text-base font-semibold my-2">
      {children}
    </h4>
  ),
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto my-3">
      <table {...props} className="w-full text-sm border-collapse">
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }) => (
    <th {...props} className="border px-2 py-1 bg-muted font-medium">
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td {...props} className="border px-2 py-1 align-top">
      {children}
    </td>
  ),
  strong: ({ children, ...props }) => (
    <strong {...props} className="font-semibold">
      {children}
    </strong>
  ),
  em: ({ children, ...props }) => (
    <em {...props} className="italic">
      {children}
    </em>
  ),
};

const ChatMessage: React.FC<ChatMessageProps> = ({
  sender,
  text,
  usedChunks = [],
  isLoading = false,
  processingStage = 'analyzing',
  processingTimeMs,
  userMessage = '',
  completeChatHistory = [],
  isBackendComplete = false,
}) => {
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [isLastVisible, setIsLastVisible] = useState(false);
  const messageRef = useRef<HTMLDivElement>(null);

  // Refs
  const botMessageRef = useRef<HTMLDivElement>(null);
  const completionTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Preprocess text to ensure newlines between --- and content
  const preprocessText = useCallback((inputText: string): string => {
    if (!inputText) return '';

    // Normalize line endings to \n
    let processedText = inputText.replace(/\r\n/g, '\n');

    // Handle exact three dashes with optional spaces
    // Add newline after opening --- if there isn't one
    processedText = processedText.replace(/^[\s]*---[\s]*\n(?!\n)/gm, match => `${match}\n`);

    // Add newline before closing --- if there isn't one
    processedText = processedText.replace(/(?<!\n)\n([\s]*---[\s]*)/g, '\n\n$1');

    // Clean up any more than 2 consecutive newlines
    processedText = processedText.replace(/\n{3,}/g, '\n\n');

    // Ensure text ends with newline if it ends with ---
    if (processedText.endsWith('---')) {
      processedText += '\n';
    }

    return processedText;
  }, []);

  // Memoize functions
  const checkIfLastMessage = useCallback(() => {
    if (!messageRef.current) return;
    const parent = messageRef.current.parentElement;
    if (!parent) return;

    const botMessages = Array.from(parent.children).filter(child => {
      return child.getAttribute('data-sender') === 'bot';
    });

    if (botMessages.length > 0) {
      const lastBotMessage = botMessages[botMessages.length - 1] as HTMLElement;
      setIsLastVisible(messageRef.current === lastBotMessage);
    }
  }, [sender]);

  const getLoadingMessage = useCallback(() => {
    const baseMsg =
      (
        {
          analyzing: 'Vraag analyseren',
          analyzing_sources: 'Bronnen analyseren',
          preparing_search: 'Zoekopdracht voorbereiden',
          collecting_results: 'Zoekresultaten ophalen',
          retrieving_more_sources: 'Meer bronnen ophalen',
          verifying_urls: 'Inhoud uit bronnen extraheren',
          reasoning: 'Bezig met redeneren',
          retrieving: 'Relevante bronnen zoeken',
        } as Record<string, string>
      )[processingStage || 'analyzing'] || 'Bezig met verwerken';

    return (
      <span className="inline-flex items-center">
        {baseMsg}
        <AnimatedDots />
      </span>
    );
  }, [processingStage]);

  useEffect(() => {
    if (!messageRef.current || sender !== 'bot') return;

    const observer = new MutationObserver(() => {
      checkIfLastMessage();
    });

    checkIfLastMessage();

    if (messageRef.current.parentElement) {
      observer.observe(messageRef.current.parentElement, {
        childList: true,
        subtree: true,
      });
    }

    return () => observer.disconnect();
  }, [sender, text, usedChunks, isLoading, processingStage, processingTimeMs, checkIfLastMessage]);

  useEffect(() => {
    if (sender === 'bot' && botMessageRef.current) {
      const handleCopyEvent = (e: ClipboardEvent) => {
        const selection = window.getSelection();
        if (
          selection &&
          selection.toString().trim() !== '' &&
          botMessageRef.current?.contains(selection.anchorNode)
        ) {
          e.preventDefault();
          e.clipboardData?.setData('text/plain', selection.toString());

          // Create a temporary div to strip HTML formatting
          const tempDiv = document.createElement('div');
          tempDiv.innerHTML = selection.toString();
          const plainText = tempDiv.textContent || tempDiv.innerText || '';

          // Put plain text on clipboard instead
          e.clipboardData?.setData('text/plain', plainText);

          toast.success('Tekst gekopieerd naar klembord!');
        }
      };

      document.addEventListener('copy', handleCopyEvent);
      return () => {
        document.removeEventListener('copy', handleCopyEvent);
      };
    }
  }, [sender, text]);

  useEffect(() => {
    return () => {
      if (completionTimerRef.current) {
        clearTimeout(completionTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (sender === 'bot' && text) {
      const COMPLETE_MARKER = '\n###COMPLETE###';
      if (text.includes(COMPLETE_MARKER)) {
        const cleanText = text.replace(COMPLETE_MARKER, '');

        const event = new CustomEvent<BotMessageCompleteEventDetail>('botMessageComplete', {
          detail: {
            botMessage: cleanText,
            userMessage,
            isBackendComplete: true,
            timestamp: Date.now(),
          },
        });

        window.dispatchEvent(event);
      }
    }
  }, [sender, text, userMessage]);

  useEffect(() => {
    if (isLoading) {
      if (completionTimerRef.current) {
        clearTimeout(completionTimerRef.current);
      }
    }
  }, [isLoading]);

  useEffect(() => {
    if (sender === 'bot' && !isLoading && text) {
      window.testTriggerSave = () => {
        const event = new CustomEvent<BotMessageCompleteEventDetail>('botMessageComplete', {
          detail: {
            botMessage: text,
            userMessage,
            isBackendComplete: true,
            timestamp: Date.now(),
          },
        });
        window.dispatchEvent(event);
      };

      return () => {
        delete window.testTriggerSave;
      };
    }
  }, [sender, isLoading, text, userMessage]);

  const handleCopy = useCallback(() => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = text;

    // Remove markdown formatting
    let plainText = tempDiv.textContent || tempDiv.innerText || '';

    // Remove markdown headers
    plainText = plainText.replace(/^#+\s/gm, '');

    // Remove markdown bold/italic
    plainText = plainText.replace(/[*_~`]/g, '');

    // Remove markdown links but keep the text
    plainText = plainText.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');

    // Remove markdown lists
    plainText = plainText.replace(/^\s*[-*+]\s/gm, '');
    plainText = plainText.replace(/^\s*\d+\.\s/gm, '');

    // Remove markdown blockquotes
    plainText = plainText.replace(/^\s*>\s/gm, '');

    // Remove markdown code blocks
    plainText = plainText.replace(/```[\s\S]*?```/g, '');
    plainText = plainText.replace(/`[^`]*`/g, '');

    // Remove all instances of markdown delimiters (---)
    plainText = plainText.replace(/---/g, '');

    // Clean up extra whitespace
    plainText = plainText.replace(/\n\s*\n/g, '\n\n').trim();

    navigator.clipboard.writeText(plainText);
    toast.success('Tekst gekopieerd naar klembord!');
  }, [text]);

  return (
    <div
      ref={messageRef}
      data-sender={sender}
      className={[
        'mb-1 flex items-start w-full',
        sender === 'user' ? 'justify-end' : 'justify-start',
      ].join(' ')}
    >
      {sender === 'user' ? (
        <div className="p-2 rounded-2xl bg-[rgba(255,175,0,0.1)] w-[60%] break-words border border-[rgba(255,175,0,0.3)] hover:bg-[rgba(255,175,0,0.15)] hover:border-[rgba(255,175,0,0.4)]">
          <ReactMarkdown components={markdownComponents}>{text}</ReactMarkdown>
        </div>
      ) : (
        <div
          ref={botMessageRef}
          onMouseEnter={() => setIsHovering(true)}
          onMouseLeave={() => setIsHovering(false)}
          className={`p-2 w-full break-words${isLastVisible ? ' min-h-[65vh]' : ''}`}
        >
          {isLoading && text.trim() === '' ? (
            <div className="flex flex-row items-center gap-2 ml-1 my-1">
              <Loader2 className="h-5 w-5 animate-spin text-brand-400" />
              <span className="text-sm font-medium text-muted-foreground">
                {getLoadingMessage()}
              </span>
            </div>
          ) : (
            <>
              <ReactMarkdown components={markdownComponents}>{preprocessText(text)}</ReactMarkdown>

              {sender === 'bot' && isBackendComplete && !isLoading && (
                <div
                  className={`ml-1 mt-1 w-full h-8 flex items-center transition-opacity duration-200 ${
                    isLastVisible || isHovering ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={handleCopy}
                          aria-label="Kopiëren"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Kopiëren</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  <MessageFeedback
                    text={text}
                    usedChunks={usedChunks}
                    isLastVisible={isLastVisible}
                    isHovering={isHovering}
                  />

                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setFeedbackModalOpen(!feedbackModalOpen)}
                          aria-label="Geef feedback"
                        >
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Geef feedback</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>

                  {Array.isArray(usedChunks) &&
                    usedChunks.some(c => c && c.source_url && c.source_url.trim() !== '') && (
                      <div className="ml-1">
                        <ChunksModal chunks={usedChunks} loading={false} />
                      </div>
                    )}
                </div>
              )}
            </>
          )}

          {feedbackModalOpen && (
            <Feedback
              open={feedbackModalOpen}
              onClose={() => setFeedbackModalOpen(false)}
              chatHistory={completeChatHistory}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
