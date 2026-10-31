import {
    createContext,
    useContext,
    useState,
    type ReactNode,
  } from "react"
  
  import type { User, LoginRequest, RegisterRequest } from "@/types/auth.types"
  
  import * as authService from "@/services/auth.service"
  
  interface AuthContextType {
    user: User | null
    loading: boolean
    login: (data: LoginRequest) => Promise<void>
    register: (data: RegisterRequest) => Promise<void>
    logout: () => void
  }
  
  const AuthContext = createContext<AuthContextType | undefined>(undefined)
  
  export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(false)
  
    const login = async (data: LoginRequest) => {
      setLoading(true)
      try {
        const response = await authService.login(data)
        setUser(response.user)
      } finally {
        setLoading(false)
      }
    }
  
    const register = async (data: RegisterRequest) => {
      setLoading(true)
      try {
        await authService.register(data)
      } finally {
        setLoading(false)
      }
    }
  
    const logout = () => {
      authService.logout()
      setUser(null)
    }
  
    return (
      <AuthContext.Provider
        value={{ user, loading, login, register, logout }}
      >
        {children}
      </AuthContext.Provider>
    )
  }
  
  export function useAuth() {
    const context = useContext(AuthContext)
  
    if (!context) {
      throw new Error("useAuth must be used within AuthProvider")
    }
  
    return context
  }