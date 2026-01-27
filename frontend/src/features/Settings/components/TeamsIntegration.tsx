import { useState } from 'react';
import { Users } from 'lucide-react';

import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';

export default function TeamsIntegration() {
  const [isConnected, setIsConnected] = useState(false);
  const [teamName, setTeamName] = useState('AI4Accountancy Team');
  const [defaultChannel, setDefaultChannel] = useState('Algemeen');
  const [isLoading, setIsLoading] = useState(false);

  const handleConnect = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Microsoft Teams OAuth connection
      console.log('Connecting to Microsoft Teams...');
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate OAuth flow
      setIsConnected(true);
    } catch (error) {
      console.error('Error connecting to Teams:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Teams disconnection
      console.log('Disconnecting from Teams...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      setIsConnected(false);
    } catch (error) {
      console.error('Error disconnecting from Teams:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement Teams test message
      console.log('Testing Teams connection...');
      await new Promise(resolve => setTimeout(resolve, 1000));
      // Show success message
    } catch (error) {
      console.error('Error testing Teams connection:', error);
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
          <div className="h-8 w-8 bg-blue-100 rounded flex items-center justify-center">
            <Users className="h-4 w-4 text-blue-600" />
          </div>
          <div>
            <h3 className="font-medium">Microsoft Teams</h3>
            <p className="text-sm text-muted-foreground">
              Integreer met uw Microsoft Teams workspace
            </p>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {isConnected ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="teams-team-name">Team naam</Label>
              <Input
                id="teams-team-name"
                value={teamName}
                onChange={e => setTeamName(e.target.value)}
                disabled
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="teams-default-channel">Standaard kanaal</Label>
              <Input
                id="teams-default-channel"
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
              Uw Microsoft Teams integratie is actief. Notificaties worden verzonden naar{' '}
              <strong>{defaultChannel}</strong> in <strong>{teamName}</strong>.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p>
              Verbind uw workspace met Microsoft Teams om real-time notificaties te ontvangen over
              belangrijke gebeurtenissen en updates.
            </p>
          </div>

          <Button onClick={handleConnect} disabled={isLoading} className="w-full">
            {isLoading ? 'Verbinden...' : 'Verbind met Microsoft Teams'}
          </Button>

          <div className="text-xs text-muted-foreground">
            <p>
              Door te verbinden geeft u AI4Accountancy toestemming om berichten te verzenden naar uw
              Microsoft Teams workspace.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
