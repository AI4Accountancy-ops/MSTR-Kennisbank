import { Sparkles, Zap, Mail, BarChart3, type LucideIcon } from 'lucide-react';

interface Item {
  icon: LucideIcon;
  title: string;
  description: string;
}

const items: Item[] = [
  {
    icon: Sparkles,
    title: 'AI4 Accountancy',
    description:
      'Een slimme AI-assistent die jou helpt als accountant, administratiekantoor of belastingadviseur. Met geavanceerde AI-technologie en handige functies bespaar je tijd, automatiseer je processen en verbeter je de communicatie met klanten.',
  },
  {
    icon: Zap,
    title: 'Tijd besparen',
    description:
      'Automatiseer repetitieve taken en ontvang snel en accuraat antwoord met bronverwijzingen.',
  },
  {
    icon: Mail,
    title: 'Betere klantcommunicatie',
    description: 'Laat professionele e-mails, samenvattingen en rapportages voor je opstellen.',
  },
  {
    icon: BarChart3,
    title: 'Efficiënte analyses',
    description: 'Verkrijg heldere en betrouwbare inzichten in diverse belastingvraagstukken.',
  },
];

export default function LoginContent() {
  return (
    <div className="flex max-w-[450px] flex-col gap-8 self-center">
      {items.map((item, index) => {
        const Icon = item.icon;
        return (
          <div key={index} className="flex items-start gap-2">
            <Icon className="size-6 shrink-0 text-brand-400 mt-1" />
            <div>
              <h2 className="mb-2 text-xl font-medium text-brand-400">{item.title}</h2>
              <p className="text-sm leading-relaxed text-foreground">{item.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
