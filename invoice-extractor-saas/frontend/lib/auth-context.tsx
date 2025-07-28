'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'
import { apiClient } from './api'
import { User } from './types'

interface AuthContextType {
  user: User | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, companyName?: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  // Check if user is authenticated on app load
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        if (apiClient.isAuthenticated()) {
          const currentUser = await apiClient.getCurrentUser()
          setUser(currentUser)
          // Store user in cookie for quick access
          Cookies.set('user', JSON.stringify(currentUser), { expires: 7 })
        }
      } catch {
        // Token might be invalid, clear it
        apiClient.logout()
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [])

  const login = async (email: string, password: string) => {
    try {
      setError(null)
      setLoading(true)
      
      // Login and get token
      await apiClient.login(email, password)
      
      // Get user data
      const currentUser = await apiClient.getCurrentUser()
      setUser(currentUser)
      
      // Store user in cookie
      Cookies.set('user', JSON.stringify(currentUser), { expires: 7 })
      
      // Redirect to dashboard
      router.push('/dashboard')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Échec de la connexion'
      setError(errorMessage)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const register = async (email: string, password: string, companyName?: string) => {
    try {
      setError(null)
      setLoading(true)
      
      // Register user
      await apiClient.register({
        email,
        password,
        company_name: companyName
      })
      
      // Auto-login after registration
      await apiClient.login(email, password)
      
      // Get updated user data
      const currentUser = await apiClient.getCurrentUser()
      setUser(currentUser)
      
      // Store user in cookie
      Cookies.set('user', JSON.stringify(currentUser), { expires: 7 })
      
      // Redirect to dashboard
      router.push('/dashboard')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Échec de l\'inscription'
      setError(errorMessage)
      throw error
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    apiClient.logout()
    setUser(null)
    router.push('/auth/signin')
  }

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Higher-order component for protecting routes
export function withAuth<T extends object>(Component: React.ComponentType<T>) {
  return function AuthenticatedComponent(props: T) {
    const { isAuthenticated, loading } = useAuth()
    const router = useRouter()

    useEffect(() => {
      if (!loading && !isAuthenticated) {
        router.push('/auth/signin')
      }
    }, [isAuthenticated, loading, router])

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
        </div>
      )
    }

    if (!isAuthenticated) {
      return null
    }

    return <Component {...props} />
  }
}