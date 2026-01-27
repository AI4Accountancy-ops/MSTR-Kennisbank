import { useState } from 'react';
import { Plus, Edit, Trash2, TestTube } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table';

interface Webhook {
  id: string;
  url: string;
  events: string[];
  status: 'active' | 'inactive';
  lastTriggered?: string;
}

export default function WebhooksManagement() {
  const [webhooks] = useState<Webhook[]>([
    {
      id: '1',
      url: 'https://example.com/webhook',
      events: ['user.created', 'user.updated'],
      status: 'active',
      lastTriggered: '2025-01-15T10:30:00Z',
    },
  ]);

  const handleAddWebhook = () => {
    // TODO: Implement add webhook logic
    console.log('Add webhook');
  };

  const handleEditWebhook = (webhook: Webhook) => {
    // TODO: Implement edit webhook logic
    console.log('Edit webhook:', webhook);
  };

  const handleDeleteWebhook = (webhook: Webhook) => {
    // TODO: Implement delete webhook logic
    console.log('Delete webhook:', webhook);
  };

  const handleTestWebhook = (webhook: Webhook) => {
    // TODO: Implement test webhook logic
    console.log('Test webhook:', webhook);
  };

  const getStatusBadge = (status: Webhook['status']) => {
    return status === 'active' ? (
      <Badge className="bg-green-100 text-green-800">Actief</Badge>
    ) : (
      <Badge variant="outline">Inactief</Badge>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('nl-NL', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-medium">Geconfigureerde Webhooks</h3>
          <p className="text-sm text-muted-foreground">
            Beheer uw webhook endpoints en gebeurtenissen
          </p>
        </div>
        <Button onClick={handleAddWebhook}>
          <Plus className="h-4 w-4 mr-2" />
          Webhook toevoegen
        </Button>
      </div>

      {webhooks.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground mb-4">Nog geen webhooks geconfigureerd</p>
            <Button onClick={handleAddWebhook}>
              <Plus className="h-4 w-4 mr-2" />
              Eerste webhook toevoegen
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>URL</TableHead>
                <TableHead>Gebeurtenissen</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Laatste trigger</TableHead>
                <TableHead className="text-right">Acties</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhooks.map(webhook => (
                <TableRow key={webhook.id}>
                  <TableCell className="font-mono text-sm">{webhook.url}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {webhook.events.map(event => (
                        <Badge key={event} variant="outline" className="text-xs">
                          {event}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(webhook.status)}</TableCell>
                  <TableCell>
                    {webhook.lastTriggered ? formatDate(webhook.lastTriggered) : 'Nooit'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTestWebhook(webhook)}
                      >
                        <TestTube className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditWebhook(webhook)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteWebhook(webhook)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
