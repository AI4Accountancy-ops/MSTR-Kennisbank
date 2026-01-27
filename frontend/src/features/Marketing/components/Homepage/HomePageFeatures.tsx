import { BookOpenCheck, ShieldCheck, Sparkles } from 'lucide-react';

export default function HomePageFeatures() {
  return (
    <section className="w-full py-12 md:py-16 lg:py-20">
      <div className="container mx-auto px-4 md:px-6">
        <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden>
          <defs>
            <linearGradient id="brandGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#e9e336" />
              <stop offset="100%" stopColor="#c63128" />
            </linearGradient>
          </defs>
        </svg>
        <style>{`.gradient-stroke path, .gradient-stroke circle, .gradient-stroke line, .gradient-stroke polyline, .gradient-stroke polygon { stroke: url(#brandGradient) !important; fill: none !important; }`}</style>
        <div className="">
          <h2 className="text-base/7 font-semibold text-muted-foreground">
            Waarom kiezen voor AI4Accountancy?
          </h2>
          <p className="mt-2 max-w-lg text-4xl font-semibold tracking-tight text-pretty text-primary sm:text-5xl">
            Features die je helpen om vooruit te blijven
          </p>
        </div>
        <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-16 lg:grid-cols-6 lg:grid-rows-1">
          <div className="relative lg:col-span-2">
            <div className="relative flex h-full flex-col overflow-hidden rounded-[calc(var(--radius-lg)+1px)] lg:rounded-bl-[calc(2rem+1px)]">
              <div className="flex h-80 items-center justify-center bg-accent">
                <BookOpenCheck aria-label="Actuele kennis" className="gradient-stroke h-40 w-40" />
              </div>

              <div className="p-10 pt-8">
                <p className="mt-2 text-lg font-medium tracking-tight text-primary">
                  Actuele kennis
                </p>
                <p className="mt-2 max-w-lg text-sm/6 text-foreground">
                  Direct antwoorden met onderliggende bronnen van betrouwbare bronnen.
                </p>
              </div>
            </div>
            <div className="pointer-events-none absolute inset-0 rounded-lg shadow-sm outline outline-primary/5 lg:rounded-bl-4xl" />
          </div>
          <div className="relative lg:col-span-2">
            <div className="relative flex h-full flex-col overflow-hidden rounded-[calc(var(--radius-lg)+1px)]">
              <div className="flex h-80 items-center justify-center bg-accent">
                <Sparkles
                  aria-label="Tijdbesparende assistent"
                  className="gradient-stroke h-40 w-40"
                />
              </div>

              <div className="p-10 pt-8">
                <p className="mt-2 text-lg font-medium tracking-tight text-primary">
                  Tijdbesparende assistent
                </p>
                <p className="mt-2 max-w-lg text-sm/6 text-foreground">
                  Ontvang snel relevante en praktisch advies en voorkom herhalend werk.
                </p>
              </div>
            </div>
            <div className="pointer-events-none absolute inset-0 rounded-lg shadow-sm outline outline-primary/5" />
          </div>
          <div className="relative lg:col-span-2">
            <div className="relative flex h-full flex-col overflow-hidden rounded-[calc(var(--radius-lg)+1px)] max-lg:rounded-b-[calc(2rem+1px)] lg:rounded-br-[calc(2rem+1px)]">
              <div className="flex h-80 items-center justify-center bg-accent">
                <ShieldCheck
                  aria-label="Veilig & Nederlands"
                  className="gradient-stroke h-40 w-40"
                />
              </div>

              <div className="p-10 pt-8">
                <p className="mt-2 text-lg font-medium tracking-tight text-primary">
                  Veilig & Nederlands
                </p>
                <p className="mt-2 max-w-lg text-sm/6 text-foreground">
                  Data blijft in jouw eigen omgeving en voldoet aan Nederlandse wet- en regelgeving.
                </p>
              </div>
            </div>
            <div className="pointer-events-none absolute inset-0 rounded-lg shadow-sm outline outline-primary/5 max-lg:rounded-b-4xl lg:rounded-br-4xl" />
          </div>
        </div>
      </div>
    </section>
  );
}
