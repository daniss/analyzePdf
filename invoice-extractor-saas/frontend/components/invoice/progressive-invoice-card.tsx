'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  FileText, 
  Bot, 
  Check, 
  Edit2, 
  Save,
  X,
  ChevronDown,
  ChevronRight,
  Zap,
  Building2,
  Calendar,
  Hash,
  DollarSign,
  Eye,
  Loader2,
  Clock,
  CheckCircle,
  Download
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { Invoice, FieldConfidence } from '@/lib/types'
import { useInvoiceProgress } from '@/lib/hooks/useInvoiceProgress'
import { useFrenchValidation, getFrenchFieldLabel } from '@/lib/hooks/useFrenchValidation'
import { SIRETStatusIndicator } from '@/components/validation/siret-status-indicator'
import { ExportFormatSelector } from '@/components/invoice/export-format-selector'

// Simplified: Single Claude Vision processing mode

interface ProgressiveInvoiceCardProps {
  invoice: Invoice
  onUpdate?: (invoice: Invoice) => void
  expanded?: boolean
  showReviewButton?: boolean
}

interface EditableFieldProps {
  label: string
  value: string | number | null | undefined
  confidence?: FieldConfidence
  field: string
  invoiceId: string
  onUpdate: (field: string, value: string | number) => void
  icon?: React.ReactNode
}

function getConfidenceBadge(confidence?: number) {
  if (!confidence) return null
  
  if (confidence >= 90) {
    return <Badge variant="success" className="text-xs">High</Badge>
  } else if (confidence >= 70) {
    return <Badge variant="warning" className="text-xs">Medium</Badge>
  } else {
    return <Badge variant="error" className="text-xs">Low</Badge>
  }
}

function getSourceIcon(source?: string) {
  switch (source) {
    case 'text':
      return <Zap className="h-3 w-3" />
    case 'ai':
      return <Bot className="h-3 w-3" />
    case 'manual':
      return <Edit2 className="h-3 w-3" />
    default:
      return null
  }
}

