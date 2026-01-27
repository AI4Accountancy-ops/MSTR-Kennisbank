import { useState } from 'react';
import { useNavigate } from 'react-router';
import { saveChatHistory, getChatById, deleteChat } from '@features/ChatHistory/api';
import { useChatHistory } from '@features/ChatHistory/context/ChatHistoryContext';
import { useChatContext } from '~/context/ChatContext';
import { ChatMessage } from '~/context/ChatContext';
import { getUserId } from '@features/Authentication/utils';
import { useQueryClient } from '@tanstack/react-query';

type SaveChatPayload = {
  user_id: string;
  chat_title: string;
  chat_history: ChatMessage[];
  chat_id?: string;
  preserve_chunks?: boolean;
};

export const useChatOperations = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const { chatHistory, setChatHistory, resetChat } = useChatContext();
  const { history, refetchHistory } = useChatHistory();

  const [selectedChatId, setSelectedChatId] = useState<string | undefined>(undefined);

  // Function to save a message pair
  const saveMessagePair = async () => {
    const userId = getUserId();
    if (!userId) {
      console.error('No user ID available for saving chat history');
      return null;
    }

    if (chatHistory.length === 0) {
      return null;
    }

    let chatTitle = 'Nieuwe Chat';

    if (selectedChatId) {
      const allChats = [
        ...history.today,
        ...history.yesterday,
        ...history.previous_7_days,
        ...history.older,
      ];

      const existingChat = allChats.find(chat => chat.id === selectedChatId);
      if (existingChat) {
        const existingTitle = existingChat.title;
        // Only use existing title if it's not a default value
        if (existingTitle && 
            existingTitle !== 'Nieuwe Chat' && 
            existingTitle !== 'New Chat' && 
            existingTitle.trim() !== '') {
          chatTitle = existingTitle;
        } else {
          // Generate title from first user message if existing title is default
          for (const msg of chatHistory) {
            if (msg.role === 'user') {
              chatTitle = msg.message.substring(0, 30) + (msg.message.length > 30 ? '...' : '');
              break;
            }
          }
        }
      } else {
        // Fallback to user message if chat not found in history
        for (const msg of chatHistory) {
          if (msg.role === 'user') {
            chatTitle = msg.message.substring(0, 30) + (msg.message.length > 30 ? '...' : '');
            break;
          }
        }
      }
    } else {
      // For new chats, use the first user message as title
      for (const msg of chatHistory) {
        if (msg.role === 'user') {
          chatTitle = msg.message.substring(0, 30) + (msg.message.length > 30 ? '...' : '');
          break;
        }
      }
    }

    try {
      const chatId = await saveChatHistory({
        user_id: userId,
        chat_title: chatTitle,
        chat_history: chatHistory,
        chat_id: selectedChatId,
      });

      if (!selectedChatId && chatId) {
        setSelectedChatId(chatId);
      }

      window.dispatchEvent(new Event('chatSaved'));

      return chatId;
    } catch (error) {
      console.error('Error saving chat:', error);
      return null;
    }
  };

  // Function to completely reset chat
  const completelyResetChat = () => {
    // Reset React states
    setSelectedChatId(undefined);
    resetChat(); // Clear chat context

    // Force refresh and navigation last after all state is cleared
    window.dispatchEvent(new Event('newChat'));

    // Navigate to /chatbot without a chatId parameter to ensure a fresh chat
    navigate('/chatbot');
  };

  // Handler for creating a new chat
  const handleNewChat = () => {
    completelyResetChat();
  };

  // Load a chat by ID
  const handleSelectChat = async (chatId: string, forceReload = false): Promise<void> => {
    // Only skip reload if not forced and already selected
    if (!forceReload && selectedChatId === chatId) {
      return;
    }

    // Set loading state
    setIsLoadingChat(true);

    // Clear existing chat data first to prevent showing stale data
    if (selectedChatId !== chatId) {
      resetChat(); // Clear chat context
    }

    try {
      const userId = getUserId();
      if (!userId) {
        console.error('No user ID available for loading chat');
        setIsLoadingChat(false);
        return;
      }

      // Get the chat from React Query cache or fetch if not available
      const response = await queryClient.fetchQuery({
        queryKey: ['chat', chatId],
        queryFn: () => getChatById(chatId, userId),
      });

      if (response.status === 'success' && response.chat && response.chat.messages) {
        // Update the selected chat ID
        setSelectedChatId(chatId);

        // Extract messages
        const messages = [];

        for (const pair of response.chat.messages) {
          // Process user message
          if (pair.user) {
            messages.push({
              role: 'user',
              message: pair.user,
              messageId: `${pair.id}-user`,
              pairId: pair.id,
            });
          }

          // Process assistant message
          if (pair.assistant) {
            messages.push({
              role: 'assistant',
              message: pair.assistant,
              messageId: `${pair.id}-assistant`,
              pairId: pair.id,
            });
          }
        }

        // Update chat context with the messages
        setChatHistory(messages as ChatMessage[]);
      }
    } catch (error) {
      console.error('Error loading chat:', error);
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Handle deleting a chat
  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat(chatId, getUserId());
      // Use the centralized refetchHistory function
      await refetchHistory();

      // If the deleted chat was selected, reset
      if (selectedChatId === chatId) {
        setSelectedChatId(undefined);
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
    }
  };

  // Function to save a message pair from event data
  const saveMessagePairFromEvent = async (messagePair: ChatMessage[]): Promise<string | null> => {
    const userId = getUserId();
    if (!userId) {
      console.error('No user ID available for saving message pair');
      return null;
    }

    if (!messagePair || messagePair.length === 0) {
      return null;
    }

    // Get the effective chat ID
    const effectiveChatId = selectedChatId;

    // If we have an existing chat ID, ALWAYS fetch current messages first to make sure
    // we don't overwrite existing messages
    if (effectiveChatId) {
      try {
        // Get the existing chat from the backend
        const response = await getChatById(effectiveChatId, userId);

        if (response.status === 'success' && response.chat && response.chat.messages.length > 0) {
          // Convert existing messages to format we can save
          const existingMessages: ChatMessage[] = [];
          response.chat.messages.forEach(pair => {
            if (pair.user) {
              existingMessages.push({
                role: 'user' as const,
                message: pair.user,
                is_initial: false,
              });
            }

            // Convert string[] chunks to the expected format
            const formatChunks = (chunks: string[] | undefined) => {
              if (!chunks || !Array.isArray(chunks)) return [];
              return chunks.map(chunk => ({
                chunk_type: 'text',
                chunk_value: chunk,
              }));
            };

            if (pair.assistant) {
              existingMessages.push({
                role: 'assistant' as const,
                message: pair.assistant,
                chunks: formatChunks(pair.chunks),
              });
            }
          });

          // Check if this is the exact same message pair we are trying to save
          if (existingMessages.length === messagePair.length) {
            const lastExistingMsg = existingMessages[existingMessages.length - 1]?.message;
            const lastNewMsg = messagePair[messagePair.length - 1]?.message;

            if (lastExistingMsg === lastNewMsg) {
              return effectiveChatId;
            }
          }

          // Combine existing messages with new pair
          const allMessages = [...existingMessages, ...messagePair];

          // Use the combined messages for saving
          messagePair = allMessages;
        }
      } catch (error) {
        console.error('Error saving message pair:', error);
      }
    }

    let chatTitle = 'Nieuwe Chat';
    const userMessage = messagePair.find(msg => msg.role === 'user');

    // If updating existing chat, preserve its title unless it's a default value
    if (effectiveChatId) {
      const allChats = [
        ...history.today,
        ...history.yesterday,
        ...history.previous_7_days,
        ...history.older,
      ];

      const existingChat = allChats.find(chat => chat.id === effectiveChatId);
      if (existingChat) {
        const existingTitle = existingChat.title;
        // Only use existing title if it's not a default value
        if (existingTitle && 
            existingTitle !== 'Nieuwe Chat' && 
            existingTitle !== 'New Chat' && 
            existingTitle.trim() !== '') {
          chatTitle = existingTitle;
        } else if (userMessage) {
          // Generate title from user message if existing title is default
          chatTitle = userMessage.message.substring(0, 30) + (userMessage.message.length > 30 ? '...' : '');
        }
      } else if (userMessage) {
        // Fallback to user message if chat not found in history
        chatTitle = userMessage.message.substring(0, 30) + (userMessage.message.length > 30 ? '...' : '');
      }
    } else if (userMessage) {
      // For new chats, use the user message as title
      chatTitle = userMessage.message.substring(0, 30) + (userMessage.message.length > 30 ? '...' : '');
    }

    // Save to backend
    try {
      const formatMessage = (
        role: 'user' | 'assistant',
        message: string,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        chunks: any[] = [],
      ) => {
        return {
          role,
          message,
          is_initial: false,
          // Ensure chunks are properly formatted according to ChunkModel
          chunks: chunks.map(chunk => ({
            id: chunk.id || String(Math.random()),
            year: chunk.year || new Date().getFullYear(),
            source: chunk.source || [],
            content: chunk.content || '',
            source_url: chunk.source_url || '',
            // Include any other fields from the original chunk
            ...chunk,
          })),
        };
      };

      // Create the chat history array
      const chatHistory = messagePair.map(msg => {
        if (msg.role === 'user') {
          return formatMessage('user', msg.message, []); // Empty chunks array for user messages
        } else {
          return formatMessage('assistant', msg.message, msg.chunks || []);
        }
      });

      // Create the save payload
      const savePayload: SaveChatPayload = {
        user_id: userId,
        chat_title: chatTitle || 'Nieuwe Chat',
        chat_history: chatHistory,
        preserve_chunks: true,
      };

      // Only add chat_id if we have one to update an existing chat
      if (effectiveChatId) {
        savePayload.chat_id = effectiveChatId;
      }

      const chatId = await saveChatHistory(savePayload);

      // ALWAYS update the selectedChatId with the returned chatId to ensure we're using
      // the correct ID for future saves
      if (chatId) {
        setSelectedChatId(chatId);
      }

      // Refresh the chat history list
      const wasUpdatingExistingChat = !!effectiveChatId;
      const chatSavedEvent = new CustomEvent('chatSaved', {
        detail: {
          skipRefetch: wasUpdatingExistingChat,
          chatId: chatId,
        },
      });
      window.dispatchEvent(chatSavedEvent);

      return chatId;
    } catch (error) {
      console.error('Error saving chat:', error);
      return null;
    }
  };

  return {
    selectedChatId,
    setSelectedChatId,
    isLoadingChat,
    setIsLoadingChat,
    chatHistory,
    saveMessagePair,
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    saveMessagePairFromEvent,
    completelyResetChat,
    resetChat,
  };
};
