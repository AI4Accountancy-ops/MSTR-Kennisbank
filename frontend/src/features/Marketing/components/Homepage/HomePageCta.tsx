import { Link } from 'react-router';
import { Button } from '@/components/ui/button';

export default function HomePageCta() {
  return (
    <>
      {/* CTA Section */}
      <div className="py-12 md:py-16 lg:py-20 bg-muted/30">
        <div className="container mx-auto px-4 md:px-6 2xl:max-w-[1400px]">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-4xl font-semibold tracking-tight text-pretty text-primary sm:text-5xl mb-2">
                Klaar om te beginnen?
              </h2>
              <p className="text-foreground mx-auto pt-2 text-base max-w-[700px] sm:text-lg">
                Sluit je aan bij duizenden gebruikers die al zijn overgestapt.
              </p>
            </div>
            <div className="space-x-4">
              <Button asChild className="bg-brand text-white hover:bg-brand/80">
                <Link to="/signup">Aan de slag</Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to="/blog">Meer informatie</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
      {/* End CTA Section */}
    </>
  );
}
