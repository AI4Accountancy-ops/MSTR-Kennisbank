import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router';
import { useMsal } from '@azure/msal-react';
import { useAccessCheck } from '~/hooks/useAccessCheck';
import ModeToggle from '@/features/Marketing/components/Header/ModeToggle';
import { MobileNav } from '@/features/Marketing/components/Header/MobileNav';
import { MainNav } from '@/features/Marketing/components/Header/MainNav';
import LogoutButton from '@features/Authentication/components/LogoutButton';

import BrandIcon from '@/assets/icons/brand-icon';

// Access is determined via /api/access/check (single source of truth)

export default function MarketingHeader() {
  const { instance } = useMsal();
  const msalAccounts = instance.getAllAccounts();
  const hasManualToken = typeof window !== 'undefined' && !!localStorage.getItem('b2c_token');
  const isAuthenticated = hasManualToken || msalAccounts.length > 0;

  // Determine display name from MSAL or stored B2C user
  const account = msalAccounts[0];
  let storedName = '';
  if (typeof window !== 'undefined') {
    const b2cUserRaw = localStorage.getItem('b2c_user');
    if (b2cUserRaw) {
      try {
        const parsed: { name?: string; email?: string } = JSON.parse(b2cUserRaw);
        storedName = parsed.name || parsed.email || '';
      } catch {
        // ignore parse errors and fallback to empty name
        storedName = '';
      }
    }
  }
  const displayName = (account && (account.name || account.username)) || storedName;

  const userId: string =
    (account && account.localAccountId) ||
    (typeof window !== 'undefined'
      ? ((): string => {
          try {
            const raw = localStorage.getItem('b2c_user');
            if (!raw) return '';
            const parsed: { user_id?: string } = JSON.parse(raw);
            return parsed.user_id || '';
          } catch {
            return '';
          }
        })()
      : '');

  const { hasAccess } = useAccessCheck(isAuthenticated ? userId : '');

  return (
    <header className="bg-background sticky top-0 z-50 w-full">
      <div className="container-wrapper 3xl:fixed:px-0 px-4 md:px-6">
        <div className="3xl:fixed:container flex h-14 items-center gap-2 **:data-[slot=separator]:!h-4">
          <MobileNav className="flex lg:hidden" />
          <Button asChild variant="ghost" size="icon" className="hidden size-8 lg:flex">
            <Link to="/">
              <BrandIcon className="size-10" />
              <span className="sr-only">AI4Accountancy</span>
            </Link>
          </Button>
          <MainNav className="hidden lg:flex" />
          <div className="ml-auto flex items-center gap-2 md:flex-1 md:justify-end">
            <ModeToggle className="hidden sm:flex" />
            <Separator orientation="vertical" className="hidden sm:flex" />
            <div className="flex items-center gap-2">
              {isAuthenticated ? (
                <>
                  <span className="hidden sm:flex text-sm text-muted-foreground">
                    {`Welkom${displayName ? `, ${displayName}` : ''}`}
                  </span>
                  {hasAccess && (
                    <Button variant="default" asChild size="sm" className="ml-1">
                      <Link to="/chatbot">
                        Naar chatbot
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  )}
                  <LogoutButton />
                </>
              ) : (
                <>
                  <Button variant="ghost" asChild size="sm" className="hidden sm:flex">
                    <Link to="/login">Login</Link>
                  </Button>
                  <Button variant="default" asChild size="sm">
                    <Link to="/login">
                      Aan de slag
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
