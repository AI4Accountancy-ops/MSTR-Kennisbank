import {
  ChatHistoryResponse,
  ChatByIdResponse,
  DeleteChatResponse,
  ChatMessage,
  SearchChatHistoryResponse,
} from './types';
import { API_BASE_URL } from '~/config/environment';

export const saveChatHistory = async ({
  user_id,
  chat_title,
  chat_history,
  chat_id,
  preserve_chunks = true,
}: {
  user_id: string;
  chat_title: string;
  chat_history: ChatMessage[];
  chat_id?: string;
  preserve_chunks?: boolean;
}): Promise<string | null> => {
  try {
    console.log('Calling save_chat_history API with request:', {
      user_id: user_id,
      chat_title: chat_title,
      chat_id: chat_id,
      chat_history_length: chat_history.length,
    });

    // Don't try to save empty chats
    if (!chat_history || chat_history.length === 0) {
      console.error('Attempted to save empty chat history');
      throw new Error('Cannot save empty chat history');
    }

    const response = await fetch(`${API_BASE_URL}/save_chat_history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id,
        chat_title,
        chat_history,
        chat_id,
        preserve_chunks,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API error (${response.status}):`, errorText);
      throw new Error(`API error (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    console.log('API response:', data);

    if (data.status === 'success') {
      return data.chat_id;
    }
    throw new Error('Failed to save chat history: ' + (data.detail || 'Unknown error'));
  } catch (error) {
    console.error('Error saving chat history:', error);
    throw error;
  }
};

export const getChatHistory = async (userId: string): Promise<ChatHistoryResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/get_chat_history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId }),
    });

    return await response.json();
  } catch (error) {
    console.error('Error fetching chat history:', error);
    throw error;
  }
};

export const getChatById = async (chatId: string, userId: string): Promise<ChatByIdResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/get_chat_by_id`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ chat_id: chatId, user_id: userId }),
    });

    return await response.json();
  } catch (error) {
    console.error('Error fetching chat:', error);
    throw error;
  }
};

export const deleteChat = async (chatId: string, userId: string): Promise<DeleteChatResponse> => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/delete_chat?chat_id=${chatId}&user_id=${userId}`,
      {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );

    return await response.json();
  } catch (error) {
    console.error('Error deleting chat:', error);
    throw error;
  }
};

export const searchChatHistory = async (
  userId: string,
  query: string,
): Promise<SearchChatHistoryResponse> => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/search_chat_history?user_id=${userId}&query=${encodeURIComponent(query)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );

    if (!response.ok) {
      throw new Error(`API error (${response.status}): ${await response.text()}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error searching chat history:', error);
    throw error;
  }
};

export const updateChatTitle = async (
  chatId: string,
  userId: string,
  newTitle: string,
): Promise<{ status: string }> => {
  try {
    const response = await fetch(`${API_BASE_URL}/update_chat_title`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatId,
        user_id: userId,
        new_title: newTitle,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update chat title: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error updating chat title:', error);
    throw error;
  }
};