function EditableField({ label, value, confidence, field, invoiceId, onUpdate, icon }: EditableFieldProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(value || '')
  const [isSaving, setIsSaving] = useState(false)
  const { validateField, formatField } = useFrenchValidation()
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleSave = async () => {
    if (editValue === value) {
      setIsEditing(false)
      return
    }

    // French validation for business fields
    const frenchFields = [
      'siren', 'siret', 'tva', 'tva_number', 'postal_code',
      'vendor_siren', 'vendor_siret', 'vendor_tva',
      'customer_siren', 'customer_siret', 'customer_tva'
    ]
    const fieldType = field.replace(/^(vendor_|customer_)/, '') // Remove prefix for validation
    if (frenchFields.includes(field)) {
      const validation = validateField(fieldType, editValue.toString())
      if (!validation.isValid) {
        setValidationError(validation.error || 'Valeur invalide')
        return
      }
      setValidationError(null)
    }

    setIsSaving(true)
    try {
      const valueToSave = frenchFields.includes(field) ? formatField(field, editValue.toString()) : editValue
      await apiClient.updateInvoiceField(invoiceId, field, valueToSave)
      onUpdate(field, valueToSave)
      setIsEditing(false)
    } catch (error) {
      console.error('Failed to update field:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditValue(value || '')
    setValidationError(null)
    setIsEditing(false)
  }

  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          {icon}
          <label className="text-xs font-medium text-muted-foreground">{label}</label>
        </div>
        <div className="flex items-center gap-2">
          {confidence && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <div className="flex items-center gap-1">
                    {getSourceIcon(confidence.source)}
                    {getConfidenceBadge(confidence.confidence)}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">
                    Confidence: {confidence.confidence}%<br />
                    Source: {confidence.source}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {!isEditing && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setIsEditing(true)}
            >
              <Edit2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>
      
      {isEditing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Input
              value={editValue}
              onChange={(e) => {
                setEditValue(e.target.value)
                setValidationError(null) // Clear error when user types
              }}
              className={cn(
                "h-8 text-sm",
                validationError && "border-red-500 focus:border-red-500"
              )}
              disabled={isSaving}
            />
            <Button
              size="sm"
              className="h-8 w-8 p-0"
              onClick={handleSave}
              disabled={isSaving || !!validationError}
            >
              {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
              onClick={handleCancel}
              disabled={isSaving}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
          {validationError && (
            <p className="text-xs text-red-600">{validationError}</p>
          )}
        </div>
      ) : (
        <p className="text-sm font-medium">{value || '-'}</p>
      )}
    </div>
  )
}


export function ProgressiveInvoiceCard({ invoice, onUpdate, expanded: initialExpanded = false, showReviewButton = true }: ProgressiveInvoiceCardProps) {
  const router = useRouter()
  const [isExpanded, setIsExpanded] = useState(initialExpanded)
  const [localInvoice, setLocalInvoice] = useState(invoice)
  const { validateInvoiceAmount, getTVACalculation } = useFrenchValidation()
  
  // WebSocket connection for real-time updates
  const { invoice: wsInvoice } = useInvoiceProgress(
    invoice.status === 'processing' ? invoice.id : null
  )

  useEffect(() => {
    if (wsInvoice) {
      setLocalInvoice(wsInvoice)
      if (onUpdate) onUpdate(wsInvoice)
    }
  }, [wsInvoice, onUpdate])

  const handleFieldUpdate = (field: string, value: string | number) => {
    setLocalInvoice(prev => ({
      ...prev,
      data: {
        line_items: [],
        tva_breakdown: [],
        currency: 'EUR',
        ...prev.data,
        [field]: value
      }
    }))
  }

  const handleExport = async (format: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = localStorage.getItem('access_token')
      
      const response = await fetch(`${apiUrl}/api/exports/approved/${localInvoice.id}/${format}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Export failed')
      }

      // Create download link
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Get filename from Content-Disposition header or create default
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `facture_approuvee_${localInvoice.id}.${format}`
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

    } catch (error) {
      console.error('Export failed:', error)
      alert(`Erreur d'export: ${error.message}`)
    }
  }


  const isProcessing = localInvoice.status === 'processing'
  const isFailed = localInvoice.status === 'failed'
  
  return (
    <Card className={cn(
      "transition-all duration-300",
      isProcessing && "border-blue-200 bg-blue-50/30",
      isFailed && "border-red-200 bg-red-50/30",
      localInvoice.status === 'completed' && "hover:shadow-lg"
    )}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className={cn(
              "p-3 rounded-xl",
              isProcessing ? "bg-blue-100" : isFailed ? "bg-red-100" : "bg-primary/10"
            )}>
              <FileText className={cn(
                "h-6 w-6",
                isProcessing ? "text-blue-600" : isFailed ? "text-red-600" : "text-primary"
              )} />
            </div>
            <div>
              <CardTitle className="text-lg">{localInvoice.filename}</CardTitle>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-xs text-muted-foreground">
                  {new Date(localInvoice.created_at).toLocaleDateString()}
                </span>
                {/* Review Status Badge */}
                {localInvoice.status === 'completed' && (
                  <div className="flex items-center gap-1">
                    {(!localInvoice.review_status || localInvoice.review_status === 'pending_review') ? (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-orange-100 text-orange-700 text-xs">
                        <Clock className="h-3 w-3" />
                        À réviser
                      </div>
                    ) : localInvoice.review_status === 'approved' ? (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs">
                        <CheckCircle className="h-3 w-3" />
                        Approuvée
                      </div>
                    ) : localInvoice.review_status === 'in_review' ? (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-blue-100 text-blue-700 text-xs">
                        <Eye className="h-3 w-3" />
                        En révision
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-gray-700 text-xs">
                        <CheckCircle className="h-3 w-3" />
                        Révisée
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Review Button - Only show for completed invoices and when enabled */}
            {showReviewButton && localInvoice.status === 'completed' && localInvoice.data && (
              <Button
                variant={(!localInvoice.review_status || localInvoice.review_status === 'pending_review') ? "default" : "outline"}
                size="sm"
                onClick={() => router.push(`/invoices/${localInvoice.id}/review`)}
                className={cn(
                  "gap-2",
                  (!localInvoice.review_status || localInvoice.review_status === 'pending_review') && 
                  "bg-orange-500 hover:bg-orange-600 text-white border-0 shadow-lg"
                )}
              >
                <Eye className="h-4 w-4" />
                {(!localInvoice.review_status || localInvoice.review_status === 'pending_review') ? 'Réviser Maintenant' : 'Voir Révision'}
              </Button>
            )}
            
            {/* Export Button - Only show for approved invoices */}
            {localInvoice.status === 'completed' && localInvoice.review_status === 'approved' && (
              <ExportFormatSelector 
                invoiceId={localInvoice.id}
                onExportComplete={(format, success) => {
                  if (success) {
                    console.log(`Export ${format} completed successfully`)
                  }
                }}
              />
            )}
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        
        {/* Simplified: Single processing progress */}
        {isProcessing && (
          <div className="mt-4">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              <span className="text-sm text-blue-600">Processing with Gemini 2.5 Flash...</span>
            </div>
          </div>
        )}
        
        {/* Error Message for Failed Processing */}
        {isFailed && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-800">
              <X className="h-4 w-4" />
              <span className="font-medium">Échec du Traitement</span>
            </div>
            <p className="text-red-700 text-sm mt-1">
              {localInvoice.error_message || 'Le traitement de la facture a échoué. Veuillez réessayer ou contacter le support si le problème persiste.'}
            </p>
            {localInvoice.error_message?.includes('Claude API key') && (
              <p className="text-red-600 text-xs mt-2">
                💡 <strong>Note Admin:</strong> Configurez la variable d'environnement ANTHROPIC_API_KEY pour activer le traitement automatique.
              </p>
            )}
          </div>
        )}
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground">Basic Information</h4>
              
              <EditableField
                label="Invoice Number"
                value={localInvoice.data?.invoice_number}
                confidence={localInvoice.confidence_data?.invoice_number}
                field="invoice_number"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Hash className="h-3 w-3" />}
              />
              
              <EditableField
                label="Date"
                value={localInvoice.data?.date}
                confidence={localInvoice.confidence_data?.date}
                field="date"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Calendar className="h-3 w-3" />}
              />
              
              <EditableField
                label="Montant Total TTC"
                value={localInvoice.data?.total_ttc || localInvoice.data?.total}
                confidence={localInvoice.confidence_data?.total}
                field="total_ttc"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<DollarSign className="h-3 w-3" />}
              />
              
              <EditableField
                label="Montant HT"
                value={localInvoice.data?.subtotal_ht || localInvoice.data?.subtotal}
                confidence={localInvoice.confidence_data?.subtotal_ht || localInvoice.confidence_data?.subtotal}
                field="subtotal_ht"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<DollarSign className="h-3 w-3" />}
              />
              
              <EditableField
                label="Montant TVA"
                value={localInvoice.data?.total_tva || localInvoice.data?.tax}
                confidence={localInvoice.confidence_data?.total_tva || localInvoice.confidence_data?.tax}
                field="total_tva"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<DollarSign className="h-3 w-3" />}
              />
            </div>
            
            {/* Business Information */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground">Business Information</h4>
              
              <EditableField
                label="Vendor"
                value={localInvoice.data?.vendor?.name || localInvoice.data?.vendor_name}
                confidence={localInvoice.confidence_data?.vendor_name}
                field="vendor_name"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Building2 className="h-3 w-3" />}
              />
              
              <EditableField
                label="Customer"
                value={localInvoice.data?.customer?.name || localInvoice.data?.customer_name}
                confidence={localInvoice.confidence_data?.customer_name}
                field="customer_name"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Building2 className="h-3 w-3" />}
              />
              
              {localInvoice.data?.is_french_compliant && (
                <div className="flex items-center gap-2 text-green-600">
                  <Check className="h-4 w-4" />
                  <span className="text-sm font-medium">Conforme France</span>
                </div>
              )}
            </div>
            
            {/* French Business Identifiers */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground">Identifiants Français</h4>
              
              <EditableField
                label="N° SIREN Fournisseur"
                value={localInvoice.data?.vendor?.siren_number || localInvoice.data?.vendor?.siren || localInvoice.data?.vendor_siren}
                confidence={localInvoice.confidence_data?.vendor_siren}
                field="vendor_siren"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Hash className="h-3 w-3" />}
              />
              
              <EditableField
                label="N° SIRET Fournisseur"
                value={localInvoice.data?.vendor?.siret_number || localInvoice.data?.vendor?.siret || localInvoice.data?.vendor_siret}
                confidence={localInvoice.confidence_data?.vendor_siret}
                field="vendor_siret"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Hash className="h-3 w-3" />}
              />
              
              {/* SIRET Validation Status */}
              {localInvoice.siret_validation_results && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <h5 className="text-xs font-semibold text-gray-700 mb-2">Validation SIRET</h5>
                  <SIRETStatusIndicator
                    validationSummary={localInvoice.siret_validation_results}
                    invoiceId={localInvoice.id}
                    onValidationUpdate={async () => {
                      // Refresh the invoice data after SIRET validation update
                      try {
                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                        const token = document.cookie
                          .split('; ')
                          .find(row => row.startsWith('access_token='))
                          ?.split('=')[1]
                        
                        if (!token) return
                        
                        const response = await fetch(`${apiUrl}/api/invoices/${localInvoice.id}`, {
                          headers: {
                            'Authorization': `Bearer ${token}`,
                          }
                        })
                        
                        if (response.ok) {
                          const updatedInvoice = await response.json()
                          setLocalInvoice(updatedInvoice)
                          if (onUpdate) {
                            onUpdate(updatedInvoice)
                          }
                        }
                      } catch (error) {
                        console.error('Failed to refresh invoice after SIRET validation update:', error)
                      }
                    }}
                  />
                </div>
              )}
              
              <EditableField
                label="N° TVA Intracommunautaire"
                value={localInvoice.data?.vendor?.tva_number || localInvoice.data?.vendor_tva}
                confidence={localInvoice.confidence_data?.vendor_tva}
                field="vendor_tva"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Hash className="h-3 w-3" />}
              />
              
              <EditableField
                label="N° SIREN Client"
                value={localInvoice.data?.customer?.siren_number || localInvoice.data?.customer?.siren || localInvoice.data?.customer_siren}
                confidence={localInvoice.confidence_data?.customer_siren}
                field="customer_siren"
                invoiceId={localInvoice.id}
                onUpdate={handleFieldUpdate}
                icon={<Hash className="h-3 w-3" />}
              />
            </div>
          </div>
          
          {/* Overall Confidence */}
          {localInvoice.confidence_data?.overall && (
            <div className="mt-6 pt-6 border-t">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Overall Confidence</span>
                <div className="flex items-center gap-2">
                  <Progress value={localInvoice.confidence_data.overall} className="w-32 h-2" />
                  <span className="text-sm font-medium">{localInvoice.confidence_data.overall}%</span>
                </div>
              </div>
            </div>
          )}
          
          {/* Processing Status */}
          {isProcessing && (
            <div className="mt-6 pt-6 border-t">
              <div className="flex items-center gap-2 text-blue-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Traitement de la facture en cours...</span>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}