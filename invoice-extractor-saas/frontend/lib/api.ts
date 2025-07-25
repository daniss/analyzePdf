import Cookies from 'js-cookie'
import { User, UserCreate, Token, Invoice, ApiError } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private getAuthHeader(): Record<string, string> {
    const token = Cookies.get('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid, clear auth
        Cookies.remove('access_token')
        Cookies.remove('user')
        window.location.href = '/auth/signin'
        throw new Error('Authentication required')
      }

      let errorMessage = 'An error occurred'
      try {
        const errorData: ApiError = await response.json()
        errorMessage = errorData.detail || errorMessage
      } catch {
        // If JSON parsing fails, use default message
      }
      
      throw new Error(errorMessage)
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      return response.json()
    }
    
    return response.text() as unknown as T
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
        ...options.headers,
      },
      ...options,
    }

    const response = await fetch(url, config)
    return this.handleResponse<T>(response)
  }

  // Auth methods
  async login(email: string, password: string): Promise<Token> {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const response = await fetch(`${this.baseURL}/api/auth/token`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Login failed')
    }

    const token: Token = await response.json()
    
    // Store token in cookie
    Cookies.set('access_token', token.access_token, { 
      expires: 7, // 7 days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict'
    })

    return token
  }

  async register(userData: UserCreate): Promise<User> {
    return this.request<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    })
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/api/auth/me')
  }

  logout(): void {
    Cookies.remove('access_token')
    Cookies.remove('user')
  }

  // Invoice methods
  async uploadInvoice(file: File): Promise<Invoice> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.baseURL}/api/invoices/upload`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
      },
      body: formData,
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Upload failed')
    }

    return response.json()
  }

  async getInvoices(): Promise<Invoice[]> {
    return this.request<Invoice[]>('/api/invoices/')
  }

  async getInvoice(invoiceId: string): Promise<Invoice> {
    return this.request<Invoice>(`/api/invoices/${invoiceId}`)
  }

  async deleteInvoice(invoiceId: string): Promise<void> {
    return this.request<void>(`/api/invoices/${invoiceId}`, {
      method: 'DELETE',
    })
  }

  // Export methods
  async exportInvoicesCSV(): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/csv`, {
      headers: {
        ...this.getAuthHeader(),
      },
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Export failed')
    }

    return response.blob()
  }

  async exportInvoicesJSON(): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/json`, {
      headers: {
        ...this.getAuthHeader(),
      },
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Export failed')
    }

    return response.blob()
  }

  async exportInvoiceCSV(invoiceId: string): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/${invoiceId}/csv`, {
      headers: {
        ...this.getAuthHeader(),
      },
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Export failed')
    }

    return response.blob()
  }

  async exportInvoiceJSON(invoiceId: string): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/${invoiceId}/json`, {
      headers: {
        ...this.getAuthHeader(),
      },
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Export failed')
    }

    return response.blob()
  }

  // Utility method to check if user is authenticated
  isAuthenticated(): boolean {
    return !!Cookies.get('access_token')
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)