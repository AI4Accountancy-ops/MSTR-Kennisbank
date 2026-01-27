import type { IPublicClientApplication } from '@azure/msal-browser';

// Import the MSAL instance
import { msalInstance } from '../../msal';

/**
 * Gets user ID from either MSAL authentication or B2C token stored in localStorage
 * @returns User ID as a string, or empty string if no user ID is available
 */
export const getUserId = (): string => {
  try {
    // First, check MSAL authentication
    const msalAccounts = msalInstance?.getAllAccounts();
    if (msalAccounts && msalAccounts.length > 0) {
      return msalAccounts[0].localAccountId || '';
    }

    // If no MSAL account, check B2C token
    const b2cUserData = localStorage.getItem('b2c_user');
    if (b2cUserData) {
      try {
        const userData = JSON.parse(b2cUserData);
        if (userData.sub) {
          return userData.sub;
        }
      } catch (error) {
        console.error('Error parsing B2C user data:', error);
      }
    }

    return '';
  } catch (error) {
    console.error('Error getting user ID:', error);
    return '';
  }
};

export const logoutUser = async (instance: IPublicClientApplication) => {
  try {
    // Capture the active account before clearing state
    const account = instance.getAllAccounts()[0];

    // Clear all tokens and cache first
    await instance.clearCache();

    // Set active account to null
    instance.setActiveAccount(null);

    // Clear any stored state
    localStorage.clear();
    sessionStorage.clear();

    // Clear browser cookies that might be related to authentication
    // This helps with federated providers like Google
    document.cookie.split(';').forEach(cookie => {
      const eqPos = cookie.indexOf('=');
      const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
      document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
    });

    // Use a client-side redirect with cache control headers
    await instance.logoutRedirect({
      account,
      postLogoutRedirectUri: window.location.origin,
      onRedirectNavigate: () => {
        // Force reload the page with cache clearing
        window.location.href = window.location.origin + '?logout=' + new Date().getTime();
        return false; // Prevent the default navigation
      },
    });
  } catch (error) {
    console.error('Logout error:', error);

    // Handle error case with a forced reload approach
    localStorage.clear();
    sessionStorage.clear();

    // Force a hard refresh to clear browser cache
    window.location.href = window.location.origin + '?logout=' + new Date().getTime();
  }
};
