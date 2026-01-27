import { useEffect, useState } from 'react';
import { BrowserRouter as Router } from 'react-router';
import { MsalProvider } from '@azure/msal-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import AppRoutes from '~/AppRoutes';
import { ThemeProvider } from '~/components/theme-provider';
import { ChatProvider } from '~/context/ChatContext';
import { ChatHistoryProvider } from '@features/ChatHistory/context/ChatHistoryContext';
import { msalInstance } from '~/msal';
import { authService } from '~/services/authService';
import { ToastProvider } from '~/context/ToastContext';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initialize = async () => {
      try {
        // Initialize authentication
        await authService.initialize();
      } catch (error) {
        console.error('Error during initialization:', error);
      } finally {
        setIsInitialized(true);
      }
    };

    initialize();

    // Add event listener for page loads
    window.addEventListener('load', initialize);

    // Add listener for hash changes (for redirection with tokens)
    const handleHashChange = () => {
      console.log('URL hash changed. New hash:', window.location.hash);
      initialize();
    };
    window.addEventListener('hashchange', handleHashChange);

    return () => {
      window.removeEventListener('load', initialize);
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <MsalProvider instance={msalInstance}>
          <ChatProvider>
            <Router>
              <ChatHistoryProvider>
                <ToastProvider>
                  <AppRoutes />
                </ToastProvider>
              </ChatHistoryProvider>
            </Router>
          </ChatProvider>
        </MsalProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
