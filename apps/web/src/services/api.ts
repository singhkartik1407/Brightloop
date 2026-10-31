const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1"

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

interface ApiError {
  message: string
  status: number
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers)

  headers.set("Content-Type", "application/json")

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`)
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))

    const apiError: ApiError = {
      message:
        error.detail ||
        error.message ||
        "Something went wrong. Please try again.",
      status: response.status,
    }

    throw apiError
  }

  return response.json() as Promise<T>
}