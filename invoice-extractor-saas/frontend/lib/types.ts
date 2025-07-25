// Types matching backend schemas

export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
  company_name?: string
}

export interface UserCreate {
  email: string
  password: string
  company_name?: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface LineItem {
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface InvoiceData {
  invoice_number?: string
  date?: string
  vendor_name?: string
  vendor_address?: string
  customer_name?: string
  customer_address?: string
  line_items: LineItem[]
  subtotal?: number
  tax?: number
  total?: number
  currency: string
}

export interface Invoice {
  id: string
  filename: string
  status: 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at?: string
  data?: InvoiceData
  error_message?: string
}

export interface ApiError {
  detail: string
}

export interface DashboardStats {
  total_invoices: number
  total_amount: number
  avg_processing_time: number
  accuracy_rate: number
}