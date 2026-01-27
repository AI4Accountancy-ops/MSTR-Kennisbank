import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Loader2 } from 'lucide-react';

import LoginAuthentication from '@features/Authentication';

export default function Index() {
  const isAuthenticated = useIsAuthenticated();
  const navigate = useNavigate();
  const { instance, accounts } = useMsal();
  const [processingAuth, setProcessingAuth] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    console.log('Index page - isAuthenticated:', isAuthenticated);
    console.log('Index page - accounts:', accounts);
    console.log('Index page - hash:', window.location.hash);
    console.log('Index page - checking for stored token...');

    // Check if we have a stored token before checking hash
    const storedToken = localStorage.getItem('b2c_token');
    if (storedToken) {
      console.log('Index page - found stored token, redirecting to home');
      navigate('/chatbot', { replace: true });
      return;
    }

    // Check for hash in the URL that may contain tokens
    if (window.location.hash && window.location.hash.includes('id_token')) {
      setProcessingAuth(true);
      console.log('Found id_token in hash, attempting to process...');

      try {
        // Extract id_token from hash
        const idTokenMatch = window.location.hash.match(/id_token=([^&]*)/);
        if (idTokenMatch && idTokenMatch[1]) {
          const idToken = idTokenMatch[1];
          console.log('Extracted token from hash');

          // Decode token payload
          const tokenParts = idToken.split('.');
          if (tokenParts.length === 3) {
            const tokenPayload = JSON.parse(atob(tokenParts[1]));
            console.log('Token payload:', tokenPayload);

            // Store token in localStorage for session persistence
            localStorage.setItem('b2c_token', idToken);
            localStorage.setItem(
              'b2c_user',
              JSON.stringify({
                name: tokenPayload.name || tokenPayload.emails?.[0] || 'User',
                email: tokenPayload.emails?.[0] || '',
                sub: tokenPayload.sub,
                user_id: tokenPayload.sub,
              }),
            );

            console.log('Index page - token stored, redirecting to home');

            // Clear the hash and redirect to home immediately
            window.location.hash = '';
            navigate('/chatbot', { replace: true });
            return;
          }
        }
      } catch (error) {
        console.error('Error processing token:', error);
        setAuthError('Failed to process authentication response');
        setProcessingAuth(false);
      }

      return; // Exit early to prevent redirect logic below
    }

    // Normal authenticated check
    if (isAuthenticated) {
      console.log('User is authenticated via MSAL, redirecting to home');
      navigate('/chatbot');
    }
  }, [isAuthenticated, navigate, instance, accounts]);

  if (processingAuth) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="h-10 w-10 animate-spin" />
        <h2 className="mt-4 text-lg font-semibold">Completing authentication...</h2>
      </div>
    );
  }

  if (authError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h2 className="mb-4 text-lg font-semibold text-destructive" role="alert">
          {authError}
        </h2>
        <p className="text-muted-foreground">Please try logging in again.</p>
      </div>
    );
  }

  return (
    <main className="relative flex h-full items-center justify-center before:absolute before:inset-0 before:-z-10 before:bg-[radial-gradient(ellipse_at_50%_50%,hsl(0,0%,50%),hsl(0,0%,100%))] dark:before:bg-[radial-gradient(ellipse_at_50%_50%,hsla(39,95.2%,49.2%,0.28),hsl(0,30%,5%))]">
      <LoginAuthentication />
    </main>
  );
}
