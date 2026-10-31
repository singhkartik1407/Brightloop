export type UserRole = "admin" | "staff" | "customer"

export interface User {
  id: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface Customer {
  id: string
  display_name: string
  company_name: string | null
  billing_email: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  fullName: string
  email: string
  password: string
  businessName?: string
  phone?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RegisterResponse {
  user: User
  customer: Customer
}