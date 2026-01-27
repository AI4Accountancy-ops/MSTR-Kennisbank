import { IPublicClientApplication } from '@azure/msal-browser';
import { msalInstance } from '~/msal';
import { API_BASE_URL } from '~/config/environment';

/**
 * Interface for token payload from B2C authentication
 */
interface TokenPayload {
  sub: string;
  iss?: string;
  email?: string;
  name?: string;
}

/**
 * Interface for user information to be stored
 */
interface UserInfo {
  name: string;
  email: string;
  sub: string;
  user_id: string;
  is_subscribed: boolean;
}

/**
 * Service for handling authentication operations
 */
interface LoginBackendResponse {
  readonly status: string;
  readonly message?: string;
  readonly next?: 'checkout' | 'choose_plan' | 'app';
  readonly checkout_url?: string;
  readonly user_id?: string;
  readonly request_id?: string;
}

export class AuthService {
  private msalInstance: IPublicClientApplication;
  // Track in-flight login requests to prevent duplicates
  private pendingLoginRequests: Map<
    string,
    Promise<{ success: boolean; message?: string; backend?: LoginBackendResponse }>
  > = new Map();

  constructor(msalInstance: IPublicClientApplication) {
    this.msalInstance = msalInstance;
  }

  /**
   * Initialize MSAL and handle authentication state
   * @returns Promise that resolves when initialization is complete
   */
  public async initialize(): Promise<void> {
    try {
      await this.msalInstance.initialize();
      console.log('MSAL initialized successfully');

      const urlHash = window.location.hash;
      if (urlHash && urlHash.length > 0) {
        console.log('Found hash in URL, processing authentication response');
      }

      const redirectResponse = await this.msalInstance.handleRedirectPromise();
      console.log('Redirect response:', redirectResponse);

      const accounts = this.msalInstance.getAllAccounts();
      console.log('Accounts after initialization:', accounts);

      if (accounts.length > 0) {
        console.log('Setting active account:', accounts[0]);
        this.msalInstance.setActiveAccount(accounts[0]);

        // Save Microsoft user to backend and honor backend next steps
        if (redirectResponse) {
          const account = accounts[0];
          const userInfo: UserInfo = {
            name: account.name || 'User',
            email: account.username || '',
            sub: account.localAccountId,
            user_id: account.localAccountId,
            is_subscribed: false,
          };

          const saveResult = await this.saveUserToBackend(userInfo, 'microsoft');
          if (!saveResult.success) {
            // Log but continue - don't block login flow on save failure
            console.warn(`User data save warning: ${saveResult.message}`);
          } else {
            console.log('User data saved successfully:', saveResult.message);
          }
          await this.handlePostLoginNext(saveResult.backend);
        }
      } else {
        console.log('No accounts found after initialization');
        await this.handleManualTokenProcessing(urlHash);
      }
    } catch (error) {
      console.error('Error initializing MSAL:', error);
      throw error;
    }
  }

  /**
   * Process authentication token manually if automatic processing fails
   * @param urlHash - URL hash containing authentication information
   * @returns Promise that resolves when processing is complete
   */
  private async handleManualTokenProcessing(urlHash: string): Promise<void> {
    if (!urlHash) {
      return;
    }

    console.log('Attempting to manually parse hash:', urlHash);

    const idTokenMatch = urlHash.match(/id_token=([^&]*)/);
    if (!idTokenMatch || !idTokenMatch[1]) {
      return;
    }

    console.log('Found ID token in URL hash, attempting to process manually');

    try {
      const idToken = idTokenMatch[1];
      const tokenPayload = this.decodeToken(idToken);

      if (tokenPayload && tokenPayload.email) {
        // storeUserInformation now handles the redirect
        await this.storeUserInformation(idToken, tokenPayload);
      }
    } catch (tokenError) {
      console.error('Error processing ID token:', tokenError);
      throw tokenError;
    }
  }

