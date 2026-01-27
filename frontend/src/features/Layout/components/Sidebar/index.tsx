import MenuContent from './components/MenuContent';
import SidebarMobile from './components/SidebarMobile';
import UserProfile from './components/UserProfile';
import FeatureNotification from './components/FeatureNotification';
import IntegrationsSection from './components/IntegrationsSection';
import { Separator } from '~/components/ui/separator';
import ChatHistoryList from '@features/ChatHistory/components/ChatHistoryList';

import { useNetworkTracking } from './hooks/useNetworkTracking';
import { useChatOperations } from './hooks/useChatOperations';

import type { SidebarProps } from './types';

const Sidebar: React.FC<SidebarProps> = props => {
  const {
    selectedChatId,
    isLoadingChat,
    handleSelectChat,
    setSelectedChatId,
    resetChat,
    setIsLoadingChat,
  } = useChatOperations();

  useNetworkTracking();

  if (props.isMobile) {
    return <SidebarMobile menuItems={props.menuItems} />;
  }

  return (
    <nav className="sticky top-[calc(var(--template-frame-height,0px)+4px)] hidden h-[calc(100vh-var(--template-frame-height,0px)-4px)] w-[240px] flex-shrink-0 md:block">
      <div className="flex h-full w-full flex-col overflow-hidden">
        <div className="flex items-center gap-2 py-2 px-4">
          <img
            src={props.logo?.src}
            alt={props.logo?.alt}
            className="h-[30px] object-contain bg-[#0a0a0a] p-1 rounded-md"
          />
          <span className="text-sm font-semibold">Belasting AI</span>
        </div>

        <Separator />

        {!props.hideMenu && (
          <div className="flex flex-col my-2">
            <MenuContent items={props.menuItems} />
          </div>
        )}

        <div className="flex grow flex-col overflow-auto p-1.5 scrollbar-thin">
          {props.customContent ? (
            <div className="flex grow flex-col overflow-auto scrollbar-thin">
              {props.customContent}
            </div>
          ) : !props.hideChatHistory ? (
            <div className="flex grow flex-col overflow-auto scrollbar-thin">
              <IntegrationsSection />
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
                }}
                selectedChatId={selectedChatId}
              />
            </div>
          ) : null}
        </div>

        <FeatureNotification />
        <div className="flex flex-col gap-1 border-t p-1">
          <div className="flex flex-shrink-0 items-center">
            <UserProfile />
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Sidebar;
