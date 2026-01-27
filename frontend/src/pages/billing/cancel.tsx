import { useNavigate } from 'react-router';

import { Button } from '@/components/ui/button';

export default function BillingCancelPage() {
  const navigate = useNavigate();
  return (
    <div className="container mx-auto px-4 py-16 space-y-6">
      <h1 className="text-2xl font-semibold">Checkout geannuleerd</h1>
      <p className="text-muted-foreground">
        Je hebt de betaling geannuleerd. Je kunt een plan opnieuw kiezen of terugkeren naar de app.
      </p>
      <div className="flex gap-3">
        <Button onClick={() => navigate('/pricing')}>Kies een plan</Button>
        <Button variant="outline" onClick={() => navigate('/')}>
          Terug naar home
        </Button>
      </div>
    </div>
  );
}
