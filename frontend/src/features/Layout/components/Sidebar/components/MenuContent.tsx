import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { Dialog, DialogContent } from '~/components/ui/dialog';
import { useChatOperations } from '@features/Layout/components/Sidebar/hooks/useChatOperations';
import Settings from './Settings';
import SearchModal from '@features/ChatHistory/components/SearchModal';

import type { MenuItem } from '../types';

interface MenuContentProps {
  /** Navigation menu items */
  items: MenuItem[];
  /** Whether this menu should be positioned at the bottom */
  isBottomMenu?: boolean;
}

/**
 * MenuContent component that renders the navigation menu items
 * @param props - Component props
 * @param props.items - Navigation menu items to display
 * @param props.isBottomMenu - Whether this menu should be positioned at the bottom
 */
const MenuContent: React.FC<MenuContentProps> = ({ items, isBottomMenu = false }) => {
  const location = useLocation();
  const { handleNewChat } = useChatOperations();

  const [settingsOpenModal, setSettingsOpenModal] = useState(false);
  const [searchOpenModal, setSearchOpenModal] = useState(false);

  const handleMenuItemClick = (event: React.MouseEvent, action?: string) => {
    if (action === 'newChat') {
      event.preventDefault();
      handleNewChat();
    }

    if (action === 'openSettings') {
      event.preventDefault();
      setSettingsOpenModal(true);
    }

    if (action === 'openSearch') {
      event.preventDefault();
      setSearchOpenModal(true);
    }
  };

  return (
    <>
      <div className={`${isBottomMenu ? 'mt-auto border-t' : 'flex-grow'} p-1`}>
        <nav className="flex flex-col gap-0.5">
          {items.map((item, index) => {
            const isSearchItem = item.action === 'openSearch';
            const selected = !isSearchItem && location.pathname === item.to;
            return (
              <Link
                key={index}
                to={item.to}
                onClick={event => handleMenuItemClick(event, item.action)}
                className={
                  `mx-1 flex items-center gap-3 rounded p-2 text-sm ` +
                  (selected
                    ? 'bg-brand-400/10 text-brand-400 hover:bg-brand-400/15'
                    : isSearchItem
                      ? ''
                      : 'hover:bg-accent hover:text-accent-foreground')
                }
              >
                <span
                  className={`inline-flex size-4 items-center justify-center ${selected ? 'text-brand-400' : ''}`}
                >
                  {item.icon}
                </span>
                <span className={`${selected ? 'text-brand-400' : ''}`}>{item.text}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <Dialog open={settingsOpenModal} onOpenChange={setSettingsOpenModal}>
        <DialogContent className="p-0 border-none bg-transparent shadow-none">
          <Settings onClose={() => setSettingsOpenModal(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={searchOpenModal} onOpenChange={setSearchOpenModal}>
        <DialogContent showCloseButton={false} className="sm:max-w-2xl">
          <SearchModal onClose={() => setSearchOpenModal(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default MenuContent;
