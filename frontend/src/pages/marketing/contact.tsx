import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MessageCircle, Phone, MapPin } from 'lucide-react';
import { Link } from 'react-router';
import { useEffect, useRef } from 'react';

/**
 * ContactPage
 * Renders the contact form, contact details, and an inline Calendly booking widget.
 * The Calendly script is loaded once and the inline widget is initialized safely
 * when the script is available and the container ref is mounted.
 */

declare global {
  interface Window {
    Calendly?: {
      initInlineWidget: (config: {
        url: string;
        parentElement: HTMLElement;
        prefill?: Record<string, string>;
        utm?: Record<string, string>;
      }) => void;
    };
  }
}

export default function ContactPage() {
  // Container for Calendly to mount the inline widget into
  const calendlyContainerRef = useRef<HTMLDivElement | null>(null);

  // Load Calendly widget script once and initialize the inline widget when ready
  useEffect(() => {
    const scriptId = 'calendly-widget-js';
    const calendlyUrl =
      'https://calendly.com/d/cv6r-6xh-dtp/belasting-ai-gratis-toegang-opstart?hide_gdpr_banner=1&primary_color=ffa500';

    const initializeCalendly = () => {
      const container = calendlyContainerRef.current;
      if (container && window.Calendly) {
        // Ensure the container is empty before initializing to prevent duplicate rendering
        container.innerHTML = '';
        window.Calendly.initInlineWidget({
          url: calendlyUrl,
          parentElement: container,
        });
      }
    };

    const existingScript = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (existingScript) {
      // If the script has already loaded, initialize immediately; otherwise wait for load
      if (existingScript.getAttribute('data-loaded') === 'true') {
        initializeCalendly();
      } else {
        existingScript.addEventListener('load', initializeCalendly, { once: true });
      }
      return () => {
        if (calendlyContainerRef.current) {
          calendlyContainerRef.current.innerHTML = '';
        }
      };
    }

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = 'https://assets.calendly.com/assets/external/widget.js';
    script.async = true;
    script.onload = () => {
      script.setAttribute('data-loaded', 'true');
      initializeCalendly();
    };
    document.body.appendChild(script);

    // Cleanup: clear widget contents on unmount
    return () => {
      if (calendlyContainerRef.current) {
        calendlyContainerRef.current.innerHTML = '';
      }
    };
  }, []);
  return (
    <>
      <section className="w-full bg-background container mx-auto px-4 md:px-6 py-8 md:py-16 lg:py-20">
        <div className="container px-4 md:px-6 mx-auto">
          {/* Header */}
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-16">
            <h1 className="text-primary leading-tighter max-w-4xl text-4xl font-semibold tracking-tight text-balance lg:leading-[1.1] lg:font-semibold xl:text-5xl xl:tracking-tighter">
              Klaar om te starten?
            </h1>
            <p className="text-foreground max-w-4xl text-base text-balance sm:text-lg">
              We maken het je graag makkelijk. Boek direct een moment in onze agenda om kennis te
              maken en toegang te krijgen.
            </p>
          </div>

          {/* Main Content */}
          <div className="max-w-4xl mx-auto space-y-12">
            {/* Contact Form */}
            <div className="space-y-6">
              <form className="space-y-6">
                {/* Name Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">Voornaam</Label>
                    <Input id="firstName" placeholder="Voornaam" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Achternaam</Label>
                    <Input id="lastName" placeholder="Achternaam" required />
                  </div>
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <Label htmlFor="email">E-mail</Label>
                  <Input id="email" type="email" placeholder="jij@bedrijf.nl" required />
                </div>

                {/* Phone Number */}
                <div className="space-y-2">
                  <Label htmlFor="phone">Telefoonnummer</Label>
                  <div className="flex gap-2">
                    <Select>
                      <SelectTrigger className="w-20">
                        <SelectValue placeholder="NL" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="NL">NL</SelectItem>
                        <SelectItem value="BE">BE</SelectItem>
                        <SelectItem value="DE">DE</SelectItem>
                        <SelectItem value="FR">FR</SelectItem>
                        <SelectItem value="US">US</SelectItem>
                        <SelectItem value="UK">UK</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input id="phone" type="tel" placeholder="+31 6 12345678" className="flex-1" />
                  </div>
                </div>

                {/* Message */}
                <div className="space-y-2">
                  <Label htmlFor="message">Bericht</Label>
                  <Textarea
                    id="message"
                    placeholder="Laat een bericht achter..."
                    className="min-h-[120px]"
                    required
                  />
                </div>

                {/* Submit Button */}
                <Button type="submit" className="w-full" size="lg">
                  Verstuur bericht
                </Button>
              </form>
            </div>
          </div>
        </div>
      </section>
      <section className="w-full bg-background container mx-auto px-4 md:px-6 py-8 md:py-16 lg:py-20">
        <div className="container px-4 md:px-6 mx-auto">
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-8">
            <h2 className="text-primary leading-tighter max-w-4xl text-3xl font-semibold tracking-tight text-balance lg:leading-[1.1] lg:font-semibold xl:text-4xl xl:tracking-tighter">
              Plan een gesprek
            </h2>
            <p className="text-foreground max-w-3xl text-base text-balance sm:text-lg">
              Kies een moment dat voor u past. Bevestig direct via Calendly.
            </p>
          </div>
          <div className="flex justify-center">
            <div
              ref={calendlyContainerRef}
              className="w-full"
              style={{ minWidth: 320, height: 700 }}
            />
          </div>
        </div>
      </section>
      <section className="w-full bg-muted/30 mx-auto">
        {/* Contact Information Cards */}
        <div className="container mx-auto justify-center px-4 md:px-6 py-8 md:py-16 lg:py-20 max-w-7xl grid gap-6 md:grid-cols-3 pt-10 p-10 rounded-lg">
          {/* Chat with us */}
          <div>
            <div className="flex flex-col gap-4 items-center text-center">
              <div className="flex items-center gap-3">
                <MessageCircle className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Chat met ons</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Praat met onze vriendelijke team via live chat.
              </p>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Link
                    to="mailto:pascale@ai4accountancy.nl"
                    className="text-primary hover:underline font-medium"
                  >
                    pascale@ai4accountancy.nl
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Call us */}
          <div>
            <div className="flex flex-col gap-4 items-center text-center">
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Bel ons</h3>
              </div>
              <p className="text-sm text-muted-foreground">Bel ons rechtstreeks.</p>
              <div className="flex items-center gap-2 text-sm">
                <Link to="tel:+31653865903" className="text-primary hover:underline font-medium">
                  T. +31653865903
                </Link>
              </div>
            </div>
          </div>

          {/* Visit us */}
          <div>
            <div className="flex flex-col gap-4 items-center text-center">
              <div className="flex items-center gap-3">
                <MapPin className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Bezoek ons</h3>
              </div>
              <p className="text-sm text-muted-foreground">Bezoek ons op een van onze locaties.</p>
              <div className="flex flex-col gap-3 text-sm">
                <div className="flex items-start gap-2">
                  <Link
                    to="https://maps.google.com/?q=Oranjesingel+8,+6511+NT+Nijmegen"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    p/a Oranjesingel 8, 6511 NT Nijmegen
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
