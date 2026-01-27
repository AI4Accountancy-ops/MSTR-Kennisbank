import HomePageCta from '@/features/Marketing/components/Homepage/HomePageCta';
import HomePagePricing from '@/features/Marketing/components/Homepage/HomePagePricing';
import HomePageFaq from '@/features/Marketing/components/Homepage/HomePageFaq';
import HomePageFeatures from '@/features/Marketing/components/Homepage/HomePageFeatures';
import HomePageHero from '@/features/Marketing/components/Homepage/HomePageHero';
import HomePageLogoCloud from '@/features/Marketing/components/Homepage/HomePageLogoCloud';

export default function Home() {
  return (
    <>
      <HomePageHero />
      <HomePageLogoCloud />
      <HomePageFeatures />
      <HomePagePricing />
      <HomePageFaq />
      <HomePageCta />
    </>
  );
}