  /**
   * Decode JWT token to extract payload
   * @param token - JWT token to decode
   * @returns Decoded token payload or null if invalid
   */
  private decodeToken(token: string): TokenPayload | null {
    const tokenParts = token.split('.');
    if (tokenParts.length !== 3) {
      return null;
    }

    try {
      return JSON.parse(atob(tokenParts[1]));
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  }

  /**
   * Store user information and token in localStorage
   * @param idToken - Authentication token
   * @param tokenPayload - Decoded token payload
   */
  private async storeUserInformation(idToken: string, tokenPayload: TokenPayload): Promise<void> {
    localStorage.setItem('b2c_token', idToken);

    const userInfo: UserInfo = {
      name: tokenPayload.name || tokenPayload.email || 'User',
      email: tokenPayload.email || '',
      sub: tokenPayload.sub,
      user_id: tokenPayload.sub,
      is_subscribed: false,
    };

    localStorage.setItem('b2c_user', JSON.stringify(userInfo));
    console.log('Token stored in localStorage');

    // Call the login API to save user information in the database and follow backend instructions
    const saveResult = await this.saveUserToBackend(userInfo, 'google');
    if (!saveResult.success) {
      // Log but continue - we'll still redirect
      console.warn(`User data save warning: ${saveResult.message}`);
    } else {
      console.log('User data saved successfully:', saveResult.message);
    }
    await this.handlePostLoginNext(saveResult.backend);
  }

  /**
   * Save user information to the backend
   * @param userInfo - User information to save
   * @param authProvider - Authentication provider (microsoft or google)
   * @returns Promise resolving to success status and message
   */
  private saveUserToBackend(
    userInfo: UserInfo,
    authProvider: 'microsoft' | 'google',
  ): Promise<{ success: boolean; message?: string; backend?: LoginBackendResponse }> {
    // Generate unique key for the user to track pending requests
    const requestKey = `${userInfo.user_id}:${authProvider}`;

    // Check if there's already a pending request for this user
    if (this.pendingLoginRequests.has(requestKey)) {
      console.log(`Reusing existing login request for ${userInfo.user_id}`);
      return this.pendingLoginRequests.get(requestKey)!;
    }

    // Create a new request and store it in the pending requests map
    const requestPromise = this._executeLoginRequest(userInfo, authProvider).finally(() => {
      // Remove from pending requests when done
      this.pendingLoginRequests.delete(requestKey);
    });

    // Store the promise in the map so we can reuse it
    this.pendingLoginRequests.set(requestKey, requestPromise);
    return requestPromise;
  }

  /**
   * Execute the actual login request to the backend
   * @param userInfo - User information to save
   * @param authProvider - Authentication provider
   * @returns Promise resolving to success status and message
   */
  private async _executeLoginRequest(
    userInfo: UserInfo,
    authProvider: 'microsoft' | 'google',
  ): Promise<{ success: boolean; message?: string; backend?: LoginBackendResponse }> {
    let retryCount = 0;
    const maxRetries = 3; // Maximum number of retry attempts

    while (retryCount < maxRetries) {
      try {
        console.log(`Saving user information to backend (attempt ${retryCount + 1}):`, userInfo);

        const selectedPriceId = localStorage.getItem('selected_price_id') || undefined;
        const origin = window.location.origin;
        const successUrl = `${origin}/billing/success`;
        const cancelUrl = `${origin}/billing/cancel`;

        const requestBody = {
          user_id: userInfo.user_id,
          email: userInfo.email,
          name: userInfo.name,
          auth_provider: authProvider,
          is_subscribed: userInfo.is_subscribed,
          selected_price_id: selectedPriceId,
          success_url: successUrl,
          cancel_url: cancelUrl,
        };

        // Validate required fields before sending
        if (!requestBody.user_id) {
          console.error('Missing required field: user_id');
          return { success: false, message: 'Missing user ID' };
        }

        if (!requestBody.email) {
          console.error('Missing required field: email');
          return { success: false, message: 'Missing email' };
        }

        const response = await fetch(`${API_BASE_URL}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        // Handle HTTP error status codes
        if (!response.ok) {
          const errorText = await response.text();
          const errorStatus = response.status;

          console.error(`Backend login error (${errorStatus}):`, errorText);

          // Handle 409 Conflict (duplicate key) specially - this is not an error from the client's perspective
          if (errorStatus === 409) {
            console.log('User already exists in database, continuing...');
            return { success: true, message: 'User already exists' };
          }

          // For server errors, retry the request
          if (errorStatus >= 500 && retryCount < maxRetries - 1) {
            console.log(`Retrying due to server error (${errorStatus})...`);
            retryCount++;
            // Exponential backoff: wait longer between each retry
            await new Promise(resolve => setTimeout(resolve, 1000 * 2 ** retryCount));
            continue;
          }

          return {
            success: false,
            message: `Server error (${errorStatus}): ${errorText}`,
          };
        }

        // Response is OK, parse the JSON
        const data = (await response.json()) as LoginBackendResponse;
        console.log('Backend login response:', data);

        if (data.status !== 'success') {
          console.error('Failed to save user information:', data.message);
          return { success: false, message: data.message || 'Unknown error' };
        }

        return { success: true, message: data.message, backend: data };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error('Error saving user information to backend:', errorMessage);

        // For network errors, retry the request
        if (
          error instanceof TypeError &&
          error.message.includes('network') &&
          retryCount < maxRetries - 1
        ) {
          console.log('Retrying due to network error...');
          retryCount++;
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, 1000 * 2 ** retryCount));
          continue;
        }

        return { success: false, message: `Network error: ${errorMessage}` };
      }
    }

    // If we've reached here, we've exhausted all retries
    return { success: false, message: 'Failed after multiple attempts' };
  }

  /**
   * Redirect to home page after successful authentication
   */
  private redirectToHome(): void {
    window.location.hash = '';
    window.location.href = `${window.location.origin}/home`;
  }

  private async handlePostLoginNext(backend?: LoginBackendResponse): Promise<void> {
    try {
      const selectedKey = 'selected_price_id';
      // Clear any stored plan selection; backend response will dictate next step
      const clearSelected = () => {
        try {
          localStorage.removeItem(selectedKey);
        } catch {
          /* ignore */
        }
      };

      if (!backend || !backend.next) {
        clearSelected();
        this.redirectToHome();
        return;
      }

      if (
        backend.next === 'checkout' &&
        typeof backend.checkout_url === 'string' &&
        backend.checkout_url.length > 0
      ) {
        // Ensure the user has at least one organization before redirecting to Stripe
        try {
          const userRaw = localStorage.getItem('b2c_user');
          const userId = userRaw ? (JSON.parse(userRaw) as { user_id?: string }).user_id || '' : '';
          if (userId.length === 0) {
            window.location.href = `${window.location.origin}/onboarding/create-organization`;
            return;
          }
          const { organizationService } = await import('~/services/organizationService');
          const myOrgs = await organizationService.listMyOrganizations({ user_id: userId });
          if (!Array.isArray(myOrgs.organizations) || myOrgs.organizations.length === 0) {
            window.location.href = `${window.location.origin}/onboarding/create-organization`;
            return;
          }
        } catch {
          window.location.href = `${window.location.origin}/onboarding/create-organization`;
          return;
        }

        clearSelected();
        window.location.replace(backend.checkout_url);
        return;
      }

      if (backend.next === 'choose_plan') {
        // Keep stored selection if present, user can confirm/edit on pricing
        window.location.href = `${window.location.origin}/pricing`;
        return;
      }

      if (backend.next === 'app') {
        clearSelected();
        this.redirectToHome();
        return;
      }

      // Fallback
      clearSelected();
      this.redirectToHome();
    } catch {
      this.redirectToHome();
    }
  }
}

// Export singleton instance
export const authService = new AuthService(msalInstance);
