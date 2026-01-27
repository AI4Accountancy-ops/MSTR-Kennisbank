interface ErrorStateProps {
  readonly title?: string;
  readonly description?: string;
  readonly onRetry?: () => void;
}

export default function ErrorState({
  title = 'Er is iets misgegaan',
  description = 'Probeer het opnieuw of neem contact op met support als het probleem aanhoudt.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="space-y-2 rounded-md border border-destructive/30 bg-destructive/5 p-4">
      <h4 className="text-sm font-semibold text-destructive">{title}</h4>
      <p className="text-sm text-muted-foreground">{description}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex w-fit items-center rounded-md bg-destructive px-3 py-1.5 text-sm text-destructive-foreground hover:opacity-90"
        >
          Opnieuw proberen
        </button>
      ) : null}
    </div>
  );
}
