import { createContext, useContext, ReactNode } from 'react';
import { Toaster, toast } from 'sonner';

interface ToastContextType {
  showToast: (message: string, severity?: 'success' | 'error' | 'warning' | 'info') => void;
}

interface ToastProviderProps {
  children: ReactNode;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: ToastProviderProps) {
  const showToast = (
    message: string,
    severity: 'success' | 'error' | 'warning' | 'info' = 'success',
  ) => {
    const toastMap = {
      success: (msg: string) => toast.success(msg),
      error: (msg: string) => toast.error(msg),
      warning: (msg: string) => toast.warning(msg),
      info: (msg: string) => toast.info(msg),
    };
    toastMap[severity](message);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      <Toaster richColors position="bottom-center" />
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
