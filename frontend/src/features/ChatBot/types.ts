/**
 * Type definitions for the ChatBot feature
 */

import type { ChunkModal } from '@features/ChunksModal';
import type { ChatMessage } from '@features/Feedback/types';

// Shared streaming types (moved from hooks/types.ts for reuse)
export type ProcessingStage =
  | 'analyzing'
  | 'analyzing_sources'
  | 'preparing_search'
  | 'collecting_results'
  | 'retrieving_more_sources'
  | 'verifying_urls'
  | 'reasoning'
  | 'retrieving';

export interface ChunkLink {
  id: string;
  title: string;
  source_url: string;
}

export interface Message {
  sender: 'user' | 'bot';
  text: string;
  usedChunks?: ChunkLink[];
  isBackendComplete?: boolean;
}

export interface StreamingConfig {
  webSearchEnabled: boolean;
  toneOfVoice: string;
}

export interface UseStreamingChat {
  messages: Message[];
  isLoading: boolean;
  processingStage?: ProcessingStage;
  userInput: string;
  setUserInput: (value: string) => void;
  setMessages: (value: Message[]) => void;
  toneOfVoice: string;
  setToneOfVoice: (value: string) => void;
  webSearchEnabled: boolean;
  onToggleWebSearch: () => void;
  sendMessage: () => Promise<void>;
}

/**
 * Props for the ChatMessage component
 */
export interface ChatMessageProps {
  sender: 'user' | 'bot';
  text: string;
  usedChunks?: ChunkModal[];
  isLoading?: boolean;
  processingStage?: ProcessingStage;
  isLatest?: boolean;
  processingTimeMs?: number;
  userMessage?: string;
  completeChatHistory?: ChatMessage[];
  isBackendComplete?: boolean;
}

/**
 * Type for the bot message complete event detail
 */
export interface BotMessageCompleteEventDetail {
  botMessage: string;
  userMessage: string;
  isBackendComplete: boolean;
  timestamp: number;
}
