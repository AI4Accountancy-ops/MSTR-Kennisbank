import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
  isAxiosError,
} from 'axios';
import { API_BASE_URL } from '~/config/environment';

export interface ApiError {
  readonly status?: number;
  readonly message: string;
  readonly details?: unknown;
}

export function toApiError(error: unknown): ApiError {
  const networkMessage = 'Netwerkfout. Controleer uw verbinding en probeer het opnieuw.';
  const timeoutMessage = 'Time-out bij het verbinden met de server.';

  if (isAxiosError(error)) {
    const err: AxiosError<unknown> = error as AxiosError<unknown>;
    // Timeout / network
    if (err.code === 'ECONNABORTED') {
      return { status: err.response?.status, message: timeoutMessage, details: err.toJSON() };
    }
    if (!err.response) {
      return { message: networkMessage };
    }
    const status = err.response.status;
    const message =
      typeof err.response.data === 'object' && err.response.data !== null
        ? 'Er is een fout opgetreden bij het verwerken van uw verzoek.'
        : String(err.message ?? 'Onbekende fout');
    return { status, message, details: err.response.data };
  }

  return { message: 'Onbekende fout opgetreden.' };
}

const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
  withCredentials: false,
});

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('b2c_token');
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: unknown) => Promise.reject(toApiError(error)),
);

export async function getJson<TResponse>(url: string): Promise<TResponse> {
  try {
    const res = await http.get<TResponse>(url);
    return res.data;
  } catch (err) {
    throw toApiError(err);
  }
}

export async function postJson<TRequest, TResponse>(
  url: string,
  data: TRequest,
): Promise<TResponse> {
  try {
    const res = await http.post<TResponse>(url, data);
    return res.data;
  } catch (err) {
    throw toApiError(err);
  }
}

export async function putJson<TRequest, TResponse>(
  url: string,
  data: TRequest,
): Promise<TResponse> {
  try {
    const res = await http.put<TResponse>(url, data);
    return res.data;
  } catch (err) {
    throw toApiError(err);
  }
}

export async function deleteJson<TResponse>(url: string): Promise<TResponse> {
  try {
    const res = await http.delete<TResponse>(url);
    return res.data;
  } catch (err) {
    throw toApiError(err);
  }
}

export async function deleteWithBodyJson<TRequest, TResponse>(
  url: string,
  data: TRequest,
): Promise<TResponse> {
  try {
    const res = await http.delete<TResponse>(url, { data });
    return res.data;
  } catch (err) {
    throw toApiError(err);
  }
}

export default http;
