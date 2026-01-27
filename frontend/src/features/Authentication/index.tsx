import { useMediaQuery } from '~/hooks/useMediaQuery';
import LoginCard from './components/LoginCard';
import LoginContent from './components/LoginContent';

export default function Authentication() {
  const isMobile = useMediaQuery('(max-width: 768px)');

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-col items-center justify-center gap-8 p-4 md:min-h-[500px] md:flex-row md:gap-12 sm:p-8">
      {/* Only show LoginContent on desktop/tablet */}
      {!isMobile && (
        <div className="flex flex-1 basis-1/2 h-full w-full items-center justify-center">
          <LoginContent />
        </div>
      )}

      <div
        className={`flex h-full w-full items-center justify-center ${isMobile ? 'flex-1 basis-full' : 'flex-1 basis-1/2'}`}
      >
        <LoginCard />
      </div>
    </div>
  );
}
