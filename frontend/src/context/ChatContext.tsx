import React, { createContext, useContext, useState, ReactNode } from 'react';

// Define the types for our chat messages
export interface ChatMessageChunk {
  chunk_type: string;
  chunk_value: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  message: string;
  messageId?: string;
  pairId?: string;
  is_initial?: boolean;
  chunks?: ChatMessageChunk[];
}

// Define the shape of our chat context
interface ChatContextType {
  chatHistory: ChatMessage[];
  setChatHistory: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  addMessage: (message: ChatMessage) => void;
  resetChat: () => void;
}

// Create the context with default values
const ChatContext = createContext<ChatContextType>({
  chatHistory: [],
  setChatHistory: () => {},
  addMessage: () => {},
  resetChat: () => {},
});

// Custom hook to use the chat context
export const useChatContext = () => useContext(ChatContext);

interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);

  const addMessage = (message: ChatMessage) => {
    setChatHistory(prev => [...prev, message]);
  };

  const resetChat = () => {
    setChatHistory([]);
  };

  return (
    <ChatContext.Provider value={{ chatHistory, setChatHistory, addMessage, resetChat }}>
      {children}
    </ChatContext.Provider>
  );
};
