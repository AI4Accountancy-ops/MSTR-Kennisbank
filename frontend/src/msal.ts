import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig } from '@features/Authentication/config';

// Initialize and export MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig); 