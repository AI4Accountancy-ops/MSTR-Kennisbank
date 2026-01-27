import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface Release {
  version: string;
  date: string;
  isLatest: boolean;
  changes: string[];
}

export default function UpdatesPage() {
  const releases: Release[] = [
    {
      version: '2.0.0',
      date: 'April 15, 2023',
      isLatest: true,
      changes: [
        'Completely redesigned dashboard interface',
        'Added dark mode support across all pages',
        'Improved performance by 40%',
        'Fixed multiple accessibility issues',
        'API endpoints restructured for v2',
      ],
    },
    {
      version: '1.9.0',
      date: 'March 2, 2023',
      isLatest: false,
      changes: [
        'Added new analytics dashboard',
        'Enhanced mobile responsiveness',
        'Fixed bug with user authentication',
      ],
    },
    {
      version: '1.8.0',
      date: 'February 10, 2023',
      isLatest: false,
      changes: [
        'Added team collaboration features',
        'Improved form validation',
        'Updated documentation',
      ],
    },
    {
      version: '1.7.0',
      date: 'January 15, 2023',
      isLatest: false,
      changes: [
        'Added support for custom themes',
        'Enhanced search functionality',
        'Fixed account settings issues',
      ],
    },
  ];

  // Format date
  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
  };

  return (
    <div className="w-full bg-background container mx-auto px-4 md:px-6 py-8 md:py-16 lg:py-20">
      <div className="flex mb-16 flex-col items-center justify-center space-y-4 text-center">
        <h1 className="text-primary leading-tight max-w-4xl text-4xl font-semibold tracking-tight text-balance lg:leading-[1.1] lg:font-semibold xl:text-5xl xl:tracking-tighter">
          Changelog
        </h1>
        <p className="text-foreground max-w-4xl text-base text-balance sm:text-lg">
          Blijf op de hoogte van de laatste wijzigingen in ons product.
        </p>
      </div>

      <div className="space-y-10 max-w-2xl mx-auto">
        {releases.map((release, releaseIndex) => (
          <div
            key={release.version}
            className={cn(
              'animate-fadeIn',
              releaseIndex === 0 ? 'opacity-100' : `opacity-[0.${9 - releaseIndex}]`,
            )}
            style={{
              animationDelay: `${releaseIndex * 100}ms`,
              animationFillMode: 'both',
            }}
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-semibold tracking-tight">v{release.version}</h3>
                {release.isLatest && <Badge className="font-medium">Latest</Badge>}
              </div>
              <time className="text-muted-foreground text-sm font-medium">
                {formatDate(release.date)}
              </time>
            </div>

            <ul className="space-y-3">
              {release.changes.map((change, changeIndex) => (
                <li
                  key={changeIndex}
                  className={cn(
                    'animate-slideIn relative pl-5',
                    'before:absolute before:top-[0.6em] before:left-0 before:h-1.5 before:w-1.5 before:rounded-full',
                    changeIndex === 0 ? 'before:bg-primary' : 'before:bg-muted-foreground/50',
                  )}
                  style={{
                    animationDelay: `${200 + changeIndex * 50 + releaseIndex * 100}ms`,
                    animationFillMode: 'both',
                  }}
                >
                  {change}
                </li>
              ))}
            </ul>

            {releaseIndex < releases.length - 1 && <Separator className="mt-8" />}
          </div>
        ))}
      </div>
    </div>
  );
}
