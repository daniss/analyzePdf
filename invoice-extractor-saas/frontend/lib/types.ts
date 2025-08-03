// Types matching backend schemas

export interface SubscriptionInfo {
  pricing_tier: 'FREE' | 'PRO' | 'BUSINESS' | 'ENTERPRISE'
  status: 'ACTIVE' | 'CANCELED' | 'PAST_DUE' | 'TRIALING' | 'INCOMPLETE'
  monthly_invoice_limit: number
  monthly_invoices_processed: number
  current_period_end?: string
}

export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
  company_name?: string
  subscription?: SubscriptionInfo
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
  tva_rate?: number
  tva_amount?: number
  unit?: string
}

export interface FrenchBusinessInfo {
  name: string
  address: string
  postal_code?: string
  city?: string
  country: string
  siren_number?: string
  siret_number?: string
  tva_number?: string
  naf_code?: string
  legal_form?: string
  share_capital?: number
  rcs_number?: string
  rm_number?: string
  phone?: string
  email?: string
}

export interface SIRETValidationResult {
  original_siret: string
  cleaned_siret?: string
  validation_status: string
  blocking_level: string
  compliance_risk: string
  traffic_light_color: string
  insee_company_name?: string
  company_is_active?: boolean
  name_similarity_score?: number
  auto_correction_attempted: boolean
  auto_correction_success: boolean
  correction_details: string[]
  error_message?: string
  validation_warnings: string[]
  french_error_message: string
  french_guidance: string
  recommended_actions: string[]
  user_options: Array<{
    action: string
    label: string
    description: string
  }>
  export_blocked: boolean
  export_warnings: string[]
  liability_warning_required: boolean
  validation_record_id?: string
}

export interface SIRETValidationSummary {
  vendor_siret_validation?: {
    performed: boolean
    status?: string
    blocking_level?: string
    compliance_risk?: string
    traffic_light?: string
    export_blocked?: boolean
    french_error_message?: string
    user_options_available?: boolean
  }
  customer_siret_validation?: {
    performed: boolean
    status?: string
    blocking_level?: string
    compliance_risk?: string
    traffic_light?: string
    export_blocked?: boolean
    french_error_message?: string
    user_options_available?: boolean
  }
  overall_summary?: {
    any_siret_found: boolean
    any_export_blocked: boolean
    highest_risk: string
    requires_user_action: boolean
  }
}

export interface FrenchTVABreakdown {
  rate: number
  taxable_amount: number
  tva_amount: number
}

export interface InvoiceData {
  // Basic invoice information
  invoice_number?: string
  date?: string
  due_date?: string
  invoice_sequence_number?: number
  
  // Business entities (French format)
  vendor?: FrenchBusinessInfo
  customer?: FrenchBusinessInfo
  
  // Legacy fields for backward compatibility
  vendor_name?: string
  vendor_address?: string
  customer_name?: string
  customer_address?: string
  
  // Line items with French enhancements
  line_items: LineItem[]
  
  // Financial information with French compliance
  subtotal_ht?: number
  tva_breakdown: FrenchTVABreakdown[]
  total_tva?: number
  total_ttc?: number
  subtotal?: number  // Legacy
  tax?: number       // Legacy
  total?: number     // Legacy
  currency: string
  
  // French mandatory clauses
  payment_terms?: string
  late_payment_penalties?: string
  recovery_fees?: string
  
  // Additional fields
  notes?: string
  delivery_date?: string
  delivery_address?: string
  
  // Compliance
  is_french_compliant?: boolean
  compliance_errors?: string[]
}

export type InvoiceStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type ProcessingMode = 'auto' | 'fast' | 'detailed'

export interface FieldConfidence {
  value: string | number | null | undefined
  confidence: number
  source: 'text' | 'ai' | 'manual'
}


export interface Invoice {
  id: string
  filename: string
  status: InvoiceStatus
  created_at: string
  updated_at?: string
  processing_started_at?: string
  processing_completed_at?: string
  data?: InvoiceData
  confidence_data?: {
    invoice_number?: FieldConfidence
    date?: FieldConfidence
    total?: FieldConfidence
    subtotal_ht?: FieldConfidence
    subtotal?: FieldConfidence
    total_tva?: FieldConfidence
    tax?: FieldConfidence
    total_ttc?: FieldConfidence
    vendor_name?: FieldConfidence
    customer_name?: FieldConfidence
    vendor_siren?: FieldConfidence
    vendor_siret?: FieldConfidence
    vendor_tva?: FieldConfidence
    customer_siren?: FieldConfidence
    customer_siret?: FieldConfidence
    customer_tva?: FieldConfidence
    overall: number
  }
  siret_validation_results?: SIRETValidationSummary
  error_message?: string
  review_status?: 'pending_review' | 'in_review' | 'reviewed' | 'approved' | 'rejected'
  processing_source?: 'individual' | 'batch' | 'api'
  batch_id?: string
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