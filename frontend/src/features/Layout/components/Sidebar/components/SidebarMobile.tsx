import { Sheet, SheetContent, SheetHeader } from '~/components/ui/sheet';
import MenuContent from './MenuContent';
import UserProfile from './UserProfile';
import ChatHistoryList from '@features/ChatHistory/components/ChatHistoryList';
import { useChatOperations } from '../hooks/useChatOperations';
import IntegrationsSection from './IntegrationsSection';

import type { MenuItem } from '../types';

interface SidebarMobileProps {
  open?: boolean;
  onClose?: () => void;
  menuItems: MenuItem[];
  subMenuItems?: MenuItem[];
  avatarUrl?: string;
}

/**
 * Mobile version of the Sidebar using shadcn Sheet
 */
const SidebarMobile: React.FC<SidebarMobileProps> = ({
  open = false,
  onClose,
  menuItems,
  avatarUrl,
}) => {
  const {
    selectedChatId,
    handleSelectChat,
    isLoadingChat,
    setSelectedChatId,
    resetChat,
    setIsLoadingChat,
  } = useChatOperations();

  return (
    <Sheet open={open} onOpenChange={o => !o && onClose?.()}>
      <SheetContent side="right" className="w-[65vw] max-w-[300px] p-0">
        <SheetHeader className="sr-only">Mobiele navigatie</SheetHeader>
        <div className="flex h-full flex-col">
          <div className="p-2">
            <UserProfile avatarUrl={avatarUrl} />
          </div>
          <div className="h-px w-full bg-border" />
          <div className="flex grow flex-col overflow-hidden">
            <MenuContent items={menuItems} />
            <div className="h-px w-full bg-border" />
            <div className="p-1.5">
              <IntegrationsSection />
            </div>
            <div className="flex grow overflow-auto p-1.5">
              <ChatHistoryList
                onSelectChat={chatId => {
                  if (isLoadingChat || chatId === selectedChatId) return;
                  setSelectedChatId(chatId);
                  setIsLoadingChat(true);
                  resetChat();
                  window.dispatchEvent(new Event('chatSelectionStarted'));
                  handleSelectChat(chatId, true).finally(() => {
                    setIsLoadingChat(false);
                    window.dispatchEvent(new Event('chatLoaded'));
                  });
                  onClose?.();
                }}
                selectedChatId={selectedChatId}
              />
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default SidebarMobile;
