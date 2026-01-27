import { useState } from 'react';

import { Button } from '~/components/ui/button';
import { Checkbox } from '~/components/ui/checkbox';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';

interface WebhookModalProps {
  isOpen: boolean;
  onClose: () => void;
  webhook?: {
    id: string;
    url: string;
    events: string[];
    status: 'active' | 'inactive';
  };
}

const AVAILABLE_EVENTS = [
  { id: 'user.created', label: 'Gebruiker aangemaakt' },
  { id: 'user.updated', label: 'Gebruiker bijgewerkt' },
  { id: 'user.deleted', label: 'Gebruiker verwijderd' },
  { id: 'workspace.updated', label: 'Workspace bijgewerkt' },
  { id: 'plan.changed', label: 'Plan gewijzigd' },
  { id: 'usage.threshold', label: 'Gebruikslimiet bereikt' },
];

export default function WebhookModal({ isOpen, onClose, webhook }: WebhookModalProps) {
  const [url, setUrl] = useState(webhook?.url || '');
  const [selectedEvents, setSelectedEvents] = useState<string[]>(webhook?.events || []);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditMode = !!webhook;

  const handleEventToggle = (eventId: string, checked: boolean) => {
    if (checked) {
      setSelectedEvents([...selectedEvents, eventId]);
    } else {
      setSelectedEvents(selectedEvents.filter(id => id !== eventId));
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // TODO: Implement webhook save logic
      console.log('Saving webhook:', { url, events: selectedEvents });
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      onClose();
    } catch (error) {
      console.error('Error saving webhook:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Webhook bewerken' : 'Nieuwe webhook toevoegen'}</DialogTitle>
          <DialogDescription>
            {isEditMode
              ? 'Wijzig de instellingen van uw webhook.'
              : 'Configureer een nieuwe webhook endpoint voor real-time notificaties.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook-url">Webhook URL</Label>
            <Input
              id="webhook-url"
              type="url"
              placeholder="https://example.com/webhook"
              value={url}
              onChange={e => setUrl(e.target.value)}
              required
            />
          </div>

          <div className="space-y-3">
            <Label>Gebeurtenissen</Label>
            <p className="text-sm text-muted-foreground">
              Selecteer welke gebeurtenissen u wilt ontvangen
            </p>
            <div className="space-y-2">
              {AVAILABLE_EVENTS.map(event => (
                <div key={event.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={event.id}
                    checked={selectedEvents.includes(event.id)}
                    onCheckedChange={checked => handleEventToggle(event.id, !!checked)}
                  />
                  <Label htmlFor={event.id} className="text-sm">
                    {event.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            Annuleren
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!url || selectedEvents.length === 0 || isSubmitting}
          >
            {isSubmitting ? 'Opslaan...' : isEditMode ? 'Bijwerken' : 'Toevoegen'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
