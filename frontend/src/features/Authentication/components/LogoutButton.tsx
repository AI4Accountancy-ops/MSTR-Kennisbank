import { useMsal } from '@azure/msal-react';
import { logoutUser } from '@features/Authentication/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import { Button } from '~/components/ui/button';
import { LogOut } from 'lucide-react';

export default function LogoutButton() {
  const { instance } = useMsal();

  const handleLogout = async () => {
    await logoutUser(instance);
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            <span className="sr-only">Uitloggen</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Uitloggen</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
