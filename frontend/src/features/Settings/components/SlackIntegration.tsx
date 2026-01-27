import { useState } from 'react';
import { MessageSquare } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';

export default function SlackIntegration() {
  const [isConnected, setIsConnected] = useState(false);
  const [teamName, setTeamName] = useState('AI4Accountancy Team');
  const [defaultChannel, setDefaultChannel] = useState('#general');
  const [isLoading, setIsLoading] = useState(false);

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Slack OAuth connection
      console.log('Connecting to Slack...');
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate OAuth flow
      setIsConnected(true);
    } catch (error) {
      console.error('Error connecting to Slack:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Slack disconnection
      console.log('Disconnecting from Slack...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      setIsConnected(false);
    } catch (error) {
      console.error('Error disconnecting from Slack:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Slack test message
      console.log('Testing Slack connection...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      // Show success message
    } catch (error) {
      console.error('Error testing Slack connection:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    return isConnected ? (
      <Badge className="bg-green-100 text-green-800">Verbonden</Badge>
    ) : (
      <Badge variant="outline">Niet verbonden</Badge>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 bg-purple-100 rounded flex items-center justify-center">
            <MessageSquare className="h-4 w-4 text-purple-600" />
          </div>
          <div>
            <h3 className="font-medium">Slack</h3>
            <p className="text-sm text-muted-foreground">Integreer met uw Slack workspace</p>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {isConnected ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="team-name">Team naam</Label>
              <Input
                id="team-name"
                value={teamName}
                onChange={e => setTeamName(e.target.value)}
                disabled
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="default-channel">Standaard kanaal</Label>
              <Input
                id="default-channel"
                value={defaultChannel}
                onChange={e => setDefaultChannel(e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={handleTestConnection} disabled={isLoading}>
              {isLoading ? 'Testen...' : 'Test verbinding'}
            </Button>
            <Button variant="outline" onClick={handleDisconnect} disabled={isLoading}>
              {isLoading ? 'Verbreken...' : 'Verbinding verbreken'}
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>
              Uw Slack integratie is actief. Notificaties worden verzonden naar{' '}
              <strong>{defaultChannel}</strong> in <strong>{teamName}</strong>.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p>
              Verbind uw workspace met Slack om real-time notificaties te ontvangen over belangrijke
              gebeurtenissen en updates.
            </p>
          </div>

          <Button onClick={handleConnect} disabled={isLoading} className="w-full">
            {isLoading ? 'Verbinden...' : 'Verbind met Slack'}
          </Button>

          <div className="text-xs text-muted-foreground">
            <p>
              Door te verbinden geeft u AI4Accountancy toestemming om berichten te verzenden naar uw
              Slack workspace.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
