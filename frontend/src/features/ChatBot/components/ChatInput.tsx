import React, { FormEvent, useState, useCallback, memo, useRef, useEffect } from 'react';
import { Button } from '~/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import { Send, PenLine, ArrowDown } from 'lucide-react';

interface ChatInputProps {
  userInput: string;
  onInputChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  toneOfVoice: string;
  onToneChange: (tone: string) => void;
  showScrollButton: boolean;
  onScrollToBottom: () => void;
}

// Tailwind/Shadcn styles migrate MUI styles

// Move tone options outside component
export enum TONE_OF_VOICE {
  NORMAL = 'Normaal',
  CONCISE = 'Beknopt',
  EXPLANATORY = 'Uitleg',
}

export interface ToneOption {
  value: string;
  label: string;
  description: string;
}

export const TONE_OPTIONS: ToneOption[] = [
  {
    value: TONE_OF_VOICE.NORMAL,
    label: 'Normaal',
    description: 'Standaard schrijfstijl',
  },
  {
    value: TONE_OF_VOICE.CONCISE,
    label: 'Beknopt',
    description: 'Korte en directe antwoorden',
  },
  {
    value: TONE_OF_VOICE.EXPLANATORY,
    label: 'Uitleg',
    description: 'Gedetailleerde uitleg met context',
  },
];

const ChatInput: React.FC<ChatInputProps> = ({
  userInput,
  onInputChange,
  onSubmit,
  toneOfVoice,
  onToneChange,
  showScrollButton,
  onScrollToBottom,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);

  // Ref for the textarea to control its height
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /**
   * Auto-resizes the textarea height based on its content, up to a max height (8rem = 128px).
   * Resets height to 'auto' before measuring scrollHeight to ensure shrinkage works.
   */
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight + 20}px`;
    }
  }, [userInput]);

  // Memoize event handlers
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        onSubmit(e);
      }
    },
    [onSubmit],
  );

  const handleToneClick = useCallback(() => {
    setMenuOpen(prev => !prev);
  }, []);

  const handleToneSelect = useCallback(
    (tone: string) => {
      onToneChange(tone);
      setMenuOpen(false);
    },
    [onToneChange],
  );

  return (
    <div className="relative w-full">
      {/* Scroll button */}
      <button
        type="button"
        onClick={onScrollToBottom}
        className={[
          'absolute -top-12 left-1/2 -translate-x-1/2 z-[9999] cursor-pointer',
          'bg-background border border-border rounded-full w-10 h-10 flex items-center justify-center',
          'shadow-md transition-all duration-200',
          showScrollButton
            ? 'opacity-100 translate-y-0'
            : 'opacity-0 -translate-y-1 pointer-events-none',
        ].join(' ')}
        aria-label="Scroll naar beneden"
      >
        <ArrowDown className="h-5 w-5 text-muted-foreground" />
      </button>

      {/* Main container */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (userInput.trim() !== '') {
            onSubmit(e);
          }
        }}
        className="flex flex-col w-full relative border border-border rounded-xl bg-background min-h-10 max-h-80"
      >
        {/* Growing input container */}
        <div className="relative max-h-[21rem] overflow-auto py-3 px-4 scrollbar-thin">
          {!userInput && (
            <span className="absolute text-muted-foreground pointer-events-none">
              Type hier je vraag...
            </span>
          )}

          <textarea
            ref={textareaRef}
            value={userInput}
            onChange={e => {
              onInputChange(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            onPaste={e => {
              e.preventDefault();
              const text = e.clipboardData.getData('text/plain');
              const cleaned = text.replace(/^(?:\t| {4,})/gm, '');
              const target = e.target as HTMLTextAreaElement;
              const start = target.selectionStart;
              const end = target.selectionEnd;
              const newValue = target.value.slice(0, start) + cleaned + target.value.slice(end);
              onInputChange(newValue);
              setTimeout(() => {
                target.selectionStart = target.selectionEnd = start + cleaned.length;
              }, 0);
            }}
            className="w-full outline-none border-0 p-0 m-0 resize-none overflow-y-hidden bg-transparent text-[0.9rem] text-foreground"
            aria-label="Chat input textarea"
          />
        </div>

        {/* Bottom bar */}
        <div className="h-16 flex items-center justify-between pl-4 pr-2 rounded-b-xl">
          {/* Tone */}
          <div className="flex items-center gap-2">
            <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-2xl px-3 uppercase border !border-brand-400 !text-brand-400"
                  onClick={handleToneClick}
                >
                  <PenLine className="h-4 w-4 mr-2" />
                  {toneOfVoice === TONE_OF_VOICE.NORMAL ? (
                    'Schrijfstijl'
                  ) : (
                    <span className="text-brand-400">{toneOfVoice}</span>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" sideOffset={8} className="w-56">
                {TONE_OPTIONS.filter(t => t.value !== toneOfVoice).map(tone => (
                  <DropdownMenuItem key={tone.value} onClick={() => handleToneSelect(tone.value)}>
                    <div className="flex flex-col">
                      <span className="text-sm">{tone.label}</span>
                      <span className="text-xs text-muted-foreground">{tone.description}</span>
                    </div>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Send */}
          <Button
            type="submit"
            size="icon"
            variant="ghost"
            disabled={userInput.trim() === ''}
            aria-label="Versturen"
          >
            <Send
              className={
                userInput.trim() !== ''
                  ? 'h-5 w-5 !text-brand-400'
                  : 'h-5 w-5 text-muted-foreground'
              }
            />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default memo(ChatInput);
