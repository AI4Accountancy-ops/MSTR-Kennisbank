import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router';

import SettingsLayout from '../components/SettingsLayout';
import LoadingState from '../components/LoadingState';
import {
  DEFAULT_SETTINGS_SECTION,
  LAST_SECTION_KEY,
  isValidSettingsSection,
} from '@features/Settings/constants';

// Lazy loaded sections (use aliases to satisfy TypeScript resolver reliably)
const AccountTeam = lazy(() => import('@features/Settings/routes/sections/AccountTeam'));
const PlanBilling = lazy(() => import('@features/Settings/routes/sections/PlanBilling'));
const Security = lazy(() => import('@features/Settings/routes/sections/Security'));
const UsageQuotas = lazy(() => import('@features/Settings/routes/sections/UsageQuotas'));
const Integrations = lazy(() => import('@features/Settings/routes/sections/Integrations'));
const Office365 = lazy(() => import('@features/Settings/routes/sections/Office365'));
const OutlookSuccess = lazy(() => import('@features/Settings/routes/sections/OutlookSuccess'));
const Support = lazy(() => import('@features/Settings/routes/sections/Support'));
const Legal = lazy(() => import('@features/Settings/routes/sections/Legal'));

// Basic skeleton to keep UX consistent
function SettingsSkeleton() {
  return <LoadingState message="Instellingen laden..." skeletonLines={3} />;
}

// Helper component to redirect to the last visited or default section
function RedirectToLastSection() {
  let destination = DEFAULT_SETTINGS_SECTION;
  try {
    const stored = localStorage.getItem(LAST_SECTION_KEY);
    if (isValidSettingsSection(stored)) {
      destination = stored;
    }
  } catch (error) {
    console.warn('Kon laatste sectie niet ophalen uit localStorage:', error);
  }
  return <Navigate to={destination} replace />;
}

export default function SettingsRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SettingsLayout />}>
        <Route index element={<RedirectToLastSection />} />
        <Route
          path="account-team"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <AccountTeam />
            </Suspense>
          }
        />
        <Route
          path="plan-billing"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <PlanBilling />
            </Suspense>
          }
        />
        <Route
          path="security"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <Security />
            </Suspense>
          }
        />
        <Route
          path="usage-quotas"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <UsageQuotas />
            </Suspense>
          }
        />
        <Route
          path="integrations"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <Integrations />
            </Suspense>
          }
        />
        <Route
          path="integrations/office365"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <Office365 />
            </Suspense>
          }
        />
        <Route
          path="integrations/outlook/success"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <OutlookSuccess />
            </Suspense>
          }
        />
        <Route
          path="support"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <Support />
            </Suspense>
          }
        />
        <Route
          path="legal"
          element={
            <Suspense fallback={<SettingsSkeleton />}>
              <Legal />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
