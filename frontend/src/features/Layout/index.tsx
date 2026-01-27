import { ReactNode } from 'react';
import { Settings, Info, PlusCircle, Search as SearchIcon } from 'lucide-react';
import Sidebar from '@features/Layout/components/Sidebar';
import AppNavbar from '@features/Layout/components/AppNavbar';
import Logo from '@assets/images/ai4accountancy_logo_mobile.png';

import type { LogoConfig, MenuItem } from '@features/Layout/components/Sidebar/types';

// Top navbar menu (should not include Search)
const APP_MENU_ITEMS: MenuItem[] = [
  {
    text: 'Nieuwe chat',
    icon: <PlusCircle className="size-4" />,
    to: '/chatbot',
    action: 'newChat',
  },
];

// Sidebar menu (includes Search below Nieuwe chat)
const APP_SIDEBAR_MENU_ITEMS: MenuItem[] = [
  ...APP_MENU_ITEMS,
  {
    text: 'Zoeken',
    icon: <SearchIcon className="size-4" />,
    to: '/chatbot',
    action: 'openSearch',
  },
];

const APP_SUBMENU_ITEMS: MenuItem[] = [
  {
    text: 'Settings',
    icon: <Settings className="size-4" />,
    to: '/settings',
    action: 'openSettings',
  },
  { text: 'About', icon: <Info className="size-4" />, to: 'https://www.ai4accountancy.nl/' },
];

type LayoutProps = {
  children: ReactNode;
  /** Optional override to fully replace the default sidebar body */
  sidebarOverride?: ReactNode;
  /** When overriding sidebar, optionally hide top menu */
  hideSidebarMenu?: boolean;
};

export default function Layout({ children, sidebarOverride, hideSidebarMenu }: LayoutProps) {
  // Strictly type the logo config
  const logoConfig: LogoConfig = {
    src: Logo,
    alt: 'AI4Accountancy Logo',
    width: '100%',
  };

  return (
    <div className="flex h-full w-full">
      {sidebarOverride ? (
        <Sidebar
          logo={logoConfig}
          menuItems={APP_SIDEBAR_MENU_ITEMS}
          subMenuItems={APP_SUBMENU_ITEMS}
          customContent={sidebarOverride}
          hideMenu={hideSidebarMenu}
          hideChatHistory
        />
      ) : (
        <Sidebar
          logo={logoConfig}
          menuItems={APP_SIDEBAR_MENU_ITEMS}
          subMenuItems={APP_SUBMENU_ITEMS}
        />
      )}
      <AppNavbar menuItems={APP_MENU_ITEMS} subMenuItems={APP_SUBMENU_ITEMS} />
      <main className="mt-18 mx-2 mb-2 flex w-full flex-grow flex-col items-end gap-2 overflow-auto p-3 bg-sidebar rounded-md md:m-1">
        {children}
      </main>
    </div>
  );
}
