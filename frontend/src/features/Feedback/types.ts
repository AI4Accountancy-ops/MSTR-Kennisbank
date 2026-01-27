export interface ChunkModel {
  id: string;
  source_url: string;
  title?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  message: string;
  chunks: any[];
}

export interface FeedbackRequest {
  category: string;
  feedback_text: string;
  chat_history: ChatMessage[];
}

export interface MessageFeedbackRequest {
  user_id: string;
  chat_message: ChatMessage;
  feedback_type: string;
}
