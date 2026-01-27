import { useEffect } from 'react';
import { useSettingsLayout } from '../../components/SettingsLayout';
import OfficeEmailInbox from '../../components/OfficeEmailInbox';

export default function Office365() {
  const { setContentWidthClass } = useSettingsLayout();

  // Expand content width on this page; restore default on unmount
  useEffect(() => {
    setContentWidthClass('w-[70%] max-w-6xl');
    return () => setContentWidthClass('w-[50%] max-w-5xl');
  }, [setContentWidthClass]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Microsoft 365</h1>
        <p className="text-muted-foreground">
          Beheer uw Outlook/Office 365-koppeling en instellingen.
        </p>
      </div>

      <OfficeEmailInbox />
    </div>
  );
}
