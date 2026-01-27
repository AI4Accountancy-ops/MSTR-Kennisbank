import { useEffect, useState } from 'react';
import { useLocation } from 'react-router';
import { Routes, Route, Navigate, Outlet } from 'react-router';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Loader2 } from 'lucide-react';

import MarketingHeader from '@features/Marketing/components/Header';
import MarketingFooter from '@features/Marketing/components/Footers';
import SettingsRoutes from '@features/Settings/routes';

import HomePage from '~/pages/marketing/home';
import LoginPage from '~/pages/login';
import SignupPage from '~/pages/signup';
import ChatPage from '~/pages/chat';
import PricingPage from '~/pages/marketing/pricing';
import BillingSuccessPage from '~/pages/billing/success';
import BillingCancelPage from '~/pages/billing/cancel';
import ContactPage from '~/pages/marketing/contact';
import UpdatesPage from '~/pages/marketing/updates';
import OutlookIntegrationsPage from '~/pages/integrations/outlook';
import CreateOrganizationPage from '~/pages/onboarding/create-organization';

import { useOrganizations } from './hooks/useOrganizations';
import { useAccessCheck } from './hooks/useAccessCheck';

function AppRoutes() {
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();
  const [, setIsManuallyAuthenticated] = useState(false);

  // Check for manual token on every render
  useEffect(() => {
    const checkToken = () => {
      const token = localStorage.getItem('b2c_token');
      setIsManuallyAuthenticated(!!token);
    };

    // Check immediately
    checkToken();

    // Also set up interval to check regularly (in case token is added after mount)
    const tokenCheckInterval = setInterval(checkToken, 1000);

    return () => {
      clearInterval(tokenCheckInterval);
    };
  }, []);

  // Protected Layout component that uses Outlet
  const ProtectedLayout = () => {
    const location = useLocation();
    // Check token directly in the component function for most up-to-date state
    const token = localStorage.getItem('b2c_token');
    const hasManualToken = !!token;

    const accounts = instance.getAllAccounts();
    console.log('ProtectedRoutes - Accounts:', accounts);
    console.log('ProtectedRoutes - IsAuthenticated (MSAL):', isAuthenticated);
    console.log('ProtectedRoutes - HasManualToken (B2C):', hasManualToken);

    // Check if we have a stored token or MSAL is authenticated
    if ((!isAuthenticated || accounts.length === 0) && !hasManualToken) {
      console.log('Not authenticated, redirecting to login');
      return <Navigate to="/" replace />;
    }

    // If authenticated, ensure user has at least one organization; otherwise redirect to onboarding
    const account = instance.getAllAccounts()[0];
    const userId =
      (account && account.localAccountId) ||
      ((): string => {
        try {
          const raw = localStorage.getItem('b2c_user');
          if (!raw) return '';
          const parsed: { user_id?: string } = JSON.parse(raw);
          return parsed.user_id || '';
        } catch {
          return '';
        }
      })();

    const { data: myOrgs, isLoading: isOrganizationsLoading } = useOrganizations(userId);
    const { data: accessCheck, isLoading: isAccessLoading } = useAccessCheck(userId);

    const isOnboardingRoute = location.pathname.startsWith('/onboarding/create-organization');
    if (!isOnboardingRoute && (isOrganizationsLoading || isAccessLoading)) {
      return (
        <div className="flex h-[50vh] w-full items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Controle uitvoeren…
        </div>
      );
    }

    if (
      !isOnboardingRoute &&
      Array.isArray(myOrgs?.organizations) &&
      myOrgs.organizations.length === 0
    ) {
      return <Navigate to="/onboarding/create-organization" replace />;
    }

    // Use backend access check (covers whitelist, user flag, and org subscription)
    if (!isOnboardingRoute && accessCheck && accessCheck.status === 'success') {
      if (!accessCheck.has_access) {
        return <Navigate to="/pricing" replace />;
      }
    }

    return <Outlet />;
  };

  const MarketingLayout = () => {
    return (
      <div>
        <MarketingHeader />
        <Outlet />
        <MarketingFooter />
      </div>
    );
  };

  return (
    <Routes>
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/updates" element={<UpdatesPage />} />
        <Route path="/billing/success" element={<BillingSuccessPage />} />
        <Route path="/billing/cancel" element={<BillingCancelPage />} />
      </Route>

      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes grouped under a parent route with ProtectedLayout */}
      <Route element={<ProtectedLayout />}>
        <Route path="/home" element={<Navigate to="/chatbot" replace />} />
        <Route path="/chatbot" element={<ChatPage />} />
        <Route path="/chatbot/:chatId" element={<ChatPage />} />
        <Route path="/integrations/outlook" element={<OutlookIntegrationsPage />} />
        <Route path="/settings/*" element={<SettingsRoutes />} />
        <Route path="/onboarding/create-organization" element={<CreateOrganizationPage />} />
      </Route>
      {/* Onboarding route is guarded above */}
    </Routes>
  );
}

export default AppRoutes;
