import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import outlookSvg from '@assets/icons/outlook.svg';

export default function IntegrationsSection() {
  const [officeConnected, setOfficeConnected] = useState(false);

  useEffect(() => {
    const readState = () => {
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

    readState();
    const handler = () => readState();
    window.addEventListener('office365IntegrationChanged', handler);
    window.addEventListener('focus', handler);
    return () => {
      window.removeEventListener('office365IntegrationChanged', handler);
      window.removeEventListener('focus', handler);
    };
  }, []);

  if (!officeConnected) return null;

  return (
    <div className="m-2">
      <div className="pl-1 py-2 block text-brand-400 font-medium text-xs">Integraties</div>
      <div className="p-1">
        <Link
          to="/integrations/outlook"
          className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
        >
          <img src={outlookSvg} alt="Outlook" className="h-3.5 w-3.5" />
          Outlook
        </Link>
      </div>
    </div>
  );
}
