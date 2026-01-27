import { useState } from 'react';
import { Menu } from 'lucide-react';

import SidebarMobile from '@features/Layout/components/Sidebar/components/SidebarMobile';
import Logo from '@assets/images/ai4accountancy_logo_mobile.png';
import { Button } from '~/components/ui/button';

import type { MenuItem } from '@features/Layout/components/Sidebar/types';

/**
 * AppNavbar component for mobile navigation
 */
export default function AppNavbar({
  menuItems,
  subMenuItems,
}: {
  menuItems: MenuItem[];
  subMenuItems?: MenuItem[];
}) {
  const [open, setOpen] = useState(false);

  const handleToggleDrawer = (newOpen: boolean) => () => {
    setOpen(newOpen);
  };

  return (
    <header className="fixed top-[var(--template-frame-height,0px)] z-40 block w-full border-b bg-background shadow-none md:hidden">
      <div className="flex w-full flex-col items-start justify-center gap-3 px-3 py-3">
        <div className="flex w-full items-center gap-2">
          <div className="mr-auto flex items-center justify-center">
            <img src={Logo} alt="AI4Accountancy Logo" className="h-8 w-auto object-contain" />
          </div>
          <Button
            aria-label="menu"
            size="icon"
            variant="ghost"
            onClick={handleToggleDrawer(true)}
            className="rounded-md"
          >
            <Menu className="size-5" />
          </Button>
          <SidebarMobile
            open={open}
            onClose={handleToggleDrawer(false)}
            menuItems={menuItems}
            subMenuItems={subMenuItems}
          />
        </div>
      </div>
    </header>
  );
}
