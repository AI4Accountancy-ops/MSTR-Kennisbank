import { useMsal } from '@azure/msal-react';
import { useState, useEffect } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '~/components/ui/avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import OptionsMenu from './OptionsMenu';

interface UserProfileProps {
  avatarUrl?: string;
}

/**
 * UserProfile component that displays user information and logout functionality
 * @param props - Component props
 * @param props.avatarUrl - Optional URL for the user's avatar image
 */
const UserProfile: React.FC<UserProfileProps> = ({ avatarUrl }) => {
  const { instance, accounts } = useMsal();
  const activeAccount = instance.getActiveAccount();
  const currentUser = accounts[0] || {};
  const [b2cUser, setB2cUser] = useState<{ name?: string; email?: string } | null>(null);

  // Check for B2C user on mount and when localStorage changes
  useEffect(() => {
    const checkB2CUser = () => {
      const b2cUserData = localStorage.getItem('b2c_user');
      if (b2cUserData) {
        try {
          const userData = JSON.parse(b2cUserData);
          setB2cUser(userData);
        } catch (error) {
          console.error('Error parsing B2C user data:', error);
        }
      }
    };

    // Check immediately
    checkB2CUser();

    // Set up event listener for storage changes
    window.addEventListener('storage', checkB2CUser);

    return () => {
      window.removeEventListener('storage', checkB2CUser);
    };
  }, []);

  // Prioritize MSAL user, fallback to B2C user
  const userEmail = currentUser.username || b2cUser?.email || '';
  const isAuthenticated = !!activeAccount || !!b2cUser;

  if (!isAuthenticated) {
    return null;
  }

  // Identify auth provider for display
  const authProvider = activeAccount ? 'Microsoft' : 'Google';

  return (
    <div className="flex w-full items-center justify-between gap-2 p-2">
      <Avatar className="size-9">
        <AvatarImage src={avatarUrl} alt={userEmail} />
        <AvatarFallback className="text-xs">
          {userEmail ? userEmail.slice(0, 2).toUpperCase() : 'NA'}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 max-w-[calc(100%-100px)] flex-1">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="block cursor-help truncate text-xs text-muted-foreground">
                {userEmail}
              </span>
            </TooltipTrigger>
            <TooltipContent>
              <p>{userEmail}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <span className="block text-xs text-muted-foreground/70">via {authProvider}</span>
      </div>
      <OptionsMenu />
    </div>
  );
};

export default UserProfile;
