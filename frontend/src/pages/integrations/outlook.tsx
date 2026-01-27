import AppLayout from '@features/Layout';
import OfficeEmailInbox from '@features/Settings/components/OfficeEmailInbox';

export default function OutlookIntegrationsPage() {
  return (
    <AppLayout>
      <div className="w-full">
        <div className="mx-auto mt-6 w-[50%] max-w-6xl">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold">Microsoft 365</h1>
              <p className="text-muted-foreground">
                Beheer uw Outlook/Office 365-koppeling en instellingen.
              </p>
            </div>

            <OfficeEmailInbox />
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
