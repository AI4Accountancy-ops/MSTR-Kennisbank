import React, { useState, FormEvent, useEffect, useRef } from 'react';
import { X, Send } from 'lucide-react';

import { useToast } from '~/context/ToastContext';
import { Button } from '~/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '~/components/ui/select';
import { Textarea } from '~/components/ui/textarea';

import { FeedbackRequest, ChatMessage } from './types';
import { saveFeedback } from './api';

interface FeedbackProps {
  onClose: () => void;
  open: boolean;
  chatHistory?: ChatMessage[];
}

interface MenuItemOption {
  label: string;
  value: string;
}

const menuItems: MenuItemOption[] = [
  { label: 'Vraag', value: 'Question' },
  { label: 'Bug', value: 'Bug' },
  { label: 'Functieverzoek', value: 'Feature Request' },
];

const Feedback: React.FC<FeedbackProps> = ({ onClose, open, chatHistory: propsHistory }) => {
  const [category, setCategory] = useState('Question');
  const [feedbackText, setFeedbackText] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const { showToast } = useToast();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (propsHistory && propsHistory.length > 0) {
      setChatHistory(propsHistory);
      return;
    }
    const savedHistory = localStorage.getItem('belastingAI_feedbackChatHistory');
    if (savedHistory) {
      try {
        const parsedHistory = JSON.parse(savedHistory) as ChatMessage[];
        setChatHistory(parsedHistory);
      } catch (e) {
        console.error('Failed to parse saved feedback chat history:', e);
        setChatHistory([]);
      }
    }
  }, [propsHistory]);

  useEffect(() => {
    if (!open) return;
    // Scroll into view similar to original behavior
    setTimeout(() => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      if (rect.bottom > viewportHeight) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 100);
  }, [open]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const payload: FeedbackRequest = {
      category,
      feedback_text: feedbackText,
      chat_history: chatHistory,
    };
    try {
      const data = await saveFeedback(payload);
      console.log('Feedback submitted successfully:', data);
      showToast('Feedback succesvol verzonden!');
      setFeedbackText('');
      onClose();
    } catch (err) {
      console.error(err);
      showToast('Er is een fout opgetreden bij het verzenden van de feedback', 'error');
    }
  };

  if (!open) return null;

  return (
    <div
      ref={containerRef}
      className="mb-1 rounded-lg border border-border shadow-none"
      role="region"
      aria-label="Feedback formulier"
    >
      <div className="px-4 py-2">
        <form onSubmit={handleSubmit} id="feedback-form">
          <div className="space-y-3">
            <div className="flex items-center justify-end">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                aria-label="Sluiten"
                onClick={onClose}
              >
                <X className="size-4" />
              </Button>
            </div>

            <div className="grid gap-1">
              <label htmlFor="feedback-category" className="text-sm font-medium text-foreground">
                Type feedback
              </label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="feedback-category" className="h-9 w-full">
                  <SelectValue placeholder="Type feedback" />
                </SelectTrigger>
                <SelectContent>
                  {menuItems.map(item => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1">
              <label htmlFor="feedback-text" className="text-sm font-medium text-foreground">
                Beschrijving
              </label>
              <Textarea
                id="feedback-text"
                placeholder="Vertel gedetailleerd over je issue of suggestie..."
                className="min-h-[72px] max-h-[140px]"
                value={feedbackText}
                onChange={e => setFeedbackText(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-3 mb-2 flex items-center justify-end">
            <Button type="submit" size="sm" variant="brand" className="px-2">
              Verstuur
              <Send className="ml-2 size-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Feedback;
