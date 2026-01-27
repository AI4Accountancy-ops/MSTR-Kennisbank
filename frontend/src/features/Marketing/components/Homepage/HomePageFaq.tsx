import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

const faqs = [
  {
    question: 'Wat is Belasting AI precies?',
    answer:
      'Belasting AI is een slimme chatbot die je direct helpt met fiscale vragen. Het model heeft toegang tot betrouwbare bronnen zoals Belastingdienst.nl en wetten.overheid.nl en kan daarnaast eenvoudige taken uitvoeren zoals berekeningen, samenvattingen en websearch.',
  },
  {
    question: 'Hoe betrouwbaar zijn de antwoorden?',
    answer:
      'Alle antwoorden worden onderbouwd met actuele bronnen. Je krijgt dus niet alleen een advies, maar ook een link naar de officiële wet- of belastingpagina waar de informatie vandaan komt.',
  },
  {
    question: 'Is mijn data veilig?',
    answer:
      'Ja. Alle data wordt verwerkt binnen een beveiligde omgeving in Azure. Voor Enterprise-klanten bieden we zelfs een dedicated omgeving met eigen resource group en SLA, zodat data volledig gescheiden blijft.',
  },
  {
    question: 'Kan ik Belasting AI eerst uitproberen?',
    answer:
      'Ja, elk pakket begint met een 7-dagen gratis proefperiode. Je kunt tijdens de proef alle functies gebruiken zonder verplichtingen.',
  },
  {
    question: 'Hoe werkt de prijsstructuur?',
    answer:
      'Je kiest een pakket (Instap, Groei, Pro of Enterprise) dat past bij jouw kantoor. Elk pakket bevat een vast aantal vragen per maand. Extra vragen boven je bundel worden per stuk afgerekend.',
  },
];

export default function HomePageFaq() {
  return (
    <div className="lg:max-w-7xl container mx-auto px-4 md:px-6 py-24 lg:py-32">
      <div className="grid md:grid-cols-5 gap-10">
        <div className="md:col-span-2">
          <div className="max-w-xs">
            <h2 className="text-4xl font-semibold tracking-tight text-pretty text-primary sm:text-5xl mb-2">
              Veelgestelde
              <br />
              vragen
            </h2>
            <p className="text-foreground mx-auto pt-2 text-base max-w-[700px] sm:text-lg">
              Antwoorden op de meest gestelde vragen.
            </p>
          </div>
        </div>

        <div className="md:col-span-3">
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, index) => (
              <AccordionItem value={`item-${index}`} key={faq.question}>
                <AccordionTrigger className="text-lg font-semibold text-left">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground text-base">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </div>
  );
}
