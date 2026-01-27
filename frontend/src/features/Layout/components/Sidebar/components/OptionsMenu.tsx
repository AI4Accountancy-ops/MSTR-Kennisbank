import * as React from 'react';
import { useMsal } from '@azure/msal-react';
import { useNavigate } from 'react-router';
import { Info, LogOut, MoreVertical, Settings } from 'lucide-react';

import { logoutUser } from '@features/Authentication/utils';
import MenuButton from './MenuButton';
import ColorModeSwitchToggle from '~/theme/ColorModeSwitchToggle';
import { Button } from '~/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';

export default function OptionsMenu() {
  const navigate = useNavigate();
  const { instance } = useMsal();
  const [logoutDialogOpen, setLogoutDialogOpen] = React.useState<boolean>(false);

  return (
    <React.Fragment>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <MenuButton aria-label="Open menu">
            <MoreVertical className="size-4" />
          </MenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 p-0">
          <DropdownMenuItem
            onClick={() => {
              window.open('https://www.ai4accountancy.nl/', '_blank');
            }}
          >
            <Info className="mr-2 size-4" />
            <span>About</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              navigate('/settings');
            }}
          >
            <Settings className="mr-2 size-4" />
            <span>Settings</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <div className="px-2 py-1.5">
            <div className="flex items-center gap-2">
              <ColorModeSwitchToggle />
              <span className="text-xs text-muted-foreground">Thema</span>
            </div>
          </div>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setLogoutDialogOpen(true)}>
            <LogOut className="mr-2 size-4" />
            <span>Logout</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={logoutDialogOpen} onOpenChange={setLogoutDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Uitloggen Bevestigen</DialogTitle>
            <DialogDescription>
              Weet u zeker dat u wilt uitloggen? U moet opnieuw inloggen om de applicatie te kunnen
              gebruiken.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setLogoutDialogOpen(false)}>
              Annuleren
            </Button>
            <Button
              type="button"
              variant="brand"
              onClick={async () => {
                await logoutUser(instance);
                setLogoutDialogOpen(false);
              }}
            >
              Uitloggen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </React.Fragment>
  );
}
