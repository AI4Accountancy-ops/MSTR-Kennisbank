import { useRef, useEffect } from 'react';

export const useNetworkTracking = () => {
  const networkRequestCompleted = useRef(false);

  // Network observer effect
  useEffect(() => {
    const requestObserver = new PerformanceObserver(list => {
      for (const entry of list.getEntries()) {
        const resourceEntry = entry as PerformanceResourceTiming;

        // More precise matching for the specific chat endpoint
        if (entry.name.endsWith('/api/chat') && resourceEntry.initiatorType === 'fetch') {
          networkRequestCompleted.current = true;
        }
      }
    });

    requestObserver.observe({ entryTypes: ['resource'] });

    return () => {
      requestObserver.disconnect();
    };
  }, []);

  return {
    networkRequestCompleted,
  };
};
