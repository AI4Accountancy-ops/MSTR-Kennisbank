import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { Loader2, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import { ChatHistoryItem } from '../types';
import { useChatHistory } from '../context/ChatHistoryContext';
// Removed inline SearchInput; search is now in a modal triggered from sidebar
import { updateChatTitle } from '../api';
import { getUserId } from '@features/Authentication/utils';
import { useToast } from '~/context/ToastContext';

interface ChatHistoryListProps {
  onSelectChat: (chatId: string) => void;
  selectedChatId?: string;
}

const ChatHistoryList: React.FC<ChatHistoryListProps> = ({ onSelectChat, selectedChatId }) => {
  const navigate = useNavigate();
  const { history, deleteChat, isLoading, refetchHistory } = useChatHistory();
  // Search moved to modal; keep state minimal
  const userId = getUserId();
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const { showToast } = useToast();

  // Inline searching removed

  const handleDelete = async (chatId: string) => {
    try {
      await deleteChat(chatId);
      showToast('Chat succesvol verwijderd', 'success');
    } catch (error) {
      console.error('Failed to delete chat:', error);
      showToast('Fout bij het verwijderen van de chat', 'error');
    }
  };

  const handleEditClick = (chatId: string) => {
    // Find the chat in any of the sections
    const allChats = [
      ...history.today,
      ...history.yesterday,
      ...history.previous_7_days,
      ...history.older,
    ];

    const chat = allChats.find(chat => chat.id === chatId);
    if (chat) {
      setEditingChatId(chatId);
      setEditingTitle(chat.title);
    }
  };

  const handleTitleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setEditingTitle(event.target.value);
  };

  const handleTitleSubmit = async (chatId: string) => {
    if (!editingTitle.trim()) return;

    try {
      setIsUpdating(true);
      await updateChatTitle(chatId, userId, editingTitle.trim());

      // Dispatch custom event to notify other components about the title update
      const titleUpdateEvent = new CustomEvent('titleUpdated', {
        detail: {
          chatId: chatId,
          newTitle: editingTitle.trim(),
          timestamp: Date.now(),
        },
      });
      window.dispatchEvent(titleUpdateEvent);

      refetchHistory(); // Refresh the chat history
      setEditingChatId(null);
      setEditingTitle('');
      showToast('Chat titel succesvol bijgewerkt', 'success');
    } catch (error) {
      console.error('Failed to update chat title:', error);
      showToast('Er is een fout opgetreden bij het bijwerken van de chat titel', 'error');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleTitleKeyDown = (event: React.KeyboardEvent, chatId: string) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleTitleSubmit(chatId);
    } else if (event.key === 'Escape') {
      setEditingChatId(null);
      setEditingTitle('');
    }
  };

  const handleTitleBlur = (chatId: string) => {
    handleTitleSubmit(chatId);
  };

  const handleSelectChat = (chatId: string) => {
    onSelectChat(chatId);
    navigate(`/chatbot/${chatId}`);
  };

  // No inline search handler

  const renderHistorySection = (title: string, chats: ChatHistoryItem[]) => {
    if (chats.length === 0) return null;

    return (
      <div className="mt-4">
        <p className="pl-3 py-2 block text-brand-400 font-medium text-xs">{title}</p>
        <ul className="space-y-0.5 ml-2">
          {chats.map(chat => (
            <li key={chat.id} className="group transition-colors overflow-hidden">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className={[
                    'w-full rounded py-2 px-2 sm:px-4 pr-8 relative overflow-hidden transition-colors hover:bg-muted/40 text-left block',
                    selectedChatId === chat.id ? 'bg-muted/60' : '',
                  ].join(' ')}
                  onClick={() => handleSelectChat(chat.id)}
                >
                  {editingChatId === chat.id ? (
                    <div className="relative w-full flex items-center pr-4">
                      <Input
                        autoFocus
                        value={editingTitle}
                        onChange={handleTitleChange}
                        onKeyDown={e => handleTitleKeyDown(e, chat.id)}
                        onBlur={() => handleTitleBlur(chat.id)}
                        disabled={isUpdating}
                        className="h-8 text-sm bg-transparent"
                      />
                      {isUpdating && (
                        <Loader2
                          className={[
                            'absolute right-1 top-1/2 -translate-y-1/2 z-10',
                            'h-4 w-4 animate-spin',
                          ].join(' ')}
                        />
                      )}
                    </div>
                  ) : (
                    <span className="max-w-[95%] overflow-hidden text-ellipsis whitespace-nowrap text-sm text-left block">
                      {chat.title}
                    </span>
                  )}
                </button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="more-options-button opacity-0 group-hover:opacity-100"
                      aria-label="Meer opties"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" sideOffset={6} className="w-44">
                    <DropdownMenuItem onClick={() => handleEditClick(chat.id)}>
                      <Pencil className="h-4 w-4 mr-2" />
                      Bewerken
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(chat.id)}
                      className="text-red-500 focus:text-red-500"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Verwijderen
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="w-full h-full flex flex-col relative">
      <div className="flex-1 overflow-auto h-full w-full scrollbar-thin">
        {isLoading ? (
          <div className="flex justify-center p-3">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : (
          <div className="overflow-auto h-full w-full scrollbar-thin">
            {renderHistorySection('Vandaag', history.today)}
            {renderHistorySection('Gisteren', history.yesterday)}
            {renderHistorySection('Vorige 7 dagen', history.previous_7_days)}
            {renderHistorySection('Chats', history.older)}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatHistoryList;
