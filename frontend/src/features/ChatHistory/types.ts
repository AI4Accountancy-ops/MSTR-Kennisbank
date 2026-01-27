export interface ChatMessage {
  role: 'user' | 'assistant';
  message: string;
  messageId?: string;
  pairId?: string;
  is_initial?: boolean;
  chunks?: {
    chunk_type: string;
    chunk_value: string;
  }[];
}

export interface ChatPair {
  id?: string;
  user: string;
  assistant: string;
  chunks?: string[];
  timestamp?: string;
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatPair[];
}

export interface CategorizedHistory {
  today: ChatHistoryItem[];
  yesterday: ChatHistoryItem[];
  previous_7_days: ChatHistoryItem[];
  older: ChatHistoryItem[];
}

export interface ChatHistoryResponse {
  status: string;
  history: CategorizedHistory;
}

export interface ChatByIdResponse {
  status: string;
  chat: ChatHistoryItem;
}

export interface SaveChatHistoryRequest {
  user_id: string;
  chat_title?: string;
  chat_history: ChatMessage[];
  chat_id?: string;
  clear_existing?: boolean;
}

export interface DeleteChatResponse {
  status: string;
}

export interface SearchChatHistoryResponse {
  status: string;
  results: ChatHistoryItem[];
}
