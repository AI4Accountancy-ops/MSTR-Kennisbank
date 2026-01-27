import ExactLogo from '@/assets/icons/exact.png';
import FiscaalLogo from '@/assets/icons/fiscaal.png';
import OamkbLogo from '@/assets/icons/oamkb.png';
import YukiLogo from '@/assets/icons/yuki.png';
import Ai4Logo from '@/assets/images/ai4accountancy_logo.png';

export default function HomePageLogoCloud() {
  return (
    <section className="w-full py-12 md:py-16 lg:py-20 bg-muted/30">
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-8">
          <div className="text-center space-y-2">
            <p className="text-sm font-medium text-primary uppercase tracking-wider">
              Vertrouwd door marktleiders
            </p>
          </div>

          <div className="flex flex-wrap flex-row text-primary/80 justify-center gap-8 lg:gap-24 items-center justify-items-center w-full max-w-6xl">
            <div className="flex items-center justify-center">
              <img
                src={ExactLogo}
                alt="Exact"
                className="h-10 w-auto object-contain filter grayscale opacity-80"
              />
            </div>

            <div className="flex items-center justify-center">
              <img
                src={FiscaalLogo}
                alt="Fiscaal Gemak"
                className="h-10 w-auto object-contain filter grayscale opacity-80"
              />
            </div>

            <div className="flex items-center justify-center">
              <img
                src={OamkbLogo}
                alt="OAMKB"
                className="h-10 w-auto object-contain filter grayscale opacity-80"
              />
            </div>

            <div className="flex items-center justify-center">
              <img
                src={YukiLogo}
                alt="Yuki"
                className="h-15 w-auto object-contain filter grayscale opacity-80"
              />
            </div>

            <div className="flex items-center justify-center">
              <img
                src={Ai4Logo}
                alt="AI4Accountancy"
                className="h-15 w-auto object-contain filter grayscale opacity-100"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
