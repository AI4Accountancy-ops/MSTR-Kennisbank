import type { ReactNode } from 'react';

interface LoadingStateProps {
  readonly message?: string;
  readonly skeletonLines?: number;
  readonly headerWidthClassName?: string; // e.g., "w-48"
  readonly className?: string;
  readonly accessory?: ReactNode;
}

export default function LoadingState({
  message = 'Laden...',
  skeletonLines = 3,
  headerWidthClassName = 'w-48',
  className,
  accessory,
}: LoadingStateProps) {
  const lines = Array.from({ length: Math.max(0, skeletonLines) });
  return (
    <div className={['space-y-3', className ?? ''].join(' ')}>
      <div className={['h-8 animate-pulse rounded bg-muted', headerWidthClassName].join(' ')} />
      {lines.map((_, idx) => (
        <div
          key={`line-${idx}`}
          className={['h-4 animate-pulse rounded bg-muted', idx % 2 === 0 ? 'w-3/4' : 'w-2/3'].join(
            ' ',
          )}
        />
      ))}
      <div className="h-64 w-full animate-pulse rounded bg-muted" />
      {accessory}
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
