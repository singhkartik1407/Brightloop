import { APP_CONFIG } from "./mock.config";

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg: string;
  type?: string;
}

export class ApiError extends Error {
  public status: number;
  public details: ApiErrorDetail[] | null;
  public rawData: unknown;

  constructor(status: number, message: string, details: ApiErrorDetail[] | null = null, rawData: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
    this.rawData = rawData;
  }
}

const TOKEN_KEY = "brightloop_access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const baseUrl = APP_CONFIG.API_BASE_URL.replace(/\/+\$/, "");
  const url = `${baseUrl}${cleanEndpoint}`;

  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  headers.set("Accept", "application/json");

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  let response: Response;
  try {
    response = await fetch(url, config);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Network failure. Backend may be offline.";
    throw new ApiError(0, `Cannot connect to server: ${message}`);
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return {} as T;
  }

  let responseData: unknown = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      responseData = await response.json();
    } catch {
      responseData = null;
    }
  } else {
    responseData = await response.text();
  }

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    let details: ApiErrorDetail[] | null = null;

    if (responseData && typeof responseData === "object") {
      const dataObj = responseData as Record<string, unknown>;

      if (Array.isArray(dataObj.detail)) {
        details = dataObj.detail as ApiErrorDetail[];
        errorMessage = details
          .map((d) => (d.loc && d.loc.length > 0 ? `${d.loc.slice(1).join(".")}: ${d.msg}` : d.msg))
          .join(" | ");
      } else if (typeof dataObj.detail === "string") {
        errorMessage = dataObj.detail;
      } else if (typeof dataObj.message === "string") {
        errorMessage = dataObj.message;
      }
    }

    if (response.status === 401) {
      setAccessToken(null);
    }

    throw new ApiError(response.status, errorMessage, details, responseData);
  }

  return responseData as T;
}
