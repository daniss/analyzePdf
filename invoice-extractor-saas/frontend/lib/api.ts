import Cookies from 'js-cookie'
import { User, UserCreate, Token, Invoice, ApiError } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private getAuthHeader(): Record<string, string> {
    const token = Cookies.get('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // Public method to get auth headers for external use
  public getAuthHeaders(): Record<string, string> {
    return this.getAuthHeader()
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      if (response.status === 401) {
        // Try to refresh token before giving up
        try {
          await this.refreshToken()
          // Don't redirect, let the calling code retry with new token
          throw new Error('TOKEN_REFRESHED')
        } catch (refreshError) {
          // Refresh failed, clear auth and redirect
          Cookies.remove('access_token')
          Cookies.remove('user')
          window.location.href = '/auth/signin'
          throw new Error('Authentification requise')
        }
      }

      let errorMessage = 'An error occurred'
      try {
        const errorData: any = await response.json()
        console.log('🔍 Error response data:', JSON.stringify(errorData, null, 2))
        // Handle multiple formats: {detail: ...}, {message: ...}, {error: {message: ...}}
        errorMessage = errorData.detail || errorData.message || errorData.error?.message || errorMessage
        console.log('📝 Extracted error message:', errorMessage)
      } catch (parseError) {
        console.log('❌ Failed to parse error JSON:', parseError)
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

  private async refreshToken(): Promise<void> {
    const currentToken = Cookies.get('access_token')
    if (!currentToken) {
      throw new Error('No token to refresh')
    }

    // In a real app, you'd have a refresh token endpoint
    // For now, we'll extend the token expiry by re-authenticating
    // This is a simplified approach - ideally use refresh tokens
    const response = await fetch(`${this.baseURL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      }
    })

    if (!response.ok) {
      throw new Error('Token refresh failed')
    }

    const data: Token = await response.json()
    Cookies.set('access_token', data.access_token, { expires: 7 })
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount = 0
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

    try {
      const response = await fetch(url, config)
      return await this.handleResponse<T>(response)
    } catch (error) {
      // If token was refreshed, retry the request once
      if (error instanceof Error && error.message === 'TOKEN_REFRESHED' && retryCount === 0) {
        return this.request<T>(endpoint, options, retryCount + 1)
      }
      throw error
    }
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
      throw new Error(errorData.detail || 'Échec de la connexion')
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
      throw new Error(errorData.detail || 'Échec du téléversement')
    }

    return response.json()
  }



  async updateInvoiceField(invoiceId: string, field: string, value: string | number | boolean | null): Promise<Invoice> {
    return this.request<Invoice>(`/api/invoices/${invoiceId}/update-field`, {
      method: 'PUT',
      body: JSON.stringify({ field, value }),
    })
  }

  async updateInvoiceReviewStatus(invoiceId: string, status: 'pending_review' | 'in_review' | 'reviewed' | 'approved' | 'rejected'): Promise<Invoice> {
    return this.request<Invoice>(`/api/invoices/${invoiceId}/review-status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    })
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

  // Export methods - Updated to match current backend API
  async exportApprovedInvoice(invoiceId: string, format: string): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/approved/${invoiceId}/${format}`, {
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

  async exportBatch(invoiceIds: string[], format: string): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/api/exports/batch?format=${format}`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(invoiceIds)
    })

    if (!response.ok) {
      const errorData: ApiError = await response.json()
      throw new Error(errorData.detail || 'Export failed')
    }

    return response.blob()
  }

  // Legacy methods (deprecated - use exportApprovedInvoice instead)
  async exportInvoiceCSV(invoiceId: string): Promise<Blob> {
    return this.exportApprovedInvoice(invoiceId, 'csv')
  }

  async exportInvoiceJSON(invoiceId: string): Promise<Blob> {
    return this.exportApprovedInvoice(invoiceId, 'json')
  }

  // Batch processing methods
  async post(endpoint: string, data: any, config?: RequestInit & { responseType?: 'blob' | 'json' }): Promise<any> {
    const url = `${this.baseURL}${endpoint}`
    const requestStartTime = Date.now()
    
    // For FormData, don't set Content-Type (let browser set it with boundary)
    const isFormData = data instanceof FormData
    const headers = {
      ...this.getAuthHeader(),
      ...config?.headers,
    }
    
    // Only add Content-Type for non-FormData requests
    if (!isFormData && !(headers as Record<string, string>)['Content-Type']) {
      (headers as Record<string, string>)['Content-Type'] = 'application/json'
    }
    
    const requestConfig: RequestInit = {
      method: 'POST',
      headers,
      body: data,
      ...config,
    }

    // Enhanced debugging for FormData
    if (isFormData && data instanceof FormData) {
      console.log('📦 ENHANCED FormData debugging:', {
        url,
        timestamp: new Date().toISOString(),
        formDataEntries: Array.from(data.entries()).map(([key, value]) => ({
          key,
          valueType: value instanceof File ? 'File' : typeof value,
          fileName: value instanceof File ? value.name : undefined,
          fileSize: value instanceof File ? value.size : undefined,
          fileType: value instanceof File ? value.type : undefined
        })),
        hasAuthToken: !!(headers as Record<string, string>)['Authorization'],
        authTokenPrefix: (headers as Record<string, string>)['Authorization']?.substring(0, 20),
        userAgent: navigator.userAgent,
        origin: window.location.origin,
        currentUrl: window.location.href
      })
    }

    // Add timeout to prevent hanging (30 seconds for testing)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => {
      console.log('⏰ TIMEOUT: Request aborted after 30 seconds')
      controller.abort()
    }, 30000)
    
    try {
      console.log('🌐 Making fetch request:', {
        url,
        method: requestConfig.method,
        hasAuth: !!(requestConfig.headers as Record<string, string>)?.Authorization,
        isFormData,
        bodyType: data instanceof FormData ? 'FormData' : typeof data,
        timestamp: new Date().toISOString(),
        requestId: Math.random().toString(36).substr(2, 9)
      })
      
      const fetchStartTime = Date.now()
      const response = await fetch(url, {
        ...requestConfig,
        signal: controller.signal
      })
      const fetchEndTime = Date.now()
      
      console.log('📡 Fetch response received:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        fetchDuration: `${fetchEndTime - fetchStartTime}ms`,
        totalDuration: `${fetchEndTime - requestStartTime}ms`,
        timestamp: new Date().toISOString()
      })
      
      clearTimeout(timeoutId)
      return this.handleResponse(response)
    } catch (error: any) {
      clearTimeout(timeoutId)
      const errorTime = Date.now()
      
      console.error('❌ DETAILED FETCH ERROR:', {
        errorName: error.name,
        errorMessage: error.message,
        errorStack: error.stack,
        url,
        isFormData,
        totalDuration: `${errorTime - requestStartTime}ms`,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        connectionStatus: navigator.onLine ? 'online' : 'offline',
        memoryUsage: (performance as any).memory ? {
          used: Math.round((performance as any).memory.usedJSHeapSize / 1024 / 1024) + 'MB',
          total: Math.round((performance as any).memory.totalJSHeapSize / 1024 / 1024) + 'MB'
        } : 'not available'
      })
      
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 30 seconds')
      }
      throw error
    }
  }

  async get(endpoint: string, config?: RequestInit): Promise<any> {
    const url = `${this.baseURL}${endpoint}`
    const requestConfig: RequestInit = {
      method: 'GET',
      headers: {
        ...this.getAuthHeader(),
        ...config?.headers,
      },
      ...config,
    }

    const response = await fetch(url, requestConfig)
    
    // Handle blob responses
    if ((config as any)?.responseType === 'blob') {
      if (!response.ok) {
        const errorData: ApiError = await response.json()
        throw new Error(errorData.detail || 'Request failed')
      }
      return response.blob()
    }
    
    return this.handleResponse(response)
  }

  async delete(endpoint: string): Promise<any> {
    return this.request(endpoint, { method: 'DELETE' })
  }

  // Utility method to check if user is authenticated
  isAuthenticated(): boolean {
    return !!Cookies.get('access_token')
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)

// WebSocket connection for real-time updates
export function createWebSocketConnection(invoiceId: string): WebSocket {
  const token = Cookies.get('access_token')
  const wsUrl = `${WS_BASE_URL}/ws/invoices/${invoiceId}?token=${token}`
  return new WebSocket(wsUrl)
}