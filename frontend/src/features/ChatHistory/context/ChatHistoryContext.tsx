import React, { createContext, useContext } from 'react';
import { CategorizedHistory, ChatHistoryItem } from '../types';
import { useChatHistoryQuery } from '../hooks/useChatHistoryQuery';

interface ChatHistoryContextType {
  history: CategorizedHistory;
  addChat: (chat: ChatHistoryItem) => void;
  deleteChat: (chatId: string) => Promise<void>;
  isLoading: boolean;
  refetchHistory: () => void;
}

const ChatHistoryContext = createContext<ChatHistoryContextType | undefined>(undefined);

export const ChatHistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { history, isLoading, deleteChat, addChat, refetchHistory } = useChatHistoryQuery();

  return (
    <ChatHistoryContext.Provider
      value={{
        history,
        addChat,
        deleteChat,
        isLoading,
        refetchHistory,
      }}
    >
      {children}
    </ChatHistoryContext.Provider>
  );
};

export const useChatHistory = () => {
  const context = useContext(ChatHistoryContext);
  if (undefined === context) {
    throw new Error('useChatHistory must be used within a ChatHistoryProvider');
  }
  return context;
};
