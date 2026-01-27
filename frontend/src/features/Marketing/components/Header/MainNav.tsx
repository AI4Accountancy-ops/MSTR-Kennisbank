import { Link } from 'react-router';
import { useLocation } from 'react-router';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export const navLinks = [
  {
    href: '/pricing',
    label: 'Prijzen', // Dutch for "Pricing"
  },
  {
    href: '/contact',
    label: 'Contact', // Dutch for "Contact"
  },
  {
    href: '/updates',
    label: 'Updates',
  },
];

export function MainNav({ className, ...props }: React.ComponentProps<'nav'>) {
  const { pathname } = useLocation();

  return (
    <nav className={cn('items-center gap-0.5', className)} {...props}>
      {navLinks.map(item => (
        <Button key={item.href} variant="ghost" asChild size="sm">
          <Link to={item.href} className={cn(pathname === item.href && 'text-primary')}>
            {item.label}
          </Link>
        </Button>
      ))}
    </nav>
  );
}
