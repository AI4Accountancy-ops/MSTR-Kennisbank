import { cn } from '@/lib/utils';
import logoMobile from '@/assets/images/ai4accountancy_logo_mobile.png';

import type React from 'react';

interface Props extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export default function BrandIcon({ className, ...props }: Props) {
  return (
    <div
      className={cn(
        'rounded-md overflow-hidden p-0.5',
        // Parent can control the overall size, default keeps it modest in nav
        'size-5',
        className,
      )}
      {...props}
    >
      <img src={logoMobile} alt="AI4Accountancy logo" className="h-full w-full object-contain" />
    </div>
  );
}
