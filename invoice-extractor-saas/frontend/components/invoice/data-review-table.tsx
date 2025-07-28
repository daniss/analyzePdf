'use client'

import { useState, useEffect } from 'react'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { 
  Check, 
  X, 
  Edit, 
  Save, 
  RotateCcw, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  Eye,
  EyeOff,
  Sparkles,
  User,
  TrendingUp,
  TrendingDown
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Invoice } from '@/lib/types'
import { apiClient } from '@/lib/api'
import { SIRETStatusIndicator } from '@/components/validation/siret-status-indicator'

interface ReviewField {
  key: string
  label: string
  category: 'basic' | 'amounts' | 'business' | 'french_compliance' | 'line_items'
  aiValue: any
  currentValue: any
  isEditing: boolean
  isRequired: boolean
  fieldType: 'text' | 'number' | 'date' | 'email' | 'siret' | 'siren' | 'tva'
  confidence?: number
  validationStatus: 'valid' | 'invalid' | 'warning' | 'pending'
  validationMessage?: string
  hasBeenModified: boolean
}

interface DataReviewTableProps {
  invoice: Invoice
  onUpdate?: (updatedInvoice: Invoice) => void
  onApprove?: () => void
  onReject?: () => void
}

export function DataReviewTable({ invoice, onUpdate, onApprove, onReject }: DataReviewTableProps) {
  const [reviewFields, setReviewFields] = useState<ReviewField[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showOnlyModified, setShowOnlyModified] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [globalValidationStatus, setGlobalValidationStatus] = useState<'pending' | 'valid' | 'invalid'>('pending')

  // Initialize review fields from invoice data
  useEffect(() => {
    if (invoice?.data) {
      const fields = createReviewFields(invoice.data)
      setReviewFields(fields)
      updateGlobalValidationStatus(fields)
    }
  }, [invoice])

  const createReviewFields = (data: any): ReviewField[] => {
    const fields: ReviewField[] = [
      // Basic Information
      {
        key: 'invoice_number',
        label: 'Numéro de Facture',
        category: 'basic',
        aiValue: data.invoice_number,
        currentValue: data.invoice_number,
        isEditing: false,
        isRequired: true,
        fieldType: 'text',
        confidence: 95,
        validationStatus: data.invoice_number ? 'valid' : 'invalid',
        validationMessage: data.invoice_number ? undefined : 'Numéro de facture requis',
        hasBeenModified: false
      },
      {
        key: 'date',
        label: 'Date',
        category: 'basic',
        aiValue: data.date,
        currentValue: data.date,
        isEditing: false,
        isRequired: true,
        fieldType: 'date',
        confidence: 92,
        validationStatus: data.date ? 'valid' : 'invalid',
        validationMessage: data.date ? undefined : 'Date de facture requise',
        hasBeenModified: false
      },
      {
        key: 'due_date',
        label: 'Date d\'Échéance',
        category: 'basic',
        aiValue: data.due_date,
        currentValue: data.due_date,
        isEditing: false,
        isRequired: false,
        fieldType: 'date',
        confidence: 88,
        validationStatus: 'valid',
        hasBeenModified: false
      },

      // Financial Amounts
      {
        key: 'subtotal_ht',
        label: 'Montant HT',
        category: 'amounts',
        aiValue: data.subtotal_ht || data.subtotal,
        currentValue: data.subtotal_ht || data.subtotal,
        isEditing: false,
        isRequired: true,
        fieldType: 'number',
        confidence: 96,
        validationStatus: (data.subtotal_ht || data.subtotal) ? 'valid' : 'invalid',
        validationMessage: (data.subtotal_ht || data.subtotal) ? undefined : 'Montant HT requis',
        hasBeenModified: false
      },
      {
        key: 'total_tva',
        label: 'Montant TVA',
        category: 'amounts',
        aiValue: data.total_tva || data.tax,
        currentValue: data.total_tva || data.tax,
        isEditing: false,
        isRequired: true,
        fieldType: 'number',
        confidence: 94,
        validationStatus: (data.total_tva || data.tax) ? 'valid' : 'invalid',
        validationMessage: (data.total_tva || data.tax) ? undefined : 'Montant TVA requis',
        hasBeenModified: false
      },
      {
        key: 'total_ttc',
        label: 'Montant Total TTC',
        category: 'amounts',
        aiValue: data.total_ttc || data.total,
        currentValue: data.total_ttc || data.total,
        isEditing: false,
        isRequired: true,
        fieldType: 'number',
        confidence: 98,
        validationStatus: (data.total_ttc || data.total) ? 'valid' : 'invalid',
        validationMessage: (data.total_ttc || data.total) ? undefined : 'Montant total requis',
        hasBeenModified: false
      },

      // Business Information
      {
        key: 'vendor_name',
        label: 'Nom Fournisseur',
        category: 'business',
        aiValue: data.vendor?.name || data.vendor_name,
        currentValue: data.vendor?.name || data.vendor_name,
        isEditing: false,
        isRequired: true,
        fieldType: 'text',
        confidence: 97,
        validationStatus: (data.vendor?.name || data.vendor_name) ? 'valid' : 'invalid',
        validationMessage: (data.vendor?.name || data.vendor_name) ? undefined : 'Nom du fournisseur requis',
        hasBeenModified: false
      },
      {
        key: 'customer_name',
        label: 'Nom Client',
        category: 'business',
        aiValue: data.customer?.name || data.customer_name,
        currentValue: data.customer?.name || data.customer_name,
        isEditing: false,
        isRequired: true,
        fieldType: 'text',
        confidence: 93,
        validationStatus: (data.customer?.name || data.customer_name) ? 'valid' : 'invalid',
        validationMessage: (data.customer?.name || data.customer_name) ? undefined : 'Nom du client requis',
        hasBeenModified: false
      },

      // French Compliance
      {
        key: 'vendor.siret_number',
        label: 'SIRET Fournisseur',
        category: 'french_compliance',
        aiValue: data.vendor?.siret_number,
        currentValue: data.vendor?.siret_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'siret',
        confidence: 85,
        validationStatus: data.vendor?.siret_number ? 'valid' : 'warning',
        validationMessage: data.vendor?.siret_number ? undefined : 'SIRET recommandé pour facturation française',
        hasBeenModified: false
      },
      {
        key: 'vendor.siren_number',
        label: 'SIREN Fournisseur',
        category: 'french_compliance',
        aiValue: data.vendor?.siren_number,
        currentValue: data.vendor?.siren_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'siren',
        confidence: 85,
        validationStatus: data.vendor?.siren_number ? 'valid' : 'warning',
        validationMessage: data.vendor?.siren_number ? undefined : 'SIREN recommandé pour facturation française',
        hasBeenModified: false
      },
      {
        key: 'vendor.tva_number',
        label: 'N° TVA Fournisseur',
        category: 'french_compliance',
        aiValue: data.vendor?.tva_number,
        currentValue: data.vendor?.tva_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'tva',
        confidence: 82,
        validationStatus: data.vendor?.tva_number ? 'valid' : 'warning',
        validationMessage: data.vendor?.tva_number ? undefined : 'N° TVA recommandé',
        hasBeenModified: false
      },
      {
        key: 'customer.siret_number',
        label: 'SIRET Client',
        category: 'french_compliance',
        aiValue: data.customer?.siret_number,
        currentValue: data.customer?.siret_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'siret',
        confidence: 85,
        validationStatus: data.customer?.siret_number ? 'valid' : 'warning',
        validationMessage: data.customer?.siret_number ? undefined : 'SIRET recommandé pour facturation française',
        hasBeenModified: false
      },
      {
        key: 'customer.siren_number',
        label: 'SIREN Client',
        category: 'french_compliance',
        aiValue: data.customer?.siren_number,
        currentValue: data.customer?.siren_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'siren',
        confidence: 85,
        validationStatus: data.customer?.siren_number ? 'valid' : 'warning',
        validationMessage: data.customer?.siren_number ? undefined : 'SIREN recommandé pour facturation française',
        hasBeenModified: false
      },
      {
        key: 'customer.tva_number',
        label: 'N° TVA Client',
        category: 'french_compliance',
        aiValue: data.customer?.tva_number,
        currentValue: data.customer?.tva_number,
        isEditing: false,
        isRequired: false,
        fieldType: 'tva',
        confidence: 82,
        validationStatus: data.customer?.tva_number ? 'valid' : 'warning',
        validationMessage: data.customer?.tva_number ? undefined : 'N° TVA recommandé',
        hasBeenModified: false
      }
    ]

    return fields
  }

  const updateGlobalValidationStatus = (fields: ReviewField[]) => {
    const hasInvalid = fields.some(f => f.isRequired && f.validationStatus === 'invalid')
    const hasWarnings = fields.some(f => f.validationStatus === 'warning')
    
    if (hasInvalid) {
      setGlobalValidationStatus('invalid')
    } else if (hasWarnings) {
      setGlobalValidationStatus('valid')
    } else {
      setGlobalValidationStatus('valid')
    }
  }

  const startEditing = (fieldKey: string) => {
    setReviewFields(prev => prev.map(field =>
      field.key === fieldKey 
        ? { ...field, isEditing: true }
        : field
    ))
  }

  const cancelEditing = (fieldKey: string) => {
    setReviewFields(prev => prev.map(field =>
      field.key === fieldKey 
        ? { ...field, isEditing: false }
        : field
    ))
  }

  const saveField = async (fieldKey: string, newValue: any) => {
    setIsLoading(true)
    try {
      // Update field via API
      await apiClient.updateInvoiceField(invoice.id, fieldKey, newValue)
      
      // Validate the new value
      const newValidationStatus = validateField(fieldKey.includes('.') ? fieldKey.split('.')[1] : fieldKey, newValue)
      
      // Update local state
      setReviewFields(prev => prev.map(field =>
        field.key === fieldKey 
          ? { 
              ...field, 
              currentValue: newValue, 
              isEditing: false, 
              hasBeenModified: true,
              validationStatus: newValidationStatus,
              validationMessage: getValidationMessage(fieldKey, newValue, newValidationStatus)
            }
          : field
      ))

      // Update global validation status
      const updatedFields = reviewFields.map(field =>
        field.key === fieldKey 
          ? { ...field, currentValue: newValue, validationStatus: newValidationStatus }
          : field
      )
      updateGlobalValidationStatus(updatedFields)

      // For SIRET/SIREN fields, trigger real-time validation feedback
      if (fieldKey.includes('siret_number') || fieldKey.includes('siren_number')) {
        // Show loading state for SIRET validation
        setReviewFields(prev => prev.map(field =>
          field.key === fieldKey 
            ? { ...field, validationMessage: 'Validation SIRET en cours...' }
            : field
        ))
        
        // The backend will automatically trigger SIRET validation
        // We'll get the updated results when we fetch the invoice
        setTimeout(async () => {
          try {
            const updatedInvoice = await apiClient.getInvoice(invoice.id)
            if (onUpdate) onUpdate(updatedInvoice)
          } catch (error) {
            console.error('Failed to refresh SIRET validation:', error)
          }
        }, 2000) // Give time for backend validation to complete
      }

      // Trigger update callback
      if (onUpdate) {
        // Fetch updated invoice data
        const updatedInvoice = await apiClient.getInvoice(invoice.id)
        onUpdate(updatedInvoice)
      }
    } catch (error) {
      console.error('Failed to update field:', error)
      // Show error state
      setReviewFields(prev => prev.map(field =>
        field.key === fieldKey 
          ? { 
              ...field, 
              isEditing: false,
              validationStatus: 'invalid',
              validationMessage: `Erreur: ${error.message || 'Mise à jour échouée'}`
            }
          : field
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const getValidationMessage = (fieldKey: string, value: any, status: string): string | undefined => {
    if (!value && status === 'invalid') {
      return 'Champ requis'
    }
    
    const fieldType = fieldKey.includes('.') ? fieldKey.split('.')[1] : fieldKey
    
    switch (fieldType) {
      case 'siret_number':
        if (status === 'invalid') return 'SIRET invalide (14 chiffres requis)'
        if (status === 'valid') return 'SIRET valide'
        break
      case 'siren_number':
        if (status === 'invalid') return 'SIREN invalide (9 chiffres requis)'
        if (status === 'valid') return 'SIREN valide'
        break
      case 'tva_number':
        if (status === 'invalid') return 'N° TVA invalide (format: FR + 11 chiffres)'
        if (status === 'valid') return 'N° TVA valide'
        break
      case 'email':
        if (status === 'invalid') return 'Email invalide'
        break
      case 'number':
        if (status === 'invalid') return 'Nombre invalide'
        break
    }
    
    return undefined
  }

  const validateField = (fieldType: string, value: any): 'valid' | 'invalid' | 'warning' => {
    if (!value || value === '') {
      // Required fields
      if (['invoice_number', 'date', 'vendor_name', 'customer_name', 'subtotal_ht', 'total_tva', 'total_ttc'].includes(fieldType)) {
        return 'invalid'
      }
      // Optional French compliance fields
      return 'warning'
    }
    
    const stringValue = value.toString().trim()
    
    switch (fieldType) {
      case 'siret_number':
        return /^\d{14}$/.test(stringValue) ? 'valid' : 'invalid'
      case 'siren_number':
        return /^\d{9}$/.test(stringValue) ? 'valid' : 'invalid'
      case 'tva_number':
        return /^FR\d{11}$/.test(stringValue.toUpperCase()) ? 'valid' : 'invalid'
      case 'email':
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(stringValue) ? 'valid' : 'invalid'
      case 'number':
        return !isNaN(parseFloat(stringValue)) && isFinite(parseFloat(stringValue)) ? 'valid' : 'invalid'
      case 'date':
        return /^\d{4}-\d{2}-\d{2}$/.test(stringValue) || /^\d{2}\/\d{2}\/\d{4}$/.test(stringValue) ? 'valid' : 'invalid'
      default:
        return 'valid'
    }
  }

  const resetField = (fieldKey: string) => {
    setReviewFields(prev => prev.map(field =>
      field.key === fieldKey 
        ? { 
            ...field, 
            currentValue: field.aiValue, 
            isEditing: false, 
            hasBeenModified: false,
            validationStatus: validateField(field.fieldType, field.aiValue)
          }
        : field
    ))
  }

  const getConfidenceBadge = (confidence?: number) => {
    if (!confidence) return null
    
    if (confidence >= 95) {
      return <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-100">
        <CheckCircle className="h-3 w-3 mr-1" />
        {confidence}%
      </Badge>
    } else if (confidence >= 80) {
      return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
        <Clock className="h-3 w-3 mr-1" />
        {confidence}%
      </Badge>
    } else {
      return <Badge variant="destructive" className="bg-red-100 text-red-800 hover:bg-red-100">
        <AlertTriangle className="h-3 w-3 mr-1" />
        {confidence}%
      </Badge>
    }
  }

  const getValidationIcon = (status: string) => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'invalid':
        return <X className="h-4 w-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const filteredFields = reviewFields.filter(field => {
    if (selectedCategory !== 'all' && field.category !== selectedCategory) return false
    if (showOnlyModified && !field.hasBeenModified) return false
    return true
  })

  const categories = [
    { key: 'all', label: 'Tous les Champs', count: reviewFields.length },
    { key: 'basic', label: 'Informations de Base', count: reviewFields.filter(f => f.category === 'basic').length },
    { key: 'amounts', label: 'Montants', count: reviewFields.filter(f => f.category === 'amounts').length },
    { key: 'business', label: 'Entreprises', count: reviewFields.filter(f => f.category === 'business').length },
    { key: 'french_compliance', label: 'Conformité Française', count: reviewFields.filter(f => f.category === 'french_compliance').length }
  ]

  const modifiedCount = reviewFields.filter(f => f.hasBeenModified).length
  const invalidCount = reviewFields.filter(f => f.validationStatus === 'invalid').length
  const validCount = reviewFields.filter(f => f.validationStatus === 'valid').length

  return (
    <div className="space-y-6">
      {/* Header with Status */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Révision des Données</h2>
          <p className="text-muted-foreground">
            Vérifiez et corrigez les données extraites avant export
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {getValidationIcon(globalValidationStatus)}
            <span className="text-sm font-medium">
              {invalidCount > 0 
                ? `${invalidCount} erreur${invalidCount > 1 ? 's' : ''}`
                : validCount === reviewFields.length 
                  ? 'Toutes les données sont valides'
                  : 'Vérification en cours'
              }
            </span>
          </div>
          
          {modifiedCount > 0 && (
            <Badge variant="outline" className="gap-1">
              <Edit className="h-3 w-3" />
              {modifiedCount} modifié{modifiedCount > 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </div>

      {/* Category Filters */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {categories.map(category => (
            <Button
              key={category.key}
              variant={selectedCategory === category.key ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category.key)}
              className="gap-2"
            >
              {category.label}
              <Badge variant="secondary" className="ml-1">
                {category.count}
              </Badge>
            </Button>
          ))}
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowOnlyModified(!showOnlyModified)}
            className={cn("gap-2", showOnlyModified && "bg-blue-50 border-blue-200")}
          >
            {showOnlyModified ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            {showOnlyModified ? 'Tous' : 'Modifiés uniquement'}
          </Button>
        </div>
      </div>

      {/* SIRET Validation Summary */}
      {invoice.siret_validation_results && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Validation SIRET</CardTitle>
          </CardHeader>
          <CardContent>
            <SIRETStatusIndicator 
              validationSummary={invoice.siret_validation_results}
              invoiceId={invoice.id}
              onValidationUpdate={async () => {
                // Refresh the invoice data after SIRET validation update
                try {
                  const updatedInvoice = await apiClient.getInvoice(invoice.id)
                  if (onUpdate) {
                    onUpdate(updatedInvoice)
                  }
                } catch (error) {
                  console.error('Failed to refresh invoice after SIRET validation update:', error)
                }
              }}
            />
          </CardContent>
        </Card>
      )}

      {/* Review Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Champ</TableHead>
              <TableHead className="w-[200px]">Valeur IA</TableHead>
              <TableHead className="w-[200px]">Valeur Révisée</TableHead>
              <TableHead className="w-[100px]">Confiance</TableHead>
              <TableHead className="w-[100px]">Statut</TableHead>
              <TableHead className="w-[150px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredFields.map((field) => (
              <TableRow key={field.key} className={cn(
                field.hasBeenModified && "bg-blue-50/50",
                field.validationStatus === 'invalid' && "bg-red-50/50"
              )}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    {field.hasBeenModified && <Edit className="h-4 w-4 text-blue-500" />}
                    {field.isRequired && <span className="text-red-500">*</span>}
                    {field.label}
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-500" />
                    <span className="font-mono text-sm">
                      {field.aiValue || <span className="text-gray-400 italic">Non détecté</span>}
                    </span>
                  </div>
                </TableCell>
                
                <TableCell>
                  {field.isEditing ? (
                    <div className="flex items-center gap-2">
                      <Input
                        type={field.fieldType === 'number' ? 'number' : 'text'}
                        defaultValue={field.currentValue || ''}
                        className="h-8"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            saveField(field.key, (e.target as HTMLInputElement).value)
                          }
                          if (e.key === 'Escape') {
                            cancelEditing(field.key)
                          }
                        }}
                        autoFocus
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-green-500" />
                      <span className="font-mono text-sm">
                        {field.currentValue || <span className="text-gray-400 italic">Vide</span>}
                      </span>
                    </div>
                  )}
                </TableCell>
                
                <TableCell>
                  {getConfidenceBadge(field.confidence)}
                </TableCell>
                
                <TableCell>
                  <div className="flex items-center gap-1">
                    {getValidationIcon(field.validationStatus)}
                    {field.validationMessage && (
                      <span className="text-xs text-gray-500">
                        {field.validationMessage}
                      </span>
                    )}
                  </div>
                </TableCell>
                
                <TableCell>
                  <div className="flex items-center gap-1">
                    {field.isEditing ? (
                      <>
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => {
                            const input = document.querySelector(`input`) as HTMLInputElement
                            saveField(field.key, input?.value || '')
                          }}
                        >
                          <Save className="h-4 w-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => cancelEditing(field.key)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => startEditing(field.key)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        {field.hasBeenModified && (
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => resetField(field.key)}
                            title="Restaurer la valeur IA"
                          >
                            <RotateCcw className="h-4 w-4" />
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-6 border-t">
        <div className="text-sm text-muted-foreground">
          {modifiedCount > 0 
            ? `${modifiedCount} champ${modifiedCount > 1 ? 's' : ''} modifié${modifiedCount > 1 ? 's' : ''}`
            : 'Aucune modification'
          }
          {invalidCount > 0 && (
            <span className="text-red-600 ml-2">
              • {invalidCount} erreur${invalidCount > 1 ? 's' : ''} à corriger
            </span>
          )}
        </div>
        
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={onReject}
            disabled={isLoading}
          >
            Rejeter
          </Button>
          <Button 
            onClick={onApprove}
            disabled={invalidCount > 0 || isLoading}
            className="gap-2"
          >
            <CheckCircle className="h-4 w-4" />
            Approuver pour Export
          </Button>
        </div>
      </div>
      
      {/* Success/Error Feedback Toast */}
      {modifiedCount > 0 && invalidCount === 0 && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="h-4 w-4" />
            <span className="font-medium">Données validées avec succès</span>
          </div>
          <p className="text-green-700 text-sm mt-1">
            Tous les champs sont valides. La facture peut être approuvée pour export.
          </p>
        </div>
      )}
    </div>
  )
}