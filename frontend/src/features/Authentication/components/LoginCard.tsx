import { useMsal } from '@azure/msal-react';

import { Card, CardContent } from '~/components/ui/card';
import { Button } from '~/components/ui/button';
import { useMediaQuery } from '~/hooks/useMediaQuery';
import { loginRequest } from '@features/Authentication/config';
import logo from '../../../assets/images/ai4accountancy_logo.png';
import microsoftLogo from '../../../assets/icons/microsoft.png';
import googleLogo from '../../../assets/icons/google.png';

export default function LoginCard() {
  const { instance } = useMsal();
  const isMobile = useMediaQuery('(max-width: 640px)');

  const handleMicrosoftLogin = async () => {
    try {
      console.log('Starting login with Microsoft identity provider');

      await instance.loginRedirect({
        ...loginRequest,
        redirectUri: `${window.location.origin}${import.meta.env.VITE_REDIRECT_PATH}`,
      });
    } catch (error) {
      console.error('Microsoft login error:', error);

      if (error instanceof Error) {
        console.error('Error details:', {
          name: error.name,
          message: error.message,
          stack: error.stack,
        });
      }
    }
  };

  const handleGoogleLogin = () => {
    try {
      console.log('Redirecting to Google login via B2C');

      // Use the standard Azure B2C format with p parameter instead of policy path
      const b2cTenant = import.meta.env.VITE_B2C_TENANT;
      const b2cDomain = import.meta.env.VITE_B2C_DOMAIN;
      const clientId = import.meta.env.VITE_CLIENT_ID;
      const policyName = import.meta.env.VITE_B2C_POLICY_NAME;
      const redirectUri = encodeURIComponent(`${window.location.origin}/home`);
      const nonce = Math.random().toString(36).substring(2, 15);
      const state = Math.random().toString(36).substring(2, 15);

      // Using the standard Azure B2C format with p parameter
      const authorizationUrl =
        `https://${b2cTenant}/${b2cDomain}/oauth2/v2.0/authorize` +
        `?p=${policyName}` +
        `&client_id=${clientId}` +
        `&response_type=id_token` +
        `&redirect_uri=${redirectUri}` +
        `&scope=openid%20profile%20email` +
        `&response_mode=fragment` +
        `&prompt=login` +
        `&nonce=${nonce}` +
        `&state=${state}` +
        `&identity_provider=google`;

      console.log('Google B2C Authorization URL:', authorizationUrl);

      // Direct navigation - this is the simplest and most reliable approach
      window.location.href = authorizationUrl;
    } catch (error) {
      console.error('Google login redirect error:', error);
    }
  };

  return (
    <Card
      className={`bg-transparent relative flex flex-col self-center border shadow-[hsla(220,30%,5%,0.05)_0px_5px_15px_0px,hsla(220,25%,10%,0.05)_0px_15px_35px_-5px] dark:shadow-[hsla(220,30%,5%,0.5)_0px_5px_15px_0px,hsla(220,25%,10%,0.08)_0px_15px_35px_-5px] ${isMobile ? 'w-auto' : 'w-full'}`}
    >
      <div className="absolute inset-0 -z-10 hidden rounded-lg bg-card-dark dark:block" />
      <CardContent className={`flex flex-col gap-4 ${isMobile ? 'p-6' : 'p-8'}`}>
        <div className={`flex items-center gap-4 ${isMobile ? 'mb-2' : 'mb-4'} justify-center`}>
          <img
            src={logo}
            alt="Company Logo"
            className={`h-auto max-w-[300px] ${isMobile ? 'w-4/5' : 'w-full'}`}
          />
        </div>
        <div className="flex w-full flex-col gap-4">
          <div className={`flex flex-col ${isMobile ? 'gap-6' : 'gap-4'}`}>
            <Button
              type="button"
              variant="muigray"
              onClick={handleMicrosoftLogin}
              size="lg"
              // className={`w-full text-transform-none ${isMobile ? 'py-3 text-base' : 'py-2 text-sm'}`}
            >
              <img src={microsoftLogo} alt="Microsoft" className="mr-2 h-4 w-4" />
              Inloggen met Microsoft
            </Button>

            <Button
              type="button"
              variant="muigray"
              onClick={handleGoogleLogin}
              size="lg"
              // className={`w-full text-transform-none ${isMobile ? 'py-3 text-base' : 'py-2 text-sm'}`}
            >
              <img src={googleLogo} alt="Google" className="mr-2 h-4 w-4" />
              Inloggen met Google
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
