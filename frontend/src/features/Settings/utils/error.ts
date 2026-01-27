export function extractErrorMessage(error: unknown): string {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    // ApiError shape { status?, message, details? }
    const maybeMsg = (error as { message?: unknown }).message;
    if (typeof maybeMsg === 'string' && maybeMsg.length > 0) return maybeMsg;
    try {
      return JSON.stringify(error);
    } catch {
      return 'Onbekende fout';
    }
  }
  return 'Onbekende fout';
}
