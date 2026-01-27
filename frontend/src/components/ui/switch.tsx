import * as React from 'react';
import * as SwitchPrimitive from '@radix-ui/react-switch';

import { cn } from '@/lib/utils';

type SwitchVariant = 'default' | 'mui';

function Switch({
  className,
  variant = 'default',
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root> & { variant?: SwitchVariant }) {
  const rootBase =
    'peer inline-flex shrink-0 items-center rounded-full border border-transparent shadow-xs transition-all outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50';

  const rootVariant =
    variant === 'mui'
      ? 'h-[26px] w-12 data-[state=checked]:bg-[hsl(39,98%,48%)] data-[state=unchecked]:bg-[#aab4be] dark:data-[state=unchecked]:bg-[#8796A5]'
      : 'h-[1.15rem] w-8 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input dark:data-[state=unchecked]:bg-input/80';

  const thumbBase = 'pointer-events-none block rounded-full ring-0 transition-transform';

  const thumbVariant =
    variant === 'mui'
      ? 'size-[24px] bg-white data-[state=checked]:translate-x-[calc(100%-2px)] data-[state=unchecked]:translate-x-0'
      : 'size-4 bg-background dark:data-[state=unchecked]:bg-foreground dark:data-[state=checked]:bg-primary-foreground data-[state=checked]:translate-x-[calc(100%-2px)] data-[state=unchecked]:translate-x-0';

  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(rootBase, rootVariant, className)}
      {...props}
    >
      <SwitchPrimitive.Thumb data-slot="switch-thumb" className={cn(thumbBase, thumbVariant)} />
    </SwitchPrimitive.Root>
  );
}

export { Switch };
