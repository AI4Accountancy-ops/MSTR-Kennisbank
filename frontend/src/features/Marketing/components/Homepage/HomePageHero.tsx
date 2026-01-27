import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import { useTheme } from '@/components/theme-provider';
import HeroImageDark from '@/assets/images/hero_image.png';
import HeroImageLight from '@/assets/images/hero_image_light.jpeg';

export default function HomePageHero() {
  const { theme } = useTheme();
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);

  useEffect(() => {
    try {
      const prefersDark =
        typeof window !== 'undefined'
          ? window.matchMedia('(prefers-color-scheme: dark)').matches
          : false;
      const effectiveDark = theme === 'dark' || (theme === 'system' && prefersDark);
      setIsDarkMode(effectiveDark);
    } catch {
      setIsDarkMode(false);
    }
  }, [theme]);
  return (
    <div className="container mx-auto flex flex-col items-center gap-2 px-6 py-8 text-center md:py-16 lg:py-20 xl:gap-4">
      <Badge variant="outline" className="max-w-sm text-balance whitespace-break-spaces">
        <Link to="#" className="flex items-center gap-2">
          Start jouw Gratis Proefperiode
          <ArrowRight className="h-4 w-4" />
        </Link>
      </Badge>

      <h1 className="text-primary leading-tighter max-w-4xl text-4xl font-semibold tracking-tight text-balance lg:leading-[1.1] lg:font-semibold xl:text-5xl xl:tracking-tighter">
        <span
          style={{
            background: 'linear-gradient(190deg, #e9e336, #c63128)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            color: 'transparent',
          }}
        >
          Belasting AI
        </span>
        <br />
        Jouw slimme belastingassistent
      </h1>
      <p className="text-foreground max-w-4xl text-base text-balance sm:text-lg">
        Altijd accuraat advies, gebaseerd op officiële bronnen van Belastingdienst.nl en
        Wetten.overheid.nl
      </p>

      <div className="flex items-center gap-4">
        <Button asChild>
          <Link to="/signup">Aan de slag</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/blog">
            Meer informatie <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
      <div className="p-4 bg-accent rounded-lg border mt-12">
        <img
          src={isDarkMode ? HeroImageDark : HeroImageLight}
          alt="App screenshot"
          width={1920}
          height={1080}
          className="rounded-lg shadow-lg"
        />
      </div>
    </div>
  );
}
