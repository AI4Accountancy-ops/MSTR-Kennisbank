import { useCallback, useEffect, useRef, useState } from 'react';
import type { UseStreamingChat, Message, ProcessingStage } from '../types';
import type { ChatRequest } from '../api';
import type { ChatMessage as FeedbackChatMessage } from '@features/Feedback/types';

type SendChatMessageFn = (payload: ChatRequest, onStream: (chunk: string) => void) => Promise<void>;

export function useStreamingChat(params: {
  chatId?: string;
  getUserId: () => string;
  sendChatMessage: SendChatMessageFn;
  onBotMessageComplete: (updated: Message[]) => void;
}): UseStreamingChat {
  const { getUserId, sendChatMessage, onBotMessageComplete } = params;

  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState<string>('');
  const [toneOfVoice, setToneOfVoice] = useState<string>('Normaal');
  const [processingStage, setProcessingStage] = useState<ProcessingStage | undefined>('analyzing');
  const [isLoading, setIsLoading] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState<boolean>(false);

  const spinnerTimeoutsRef = useRef<NodeJS.Timeout[]>([]);

  const clearSpinnerTimeouts = () => {
    spinnerTimeoutsRef.current.forEach(t => clearTimeout(t));
    spinnerTimeoutsRef.current = [];
  };

  const scheduleSpinnerStages = (isWebSearch: boolean) => {
    clearSpinnerTimeouts();
    setProcessingStage('analyzing');
    if (isWebSearch) {
      spinnerTimeoutsRef.current.push(
        setTimeout(() => setProcessingStage('preparing_search'), 800),
      );
      spinnerTimeoutsRef.current.push(
        setTimeout(() => setProcessingStage('collecting_results'), 1800),
      );
    } else {
      spinnerTimeoutsRef.current.push(setTimeout(() => setProcessingStage('retrieving'), 1800));
    }
  };

  const onToggleWebSearch = () => setWebSearchEnabled(prev => !prev);

  const convertToChatHistory = (allMessages: Message[]): FeedbackChatMessage[] =>
    allMessages.map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      message: msg.text,
      chunks: (msg.usedChunks || [])
        .filter(c => c && c.source_url && c.source_url.trim() !== '')
        .map((chunk, index) => ({
          id:
            chunk.id && chunk.id.trim() !== ''
              ? chunk.id
              : `${(chunk.source_url || '').replace(/[^a-zA-Z0-9]/g, '')}_${index}`,
          source_url: chunk.source_url || '',
          title: chunk.title || '',
        })),
    }));

  const sendMessage = useCallback(async () => {
    if (userInput.trim() === '') return;
    const currentUserMessage = userInput;
    setMessages(prev => [...prev, { sender: 'user', text: currentUserMessage }]);
    setUserInput('');

    setIsLoading(true);
    scheduleSpinnerStages(webSearchEnabled);
    setMessages(prev => [...prev, { sender: 'bot', text: '', usedChunks: [] }]);

    await sendChatMessage(
      {
        user_message: currentUserMessage,
        tone_of_voice: toneOfVoice,
        chat_history: convertToChatHistory(messages),
        user_id: getUserId(),
        web_search: webSearchEnabled,
      },
      responseText => {
        const COMPLETE_MARKER = '\n###COMPLETE###';
        const CHUNKS_MARKER = '\n###CHUNKS###';
        const RETRIEVAL_STARTED = '__RETRIEVAL_STARTED__';
        const VERIFY_FLAG = '__WEB_VERIFYING__';

        let text = responseText;

        if (text.includes(RETRIEVAL_STARTED)) {
          clearSpinnerTimeouts();
          setProcessingStage(webSearchEnabled ? 'collecting_results' : 'retrieving');
          text = text.split(RETRIEVAL_STARTED).join('');
        }
        if (text.includes(VERIFY_FLAG)) {
          clearSpinnerTimeouts();
          setProcessingStage('verifying_urls');
          text = text.split(VERIFY_FLAG).join('');
        }

        let isComplete = false;
        if (text.includes(COMPLETE_MARKER)) {
          isComplete = true;
          text = text.replace(COMPLETE_MARKER, '');
        }

        if (text.includes(CHUNKS_MARKER)) {
          clearSpinnerTimeouts();
          setProcessingStage('reasoning');
          const parts = text.split(CHUNKS_MARKER);
          const content = parts[0];
          let chunksJSON = (parts[1] || '').trim();
          const firstBrace = chunksJSON.indexOf('{');
          const lastBrace = chunksJSON.lastIndexOf('}');
          if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
            chunksJSON = chunksJSON.substring(firstBrace, lastBrace + 1);
          }
          let filtered: string[] = [];
          try {
            const parsed = JSON.parse(chunksJSON) as { filtered_urls?: string[] };
            filtered = parsed.filtered_urls || [];
          } catch {
            filtered = [];
          }
          setMessages(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.sender === 'bot') {
              last.text = content;
              last.usedChunks = filtered.map((url, i) => ({
                id: `link_${i}`,
                title: `Bron ${i + 1}`,
                source_url: url,
              }));
              if (isComplete) {
                last.isBackendComplete = true;
                clearSpinnerTimeouts();
                setIsLoading(false);
                if (webSearchEnabled) setWebSearchEnabled(false);
                onBotMessageComplete(updated);
              }
            }
            return updated;
          });
        } else {
          setMessages(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.sender === 'bot') {
              last.text = text;
              if (isComplete) {
                last.isBackendComplete = true;
                clearSpinnerTimeouts();
                setIsLoading(false);
                if (webSearchEnabled) setWebSearchEnabled(false);
                onBotMessageComplete(updated);
              }
            }
            return updated;
          });
        }
      },
    );
  }, [
    userInput,
    toneOfVoice,
    webSearchEnabled,
    messages,
    getUserId,
    sendChatMessage,
    onBotMessageComplete,
  ]);

  useEffect(() => () => clearSpinnerTimeouts(), []);

  return {
    messages,
    isLoading,
    processingStage,
    userInput,
    setUserInput,
    setMessages,
    toneOfVoice,
    setToneOfVoice,
    webSearchEnabled,
    onToggleWebSearch,
    sendMessage,
  };
}
