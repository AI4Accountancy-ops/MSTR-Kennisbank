import { Link } from 'react-router';
import { LinkedinIcon, InstagramIcon } from '@/assets/icons';
import { ArrowUpIcon } from 'lucide-react';

const footerLinks = [
  {
    title: 'Product',
    links: [{ title: 'Prijzen', href: '/pricing' }],
  },
  {
    title: 'Bronnen',
    links: [{ title: 'Contact', href: '#' }],
  },
  {
    title: 'Juridisch',
    links: [
      { title: 'Privacy', href: 'https://www.ai4accountancy.nl/privacy-and-algemene-voorwaarden/' },
    ],
  },
];

const socialLinks = [
  {
    icon: LinkedinIcon,
    href: 'https://www.linkedin.com/in/ai4accountancy/',
    label: 'LinkedIn',
  },
  {
    icon: InstagramIcon,
    href: 'https://www.instagram.com/ai4accountancy',
    label: 'Instagram',
  },
];

export default function MarketingFooter() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="bg-background w-full border-t">
      <div className="container mx-auto px-4 py-12 md:px-6 2xl:max-w-[1400px]">
        <div className="flex flex-col justify-between md:flex-row">
          <div className="mb-8 md:mb-0">
            <Link to="/" className="flex items-center space-x-2">
              <span className="text-xl font-bold">AI4Accountancy</span>
            </Link>
            <p className="text-muted-foreground mt-4 max-w-xs text-sm">
              Next level, tevreden klanten.
            </p>
            <div className="mt-6 flex gap-4">
              {socialLinks.map(link => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={link.label}
                  target="_blank"
                  rel="noreferrer"
                >
                  <link.icon className="h-5 w-5" />
                </a>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {footerLinks.map(group => (
              <div key={group.title} className="space-y-3">
                <h3 className="text-sm font-medium">{group.title}</h3>
                <ul className="space-y-2">
                  {group.links.map(link => (
                    <li key={link.title}>
                      <Link
                        to={link.href}
                        className="text-muted-foreground hover:text-foreground text-sm transition-colors"
                      >
                        {link.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 flex flex-col-reverse items-center justify-between gap-4 border-t pt-8 md:flex-row">
          <p className="text-muted-foreground text-center text-sm md:text-left">
            &copy; {new Date().getFullYear()} AI4Accountancy. All rights reserved.
          </p>
          <button
            onClick={scrollToTop}
            className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm transition-colors"
            aria-label="Scroll to top"
          >
            Terug naar boven <ArrowUpIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </footer>
  );
}
