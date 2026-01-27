import { Configuration } from '@azure/msal-browser';

// Microsoft login configuration
export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_CLIENT_ID || '',
    authority: import.meta.env.VITE_AUTHORITY || '',
    redirectUri: `${window.location.origin}${import.meta.env.VITE_REDIRECT_PATH || ''}`,
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: true,
  },
};

// Microsoft login request
export const loginRequest = {
  scopes: ['openid', 'profile', 'email', 'User.Read'],
  prompt: 'select_account',
};

export const authRequest = {
  ...loginRequest,
};
