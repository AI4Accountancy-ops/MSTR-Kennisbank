import { cn } from '@/lib/utils';

interface Props extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

export default function OutlookIcon({ className, ...props }: Props) {
  return (
    <svg
      viewBox="0 0 48 48"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      className={cn(className)}
      {...props}
    >
      {/* Background tile using currentColor to allow theming (set via className) */}
      <rect x="2" y="6" width="40" height="36" rx="6" fill="currentColor" />
      {/* Simple envelope flap */}
      <path
        d="M6 14h32v18c0 1.657-1.343 3-3 3H9c-1.657 0-3-1.343-3-3V14z"
        fill="#ffffff"
        opacity="0.12"
      />
      <path d="M9 14h26l-13 9L9 14z" fill="#ffffff" opacity="0.3" />
      {/* Stylized O mark */}
      <circle cx="36" cy="24" r="10" fill="#ffffff" opacity="0.9" />
      <circle cx="36" cy="24" r="6" fill="currentColor" />
    </svg>
  );
}
