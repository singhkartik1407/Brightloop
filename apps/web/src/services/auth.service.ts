import { setAccessToken } from "./api"
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
} from "@/types/auth.types"

// Toggle this to false when connecting to Developer A's real backend later
const USE_MOCK = true

const MOCK_USER: User = {
  id: "usr_mock_12345",
  email: "demo@brightloop.com",
  role: "admin",
  is_active: true,
  created_at: new Date().toISOString(),
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  if (USE_MOCK) {
    const mockUser: User = { ...MOCK_USER, email: data.email }
    const mockRes: LoginResponse = {
      access_token: "mock_jwt_token_sample_xyz",
      token_type: "bearer",
      expires_in: 3600,
      user: mockUser,
    }
    setAccessToken(mockRes.access_token)
    return mockRes
  }

  // Real backend call fallback
  const { apiRequest } = await import("./api")
  const response = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  })
  setAccessToken(response.access_token)
  return response
}

export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  if (USE_MOCK) {
    const mockUser: User = { ...MOCK_USER, email: data.email }
    const mockRes: RegisterResponse = {
      user: mockUser,
      customer: {
        id: "cust_mock_12345",
        display_name: data.fullName,
        company_name: data.businessName || null,
        billing_email: data.email,
      },
    }
    setAccessToken("mock_jwt_token_sample_xyz")
    return mockRes
  }

  const { apiRequest } = await import("./api")
  return apiRequest<RegisterResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getCurrentUser(): Promise<User> {
  if (USE_MOCK) {
    return MOCK_USER
  }
  const { apiRequest } = await import("./api")
  return apiRequest<User>("/auth/me")
}

export function logout() {
  setAccessToken(null)
}