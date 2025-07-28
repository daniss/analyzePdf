'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Clock,
  Edit3,
  Globe,
  FileX,
  AlertCircle,
  Info,
  Shield,
  Download,
  ExternalLink
} from 'lucide-react'

interface SIRETValidationCardProps {
  validationData: {
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
  onUserAction?: (action: string, justification: string, correctedSiret?: string) => void
  onRetryValidation?: () => void
}

export function SIRETValidationCard({ 
  validationData, 
  onUserAction, 
  onRetryValidation 
}: SIRETValidationCardProps) {
  const [showOverrideModal, setShowOverrideModal] = useState(false)
  const [selectedAction, setSelectedAction] = useState('')
  const [justification, setJustification] = useState('')
  const [correctedSiret, setCorrectedSiret] = useState('')
  const [showDetails, setShowDetails] = useState(false)

  // Traffic light indicator
  const getTrafficLightIcon = () => {
    switch (validationData.traffic_light_color) {
      case 'green':
        return <CheckCircle className="h-6 w-6 text-green-500" />
      case 'orange':
        return <AlertTriangle className="h-6 w-6 text-orange-500" />
      case 'red':
        return <XCircle className="h-6 w-6 text-red-500" />
      default:
        return <Clock className="h-6 w-6 text-gray-400" />
    }
  }

  // Status badge variant
  const getStatusBadgeVariant = () => {
    switch (validationData.traffic_light_color) {
      case 'green':
        return 'default'
      case 'orange':
        return 'secondary'
      case 'red':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  // Risk level badge
  const getRiskBadge = () => {
    const riskColors = {
      low: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-red-100 text-red-800',
      critical: 'bg-red-200 text-red-900'
    }
    
    return (
      <Badge className={riskColors[validationData.compliance_risk as keyof typeof riskColors] || 'bg-gray-100 text-gray-800'}>
        <Shield className="h-3 w-3 mr-1" />
        Risque {validationData.compliance_risk}
      </Badge>
    )
  }

  // Handle user action
  const handleUserAction = (action: string) => {
    setSelectedAction(action)
    if (action === 'manual_correction') {
      setCorrectedSiret(validationData.original_siret)
    }
    setShowOverrideModal(true)
  }

  const submitUserAction = () => {
    if (!justification.trim() || justification.length < 10) {
      alert('Veuillez fournir une justification d\'au moins 10 caractères')
      return
    }

    if (selectedAction === 'manual_correction' && (!correctedSiret || correctedSiret.length !== 14)) {
      alert('Veuillez saisir un SIRET valide de 14 chiffres')
      return
    }

    onUserAction?.(selectedAction, justification, correctedSiret || undefined)
    setShowOverrideModal(false)
    setJustification('')
    setCorrectedSiret('')
  }

  // Get action icon
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'manual_correction':
        return <Edit3 className="h-4 w-4" />
      case 'accept_warning':
        return <AlertTriangle className="h-4 w-4" />
      case 'mark_foreign':
        return <Globe className="h-4 w-4" />
      case 'reject_invoice':
        return <FileX className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  return (
    <>
      <Card className="w-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getTrafficLightIcon()}
              <div>
                <CardTitle className="text-lg">Validation SIRET</CardTitle>
                <CardDescription>
                  SIRET: {validationData.original_siret}
                  {validationData.cleaned_siret && validationData.cleaned_siret !== validationData.original_siret && (
                    <span className="text-blue-600"> → {validationData.cleaned_siret}</span>
                  )}
                </CardDescription>
              </div>
            </div>
            <div className="flex gap-2">
              {getRiskBadge()}
              <Badge variant={getStatusBadgeVariant()}>
                {validationData.validation_status.replace('_', ' ').toUpperCase()}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Main error/success message */}
          {validationData.french_error_message && (
            <div className={`p-3 rounded-lg ${
              validationData.traffic_light_color === 'red' ? 'bg-red-50 border border-red-200' :
              validationData.traffic_light_color === 'orange' ? 'bg-orange-50 border border-orange-200' :
              'bg-blue-50 border border-blue-200'
            }`}>
              <p className="font-medium text-sm">{validationData.french_error_message}</p>
            </div>
          )}

          {/* Export status */}
          {validationData.export_blocked ? (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <XCircle className="h-4 w-4 text-red-500" />
              <span className="text-sm font-medium text-red-700">Export bloqué</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
              <Download className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium text-green-700">Export autorisé</span>
              {validationData.export_warnings.length > 0 && (
                <span className="text-sm text-orange-600">avec avertissements</span>
              )}
            </div>
          )}

          {/* Export warnings */}
          {validationData.export_warnings.length > 0 && (
            <div className="space-y-1">
              {validationData.export_warnings.map((warning, index) => (
                <div key={index} className="flex items-center gap-2 text-sm text-orange-600">
                  <AlertTriangle className="h-3 w-3" />
                  {warning}
                </div>
              ))}
            </div>
          )}

          {/* INSEE company info */}
          {validationData.insee_company_name && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Info className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-medium text-blue-700">Informations INSEE</span>
              </div>
              <p className="text-sm text-blue-600">{validationData.insee_company_name}</p>
              {validationData.company_is_active !== undefined && (
                <p className="text-xs text-blue-500 mt-1">
                  Statut: {validationData.company_is_active ? 'Active' : 'Inactive'}
                </p>
              )}
              {validationData.name_similarity_score !== undefined && (
                <p className="text-xs text-blue-500">
                  Similarité nom: {validationData.name_similarity_score}%
                </p>
              )}
            </div>
          )}

          {/* French guidance */}
          {validationData.french_guidance && (
            <div className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
                className="w-full justify-between"
              >
                Conseils de conformité
                <ExternalLink className="h-3 w-3" />
              </Button>
              
              {showDetails && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <pre className="text-xs whitespace-pre-wrap text-gray-700">
                    {validationData.french_guidance}
                  </pre>
                  
                  {validationData.recommended_actions.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-700 mb-1">Actions recommandées:</p>
                      <ul className="text-xs text-gray-600 space-y-1">
                        {validationData.recommended_actions.map((action, index) => (
                          <li key={index} className="flex items-start gap-1">
                            <span className="text-blue-500">•</span>
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* User action buttons */}
          {validationData.user_options.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Actions possibles:</p>
              <div className="grid gap-2">
                {validationData.user_options.map((option, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => handleUserAction(option.action)}
                    className="justify-start h-auto p-3"
                  >
                    <div className="flex items-start gap-2 w-full">
                      {getActionIcon(option.action)}
                      <div className="text-left">
                        <div className="font-medium">{option.label}</div>
                        <div className="text-xs text-gray-500">{option.description}</div>
                      </div>
                    </div>
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Auto-correction details */}
          {validationData.auto_correction_attempted && validationData.correction_details.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                Détails correction automatique
              </summary>
              <div className="mt-2 p-2 bg-gray-50 rounded border">
                <ul className="space-y-1">
                  {validationData.correction_details.map((detail, index) => (
                    <li key={index} className="text-gray-600">• {detail}</li>
                  ))}
                </ul>
              </div>
            </details>
          )}

          {/* Retry button */}
          {onRetryValidation && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetryValidation}
              className="w-full"
            >
              Relancer la validation
            </Button>
          )}
        </CardContent>
      </Card>

      {/* User Override Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">
              Action: {validationData.user_options.find(o => o.action === selectedAction)?.label}
            </h3>
            
            {selectedAction === 'manual_correction' && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">SIRET corrigé:</label>
                <Input
                  value={correctedSiret}
                  onChange={(e) => setCorrectedSiret(e.target.value.replace(/\D/g, '').slice(0, 14))}
                  placeholder="14 chiffres"
                  maxLength={14}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Saisissez le SIRET correct de 14 chiffres
                </p>
              </div>
            )}

            {validationData.liability_warning_required && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-red-700">Avertissement de responsabilité</p>
                    <p className="text-red-600 mt-1">
                      Cette action peut engager votre responsabilité professionnelle. 
                      Assurez-vous de la légitimité de cette décision.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                Justification (obligatoire):
              </label>
              <Textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Expliquez la raison de cette action..."
                rows={3}
                className="resize-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                Minimum 10 caractères pour traçabilité
              </p>
            </div>

            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowOverrideModal(false)}
              >
                Annuler
              </Button>
              <Button
                onClick={submitUserAction}
                disabled={justification.length < 10}
              >
                Confirmer
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}