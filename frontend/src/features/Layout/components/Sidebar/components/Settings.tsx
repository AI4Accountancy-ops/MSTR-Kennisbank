import React from 'react';
import { X } from 'lucide-react';
import ColorModeSwitchToggle from '~/theme/ColorModeSwitchToggle';
import { Button } from '~/components/ui/button';

const Settings: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-[1300] flex items-center justify-center bg-black/50 p-2">
      <div className="w-full max-w-[600px] rounded-lg border bg-background p-4 shadow-lg">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xl font-semibold">Settings</h3>
          <Button type="button" size="icon" variant="ghost" onClick={onClose} className="-mt-1">
            <X className="size-4" />
          </Button>
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium text-muted-foreground">Appearance</span>
            <div className="flex items-center gap-2">
              <ColorModeSwitchToggle />
              <div>
                <div className="text-sm">Theme Mode</div>
                <div className="text-xs text-muted-foreground">
                  Switch between light and dark theme
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
