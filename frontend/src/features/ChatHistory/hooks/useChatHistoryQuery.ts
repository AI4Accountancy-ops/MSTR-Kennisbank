import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'react-router';
import { getChatHistory, deleteChat as deleteChatApi } from '../api';
import { getUserId } from '@features/Authentication/utils';
import { CategorizedHistory, ChatHistoryItem } from '../types';

/**
 * Custom hook for managing chat history operations using react-query
 * @returns Object containing chat history data and operations
 */
export const useChatHistoryQuery = () => {
  const queryClient = useQueryClient();
  const userId = getUserId();
  const location = useLocation();

  // Determine if current route should trigger chat history fetching
  const pathname = location.pathname;
  const isAllowedRoute =
    pathname === '/home' || pathname.startsWith('/chatbot') || pathname.startsWith('/settings');

  // Query for fetching chat history
  const {
    data: history = {
      today: [],
      yesterday: [],
      previous_7_days: [],
      older: [],
    },
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['chatHistory', userId],
    queryFn: async () => {
      if (!userId) {
        throw new Error('No user ID available');
      }
      const response = await getChatHistory(userId);
      return response.history;
    },
    enabled: !!userId && isAllowedRoute,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Mutation for deleting a chat
  const deleteChatMutation = useMutation({
    mutationFn: async (chatId: string) => {
      if (!userId) {
        throw new Error('No user ID available');
      }
      await deleteChatApi(chatId, userId);
    },
    onSuccess: () => {
      // Invalidate and refetch chat history after successful deletion
      queryClient.invalidateQueries({ queryKey: ['chatHistory', userId] });
    },
  });

  // Mutation for adding a new chat
  const addChatMutation = useMutation({
    mutationFn: async (chat: ChatHistoryItem) => {
      // Optimistically update the cache
      queryClient.setQueryData<CategorizedHistory>(['chatHistory', userId], old => {
        if (!old) return old;
        return {
          ...old,
          today: [chat, ...old.today],
        };
      });
    },
  });

  return {
    history,
    isLoading,
    error,
    deleteChat: deleteChatMutation.mutateAsync,
    addChat: addChatMutation.mutate,
    refetchHistory: refetch,
  };
};
