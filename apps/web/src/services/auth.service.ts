import { apiRequest, setAccessToken } from "./api";
import { USE_MOCK } from "./mock.config";
import type { User } from "@/types/domain.types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken?: string;
  access_token?: string;
  tokenType?: string;
  token_type?: string;
  user?: User;
}

const MOCK_USER: User = {
  id: "usr_mock_admin_123",
  email: "admin@brightloop.com",
  role: "ADMIN",
  isActive: true,
  createdAt: new Date().toISOString(),
};

export async function loginUser(payload: LoginPayload): Promise<User> {
  if (USE_MOCK) {
    setAccessToken("mock_jwt_token_sample");
    return { ...MOCK_USER, email: payload.email };
  }

  const res = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  const token = res.accessToken || res.access_token;
  if (!token) {
    throw new Error("Authentication response did not return an access token.");
  }

  setAccessToken(token);

  try {
    return await getCurrentUser();
  } catch {
    return {
      id: "usr_authenticated",
      email: payload.email,
      role: "ADMIN",
      isActive: true,
      createdAt: new Date().toISOString(),
    };
  }
}

export async function getCurrentUser(): Promise<User> {
  if (USE_MOCK) {
    return MOCK_USER;
  }
  return apiRequest<User>("/auth/me");
}

export function logoutUser(): void {
  setAccessToken(null);
}
