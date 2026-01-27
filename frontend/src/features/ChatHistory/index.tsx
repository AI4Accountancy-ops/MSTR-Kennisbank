import React from 'react';
import { Button } from '~/components/ui/button';
import { MessageSquare } from 'lucide-react';

interface ChatHistoryProps {
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  selectedChatId?: string;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ onNewChat }) => {
  return (
    <div className="flex justify-center w-full p-2">
      <Button variant="outline" onClick={onNewChat} className="px-3 py-2">
        <span className="inline-flex items-center text-sm font-medium text-muted-foreground">
          <MessageSquare className="h-4 w-4 mr-2" /> Nieuwe chat
        </span>
      </Button>
    </div>
  );
};

export default ChatHistory;
