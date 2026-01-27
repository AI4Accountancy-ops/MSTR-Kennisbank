import { ReactNode, createContext, useContext, useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import {
  ArrowLeft,
  ChartBar,
  CreditCard,
  HelpCircle,
  IterationCw,
  Shield,
  User,
  FileText,
} from 'lucide-react';

import AppLayout from '@features/Layout';
import { Button } from '~/components/ui/button';
import outlookSvg from '@assets/icons/outlook.svg';
import {
  LAST_SECTION_KEY,
  SETTINGS_SECTIONS,
  type SettingsSection,
} from '@features/Settings/constants';

interface SettingsLayoutContextValue {
  readonly setContentWidthClass: (className: string) => void;
}

const SettingsLayoutContext = createContext<SettingsLayoutContextValue | undefined>(undefined);

export function useSettingsLayout(): SettingsLayoutContextValue {
  const ctx = useContext(SettingsLayoutContext);
  if (!ctx) {
    throw new Error('useSettingsLayout must be used within SettingsLayout');
  }
  return ctx;
}

const sections: ReadonlyArray<{
  readonly path: string;
  readonly label: string;
  readonly icon?: ReactNode;
}> = [
  { path: 'account-team', label: 'Account & Team', icon: <User /> },
  { path: 'plan-billing', label: 'Abonnement & Facturatie', icon: <CreditCard /> },
  { path: 'security', label: 'Beveiliging & Compliance', icon: <Shield /> },
  { path: 'usage-quotas', label: 'Gebruik & Limieten', icon: <ChartBar /> },
  { path: 'integrations', label: 'Integraties', icon: <IterationCw /> },
  { path: 'support', label: 'Support', icon: <HelpCircle /> },
  { path: 'legal', label: 'Juridisch', icon: <FileText /> },
] as const;

export default function SettingsLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [contentWidthClass, setContentWidthClass] = useState<string>('w-[50%] max-w-5xl');
  const [officeConnected, setOfficeConnected] = useState<boolean>(false);

  // Persist last visited section for UX continuity
  useEffect(() => {
    try {
      const parts = location.pathname.split('/').filter(Boolean);
      const sectionCandidate = parts[0] === 'settings' ? parts[1] : undefined;
      if (typeof sectionCandidate === 'string') {
        const isValid = (SETTINGS_SECTIONS as readonly string[]).includes(sectionCandidate);
        if (isValid) {
          const section = sectionCandidate as SettingsSection;
          localStorage.setItem(LAST_SECTION_KEY, section);
        }
      }
    } catch (error) {
      console.warn('Kon laatste sectie niet opslaan in localStorage:', error);
    }
  }, [location.pathname]);

  // Track Office 365 connection state from localStorage and via custom event
  useEffect(() => {
    const readConnection = () => {
      try {
        const raw = localStorage.getItem('office365_integration_state');
        if (!raw) {
          setOfficeConnected(false);
          return;
        }
        const parsed = JSON.parse(raw) as { connected?: boolean };
        setOfficeConnected(parsed?.connected === true);
      } catch {
        setOfficeConnected(false);
      }
    };

    readConnection();
    const handler = () => readConnection();
    window.addEventListener('office365IntegrationChanged', handler);
    window.addEventListener('focus', handler);
    return () => {
      window.removeEventListener('office365IntegrationChanged', handler);
      window.removeEventListener('focus', handler);
    };
  }, []);

  const ctxValue = useMemo<SettingsLayoutContextValue>(() => ({ setContentWidthClass }), []);

  return (
    <SettingsLayoutContext.Provider value={ctxValue}>
      <AppLayout
        hideSidebarMenu
        sidebarOverride={
          <div className="">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/chatbot')}
              aria-label="Ga terug"
              className="text-accent-foreground/60 my-2 w-full flex items-center justify-start"
            >
              <ArrowLeft className="mr-2 h-4 w-4" /> Terug
            </Button>

            <div className="flex flex-col gap-1">
              {sections.map(s => {
                const item = (
                  <NavLink
                    key={s.path}
                    to={s.path}
                    className={({ isActive }) =>
                      [
                        'rounded-md px-2 py-2 text-sm transition-colors flex items-center gap-2',
                        isActive
                          ? 'bg-brand-400/10 text-accent-foreground'
                          : 'hover:bg-brand-400/15 hover:text-accent-foreground',
                      ].join(' ')
                    }
                  >
                    <span className="inline-flex size-4 items-center justify-center">{s.icon}</span>
                    {s.label}
                  </NavLink>
                );

                if (s.path !== 'integrations') return item;

                // Render second-level submenu under Integraties
                return (
                  <div key={s.path} className="flex flex-col gap-1">
                    {item}
                    {officeConnected ? (
                      <div className="ml-6 flex flex-col gap-1">
                        <NavLink
                          to="integrations/office365"
                          className={({ isActive }) =>
                            [
                              'rounded-md px-2 py-1.5 text-sm transition-colors flex items-center gap-2',
                              isActive
                                ? 'bg-brand-400/10 text-accent-foreground'
                                : 'hover:bg-brand-400/15 hover:text-accent-foreground',
                            ].join(' ')
                          }
                        >
                          <img src={outlookSvg} alt="Outlook" className="h-3.5 w-3.5" />
                          Outlook / Office 365
                        </NavLink>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        }
      >
        <div className="flex w-full flex-col">
          <div className={['mx-auto mt-6', contentWidthClass].join(' ')}>
            <Outlet />
          </div>
        </div>
      </AppLayout>
    </SettingsLayoutContext.Provider>
  );
}
