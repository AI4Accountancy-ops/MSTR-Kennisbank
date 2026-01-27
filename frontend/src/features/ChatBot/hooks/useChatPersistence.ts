import { useCallback, useRef } from 'react';
import type { Message } from '../types';
import type { ChatMessage as FeedbackChatMessage } from '@features/Feedback/types';

export function useChatPersistence(params: {
  chatId?: string;
  getUserId: () => string;
  history: {
    today: { id: string; title: string }[];
    yesterday: { id: string; title: string }[];
    previous_7_days: { id: string; title: string }[];
    older: { id: string; title: string }[];
  };
  saveChatHistory: (data: {
    user_id: string;
    chat_title: string;
    chat_history: FeedbackChatMessage[];
    chat_id?: string;
  }) => Promise<string | null>;
  navigate: (to: string, opts?: { replace?: boolean }) => void;
  refetchHistory: () => void;
  getLastEditedTitle: () => string;
}) {
  const {
    chatId,
    getUserId,
    history,
    saveChatHistory,
    navigate,
    refetchHistory,
    getLastEditedTitle,
  } = params;

  const lastSavedMessageSignatureRef = useRef<string>('');

  const convertToChatHistory = useCallback((messages: Message[]): FeedbackChatMessage[] => {
    return messages.map(msg => ({
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
  }, []);

  const deriveTitle = useCallback(
    (updatedMessages: Message[]): string => {
      if (chatId) {
        const editedTitle = getLastEditedTitle();
        if (editedTitle && editedTitle.trim() !== '') return editedTitle;

        const allChats = [
          ...history.today,
          ...history.yesterday,
          ...history.previous_7_days,
          ...history.older,
        ];
        const existing = allChats.find(c => c.id === chatId);
        const currentTitle = existing?.title || '';
        if (
          currentTitle &&
          currentTitle !== 'New Chat' &&
          currentTitle !== 'Nieuwe Chat' &&
          currentTitle.trim() !== ''
        ) {
          return currentTitle;
        }

        const firstUser = updatedMessages.find(m => m.sender === 'user');
        if (firstUser) {
          const t = firstUser.text.substring(0, 30);
          return t + (firstUser.text.length > 30 ? '...' : '');
        }
        return 'New Chat';
      }

      const firstUser = updatedMessages.find(m => m.sender === 'user');
      if (!firstUser) return 'New Chat';
      const t = firstUser.text.substring(0, 30);
      return t + (firstUser.text.length > 30 ? '...' : '');
    },
    [chatId, history, getLastEditedTitle],
  );

  const saveChatIfChanged = useCallback(
    async (updatedMessages: Message[]) => {
      const lastBot = [...updatedMessages].reverse().find(m => m.sender === 'bot');
      if (!lastBot) return;
      const signature = `${lastBot.text}-${lastBot.isBackendComplete}`;
      if (signature === lastSavedMessageSignatureRef.current) return;
      lastSavedMessageSignatureRef.current = signature;

      const chat_title = deriveTitle(updatedMessages);
      const chat_history = convertToChatHistory(updatedMessages);
      const newChatId = await saveChatHistory({
        user_id: getUserId(),
        chat_title,
        chat_history,
        chat_id: chatId,
      });

      if (!chatId && newChatId) {
        navigate(`/chatbot/${newChatId}`, { replace: true });
      }
      refetchHistory();
    },
    [
      chatId,
      convertToChatHistory,
      deriveTitle,
      getUserId,
      navigate,
      refetchHistory,
      saveChatHistory,
    ],
  );

  return { convertToChatHistory, saveChatIfChanged };
}
