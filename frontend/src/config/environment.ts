// Simple environment configuration
// This keeps the API base URL configuration in one place without introducing architectural changes

// Define the environment type
type EnvironmentType = 'development' | 'dev' | 'stage' | 'production';

// Get current environment with fallback to development
const ENV = (import.meta.env.VITE_ENVIRONMENT || 'development') as EnvironmentType;

// Determine the API base URL based on the environment
let apiBaseUrl: string;

switch (ENV) {
  case 'dev':
    apiBaseUrl =
      import.meta.env.VITE_DEV_API_URL || 'https://api-ai4accountancy-dev.azurewebsites.net';
    break;
  case 'stage':
    apiBaseUrl =
      import.meta.env.VITE_STAGE_API_URL || 'https://api-ai4accountancy-stage.azurewebsites.net';
    break;
  case 'production':
    apiBaseUrl =
      import.meta.env.VITE_PROD_API_URL || 'https://api-ai4accountancy-prod.azurewebsites.net';
    break;
  default: // development
    apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
}

// Direct override via VITE_API_URL takes precedence regardless of environment
const API_BASE_URL = import.meta.env.VITE_API_URL || apiBaseUrl;

export { API_BASE_URL };
