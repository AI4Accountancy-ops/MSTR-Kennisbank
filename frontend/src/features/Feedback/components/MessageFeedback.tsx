import React, { useCallback, useEffect, useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import { Button } from '~/components/ui/button';
import { useMsal } from '@azure/msal-react';
import { messageFeedback } from '../api';
import { MessageFeedbackRequest } from '../types';
import { ChunkModal } from '@features/ChunksModal';

interface MessageFeedbackProps {
  text: string;
  usedChunks?: ChunkModal[];
  isLastVisible: boolean;
  isHovering: boolean;
}

const MessageFeedback: React.FC<MessageFeedbackProps> = ({
  text,
  usedChunks = [],
  isLastVisible,
  isHovering,
}) => {
  const [feedbackSent, setFeedbackSent] = useState<'good' | 'bad' | null>(null);
  const [currentChatId, setCurrentChatId] = useState<string | null>(
    localStorage.getItem('belastingAI_currentChatId'),
  );

  const { accounts } = useMsal();

  const getMessageId = useCallback(() => {
    if (!text) return '';
    const hashCode = (str: string): number => {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash = hash & hash;
      }
      return hash;
    };
    const chatSessionId = localStorage.getItem('belastingAI_currentChatId') || '';
    const contentToHash = chatSessionId
      ? `${chatSessionId}-${text.substring(0, 100)}`
      : text.substring(0, 100);
    const contentHash = hashCode(contentToHash).toString(16);
    return `feedback-bot-${chatSessionId}-${contentHash}`;
  }, [text]);

  const feedbackId = React.useRef(getMessageId());

  useEffect(() => {
    const checkChatIdChange = () => {
      const newChatId = localStorage.getItem('belastingAI_currentChatId');
      if (newChatId !== currentChatId) {
        setCurrentChatId(newChatId);
        setFeedbackSent(null);
        feedbackId.current = getMessageId();
      }
    };
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'belastingAI_currentChatId') {
        checkChatIdChange();
      }
    };
    window.addEventListener('storage', handleStorageChange);
    const intervalId = setInterval(checkChatIdChange, 500);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(intervalId);
    };
  }, [currentChatId, getMessageId]);

  useEffect(() => {
    feedbackId.current = getMessageId();
  }, [text, getMessageId, currentChatId]);

  useEffect(() => {
    if (text) {
      try {
        const feedbackKey = `belastingAI_feedback_${feedbackId.current}`;
        const savedFeedback = localStorage.getItem(feedbackKey);
        if (savedFeedback) {
          setFeedbackSent(savedFeedback as 'good' | 'bad');
        } else {
          setFeedbackSent(null);
        }
      } catch (error) {
        console.error('Error retrieving feedback state from localStorage:', error);
      }
    }
  }, [text, feedbackId.current, currentChatId]);

  const handleFeedback = useCallback(
    async (type: 'good' | 'bad') => {
      if (feedbackSent === type) return;
      try {
        const userId = accounts[0]?.localAccountId || 'anonymous';
        const feedbackData: MessageFeedbackRequest = {
          user_id: userId,
          chat_message: {
            role: 'assistant',
            message: text,
            chunks: usedChunks || [],
          },
          feedback_type: type,
        };
        await messageFeedback(feedbackData);
        setFeedbackSent(type);
        try {
          const feedbackKey = `belastingAI_feedback_${feedbackId.current}`;
          localStorage.setItem(feedbackKey, type);
        } catch (error) {
          console.error('Error saving feedback state to localStorage:', error);
        }
      } catch (error) {
        console.error('Error sending feedback:', error);
      }
    },
    [accounts, text, usedChunks, feedbackSent],
  );

  // Hide all buttons (including activated ones) when not last visible or hovering
  const shouldShowButtons = isLastVisible || isHovering;

  return (
    <TooltipProvider>
      {(!feedbackSent || feedbackSent === 'good') && shouldShowButtons && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => handleFeedback('good')}
              aria-label="Goede reactie"
              disabled={feedbackSent === 'good'}
            >
              <ThumbsUp className={`size-4 ${feedbackSent === 'good' ? 'text-brand-400 fill-brand-400' : ''}`} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Goede reactie</p>
          </TooltipContent>
        </Tooltip>
      )}

      {(!feedbackSent || feedbackSent === 'bad') && shouldShowButtons && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              onClick={() => handleFeedback('bad')}
              aria-label="Slechte reactie"
              disabled={feedbackSent === 'bad'}
            >
              <ThumbsDown className={`size-4 ${feedbackSent === 'bad' ? 'text-red-500 fill-red-500' : ''}`} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Slechte reactie</p>
          </TooltipContent>
        </Tooltip>
      )}
    </TooltipProvider>
  );
};

export default MessageFeedback;
