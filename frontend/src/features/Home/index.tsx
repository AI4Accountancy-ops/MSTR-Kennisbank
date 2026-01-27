import { useEffect, useState } from 'react';
import { Sparkles, ShieldCheck, Gauge, Database, Cloud, Globe2, Shield, Copy } from 'lucide-react';

import { Button } from '~/components/ui/button';
import { Card, CardContent } from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '~/components/ui/tooltip';
import { useChatOperations } from '@features/Layout/components/Sidebar/hooks/useChatOperations';

export default function Home() {
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [copyTooltip, setCopyTooltip] = useState('Kopieer naar klembord');
  const { handleNewChat } = useChatOperations();

  const prompts: { text: string; context: string }[] = [
    {
      text: 'Kan een BV gebruikmaken van artikel 3.64 Wet IB 2001 om de boekwinst op goodwill/inventaris door te schuiven naar een nieuwe onderneming binnen dezelfde BV?',
      context: 'Verkoop onderneming en doorschuiving boekwinst',
    },
    {
      text: 'Hoe verwerk ik een afname van de herinvesteringsreserve (HIR) in de aangifte VPB als er in 2021 posten zijn geboekt die de HIR verlagen?',
      context: 'Herinvesteringsreserve in VPB aangifte',
    },
    {
      text: 'Wat zijn de fiscale gevolgen voor de vennootschapsbelasting bij een statutenwijziging die het boekjaar verandert van kalenderjaar naar gebroken boekjaar (1 juli t/m 30 juni)?',
      context: 'Wijziging boekjaar VPB',
    },
  ];

  const features = [
    {
      icon: Sparkles,
      title: 'AI-Gedreven Inzichten',
      description: 'Bespaar tijd en verminder fouten met onze AI Agents',
    },
    {
      icon: ShieldCheck,
      title: 'Veilig & Compliant',
      description: 'Enterprise-grade beveiliging met volledige naleving van wet- en regelgeving',
    },
    {
      icon: Gauge,
      title: 'Efficiënte Automatisering',
      description:
        'Stroomlijn werkprocessen en verminder handmatige taken met slimme automatisering',
    },
  ];

  const securityFeatures = [
    {
      icon: Database,
      title: 'Gegevens worden niet bewaard',
      description:
        'De gegevens die je uploadt in onze AI Agents worden niet opgeslagen, maar alleen gebruikt voor de betreffende chatsessie.',
    },
    {
      icon: Cloud,
      title: 'Veilige cloud omgeving',
      description:
        'Onze systemen draaien in een veilige cloud omgeving (Microsoft Azure), die voldoet aan alle strenge eisen voor databeveiliging.',
    },
    {
      icon: Globe2,
      title: 'Europese servers',
      description:
        'We maken gebruik van een kloon van een LLM van OpenAI, die we hosten in onze eigen Europese cloud omgeving. Hierdoor voldoen we aan alle Europese wetgeving omtrent dataveiligheid en Generative AI.',
    },
    {
      icon: Shield,
      title: 'Geanonimiseerde data',
      description:
        'In de praktijk worden vragen aan de AI Agents gesteld zonder naam en toenaam, waardoor de data geanonimiseerd is.',
    },
  ];

  const handleCopy = () => {
    navigator.clipboard.writeText(prompts[currentPromptIndex].text);
    setCopyTooltip('Gekopieerd!');
    setTimeout(() => setCopyTooltip('Kopieer naar klembord'), 2000);
  };

  const handleNewChatClick = () => {
    handleNewChat();
  };

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined;

    if (isTyping) {
      const currentPrompt = prompts[currentPromptIndex].text;
      if (displayedText.length < currentPrompt.length) {
        timeout = setTimeout(() => {
          setDisplayedText(currentPrompt.slice(0, displayedText.length + 1));
        }, 35);
      } else {
        timeout = setTimeout(() => {
          setIsTyping(false);
        }, 1500);
      }
    } else {
      timeout = setTimeout(() => {
        setDisplayedText('');
        setCurrentPromptIndex(prev => (prev + 1) % prompts.length);
        setIsTyping(true);
      }, 800);
    }

    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [displayedText, isTyping, currentPromptIndex, prompts]);

  return (
    <div className="w-full max-w-[1200px] mx-auto px-2 md:px-4 py-2 md:py-4">
      {/* Hero Section */}
      <div className="grid grid-cols-1 items-center gap-8 md:grid-cols-2 mb-12">
        <div>
          <h1 className="text-4xl font-semibold md:text-5xl mb-2">AI Accountancy Software</h1>
          <h2 className="text-xl md:text-2xl text-brand-400 mb-4">
            Maak kennis met de toekomst van accountancy software.
          </h2>
          <Button
            onClick={handleNewChatClick}
            variant="brand"
            size="xl"
            className="rounded-[12px] text-md uppercase"
          >
            <Sparkles className="mr-2 size-4" />
            Probeer Belasting AI
          </Button>
        </div>
        <div className="text-center">
          <Card className="border rounded-2xl h-[280px]">
            <CardContent className="px-6 h-full flex flex-col">
              <div className="mb-2 flex items-center justify-between">
                <h6 className="text-xl font-medium">Voorbeeldvragen</h6>
                <div className="flex gap-2">
                  {prompts.map((_, index) => (
                    <span
                      key={index}
                      className={`size-2 rounded-full transition-colors ${
                        index === currentPromptIndex ? 'bg-brand-400' : 'bg-border'
                      }`}
                    />
                  ))}
                </div>
              </div>
              <div className="relative flex-1 rounded-lg p-3 transition-colors dark:bg-input/50 text-left">
                <p className="text-sm text-muted-foreground">
                  {displayedText}
                  <span className={`transition-opacity ${isTyping ? 'opacity-100' : 'opacity-0'}`}>
                    |
                  </span>
                </p>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={handleCopy}
                        className="absolute right-2 bottom-2 opacity-70 hover:opacity-100"
                        aria-label={copyTooltip}
                      >
                        {/* 
                          Use the Copy icon from lucide-react for better UX.
                          The icon is decorative, so aria-hidden is set to true.
                        */}
                        <Copy className="size-4" aria-hidden="true" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{copyTooltip}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Divider */}
      <div className="my-12 w-full">
        <Separator className="mx-auto max-w-[800px]" />
      </div>

      {/* Features Section */}
      <div className="grid grid-cols-1 gap-6 mb-12 md:grid-cols-3">
        {features.map((feature, index) => (
          <div key={index} className="h-full">
            <Card className="h-full border rounded-2xl transition-transform duration-200 ease-in-out hover:-translate-y-1">
              <CardContent className="px-6">
                <div className="mb-6 text-brand-400">
                  <feature.icon className="size-12" />
                </div>
                <h6 className="mb-2 text-basem text-2xl font-semibold">{feature.title}</h6>
                <p className="text-md text-brand">{feature.description}</p>
              </CardContent>
            </Card>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="my-12 w-full">
        <Separator className="mx-auto max-w-[800px]" />
      </div>

      {/* Security Section */}
      <div className="mb-12">
        <h2 className="mb-2 text-center text-3xl font-semibold md:text-4xl">
          Jouw data is veilig bij AI4 Accountancy
        </h2>
        <p className="mx-auto mb-4 max-w-[800px] text-center text-muted-foreground">
          We begrijpen dat de veiligheid van jouw data van groot belang is, zeker als het gaat om
          gevoelige informatie zoals belastinggegevens. Daarom nemen we bij AI4 Accountancy
          databeveiliging zeer serieus.
        </p>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {securityFeatures.map((item, index) => (
            <Card key={index} className="border rounded-2xl">
              <CardContent className="px-6 py-2">
                <div className="mb-6 text-brand-400">
                  <item.icon className="size-12" />
                </div>
                <h6 className="mb-2 text-xl font-semibold">{item.title}</h6>
                <p className="text-md text-brand">{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
