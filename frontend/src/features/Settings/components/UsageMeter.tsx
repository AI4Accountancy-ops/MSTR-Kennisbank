import type { CSSProperties } from 'react';

interface UsageMeterProps {
  readonly label: string;
  readonly used: number;
  readonly limit?: number;
  readonly forecast?: number;
  readonly unit: string;
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function getColorClass(ratio: number): string {
  if (ratio <= 0.7) return 'bg-emerald-500';
  if (ratio <= 1) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function UsageMeter({ label, used, limit, forecast, unit }: UsageMeterProps) {
  const max = typeof limit === 'number' && limit > 0 ? limit : used;
  const ratio = max > 0 ? clamp(used / max, 0, 1) : 0;
  const percent = Math.round(ratio * 100);
  const barColor = getColorClass(ratio);

  const forecastPercent =
    typeof forecast === 'number' && max > 0 ? clamp(forecast / max, 0, 1) : undefined;

  const widthStyle: CSSProperties = { width: `${percent}%` };
  const forecastStyle: CSSProperties | undefined =
    typeof forecastPercent === 'number'
      ? { left: `${Math.round(forecastPercent * 100)}%` }
      : undefined;

  return (
    <div className="space-y-1" aria-label={`${label} gebruik`}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          {typeof limit === 'number' ? `${used} / ${limit} ${unit}` : `${used} ${unit}`}
        </span>
      </div>
      <div
        className="relative h-2 w-full rounded-full bg-accent/50"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={used}
      >
        <div className={`h-2 rounded-full ${barColor}`} style={widthStyle} />
        {forecastStyle ? (
          <div
            className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-foreground/60"
            style={forecastStyle}
            aria-label="Prognose"
          />
        ) : null}
      </div>
      {typeof forecast === 'number' ? (
        <div className="text-xs text-muted-foreground">
          Prognose: {forecast} {unit}
        </div>
      ) : null}
    </div>
  );
}
