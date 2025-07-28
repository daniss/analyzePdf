'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Clock,
  Building2,
  Info,
  Shield,
  ExternalLink
} from 'lucide-react'
import { SIRETValidationSummary } from '@/lib/types'
import { SIRETValidationCard } from './siret-validation-card'

interface SIRETStatusIndicatorProps {
  validationSummary?: SIRETValidationSummary
  invoiceId: string
  onValidationUpdate?: () => void
}

export function SIRETStatusIndicator({ 
  validationSummary, 
  invoiceId,
  onValidationUpdate 
}: SIRETStatusIndicatorProps) {
  const [showDetails, setShowDetails] = useState(false)

  if (!validationSummary?.overall_summary?.any_siret_found) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Building2 className="h-4 w-4" />
        <span>Aucun SIRET détecté</span>
      </div>
    )
  }

  const overall = validationSummary.overall_summary!
  const vendor = validationSummary.vendor_siret_validation
  const customer = validationSummary.customer_siret_validation

  // Get the worst status for overall indicator
  const getOverallStatus = () => {
    if (overall.any_export_blocked) return 'blocked'
    if (overall.requires_user_action) return 'warning'
    return 'valid'
  }

  const status = getOverallStatus()

  // Get appropriate icon and color
  const getStatusIcon = () => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />
      case 'blocked':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusText = () => {
    if (overall.any_export_blocked) return 'SIRET Bloqué'
    if (overall.requires_user_action) return 'Action Requise'
    return 'SIRET Validé'
  }

  const getStatusBadgeVariant = () => {
    switch (status) {
      case 'valid':
        return 'default'
      case 'warning':
        return 'secondary'
      case 'blocked':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  return (
    <div className="space-y-2">
      {/* Main status indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-sm font-medium">{getStatusText()}</span>
          <Badge variant={getStatusBadgeVariant()} className="text-xs">
            <Shield className="h-3 w-3 mr-1" />
            {overall.highest_risk}
          </Badge>
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowDetails(!showDetails)}
          className="h-8 px-2"
        >
          <Info className="h-3 w-3 mr-1" />
          Détails
          <ExternalLink className="h-3 w-3 ml-1" />
        </Button>
      </div>

      {/* Individual SIRET status */}
      <div className="space-y-1">
        {vendor?.performed && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-600">Fournisseur:</span>
            <div className="flex items-center gap-1">
              {vendor.traffic_light === 'green' && <CheckCircle className="h-3 w-3 text-green-500" />}
              {vendor.traffic_light === 'orange' && <AlertTriangle className="h-3 w-3 text-orange-500" />}
              {vendor.traffic_light === 'red' && <XCircle className="h-3 w-3 text-red-500" />}
              <span className="capitalize">{vendor.status?.replace('_', ' ')}</span>
              {vendor.export_blocked && (
                <Badge variant="destructive" className="text-xs ml-1">Bloqué</Badge>
              )}
            </div>
          </div>
        )}

        {customer?.performed && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-600">Client:</span>
            <div className="flex items-center gap-1">
              {customer.traffic_light === 'green' && <CheckCircle className="h-3 w-3 text-green-500" />}
              {customer.traffic_light === 'orange' && <AlertTriangle className="h-3 w-3 text-orange-500" />}
              {customer.traffic_light === 'red' && <XCircle className="h-3 w-3 text-red-500" />}
              <span className="capitalize">{customer.status?.replace('_', ' ')}</span>
              {customer.export_blocked && (
                <Badge variant="destructive" className="text-xs ml-1">Bloqué</Badge>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Export blocking warning */}
      {overall.any_export_blocked && (
        <div className="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded text-xs">
          <XCircle className="h-3 w-3 text-red-500" />
          <span className="text-red-700 font-medium">Export bloqué - action requise</span>
        </div>
      )}

      {/* Action required warning */}
      {overall.requires_user_action && !overall.any_export_blocked && (
        <div className="flex items-center gap-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs">
          <AlertTriangle className="h-3 w-3 text-orange-500" />
          <span className="text-orange-700 font-medium">Vérification recommandée</span>
        </div>
      )}

      {/* Detailed validation view */}
      {showDetails && (
        <div className="mt-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
          <div className="space-y-3">
            <h4 className="font-medium text-sm">Validation SIRET détaillée</h4>
            
            {vendor?.performed && (
              <div>
                <h5 className="text-xs font-medium text-gray-700 mb-1">Fournisseur</h5>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Statut: <span className="font-medium">{vendor.status}</span></div>
                  <div>Niveau de blocage: <span className="font-medium">{vendor.blocking_level}</span></div>
                  <div>Risque: <span className="font-medium">{vendor.compliance_risk}</span></div>
                  {vendor.french_error_message && (
                    <div className="text-red-600">⚠️ {vendor.french_error_message}</div>
                  )}
                  {vendor.user_options_available && (
                    <div className="text-blue-600">💡 Actions utilisateur disponibles</div>
                  )}
                </div>
              </div>
            )}

            {customer?.performed && (
              <div>
                <h5 className="text-xs font-medium text-gray-700 mb-1">Client</h5>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Statut: <span className="font-medium">{customer.status}</span></div>
                  <div>Niveau de blocage: <span className="font-medium">{customer.blocking_level}</span></div>
                  <div>Risque: <span className="font-medium">{customer.compliance_risk}</span></div>
                  {customer.french_error_message && (
                    <div className="text-red-600">⚠️ {customer.french_error_message}</div>
                  )}
                  {customer.user_options_available && (
                    <div className="text-blue-600">💡 Actions utilisateur disponibles</div>
                  )}
                </div>
              </div>
            )}

            {overall.requires_user_action && (
              <div className="space-y-2 mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => {
                    // TODO: Open full SIRET validation modal
                    console.log('Open SIRET validation modal for invoice:', invoiceId)
                  }}
                >
                  Gérer la validation SIRET
                </Button>
                
                {/* Quick actions for common SIRET issues */}
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={async () => {
                      try {
                        // Trigger SIRET re-validation
                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                        const token = document.cookie
                          .split('; ')
                          .find(row => row.startsWith('access_token='))
                          ?.split('=')[1]
                        
                        if (!token) {
                          alert('Token d\'authentification introuvable')
                          return
                        }
                        
                        const response = await fetch(`${apiUrl}/api/siret/revalidate/${invoiceId}`, {
                          method: 'POST',
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          }
                        })
                        
                        if (response.ok) {
                          alert('Re-validation SIRET terminée avec succès')
                          if (onValidationUpdate) {
                            onValidationUpdate()
                          }
                        } else {
                          const errorData = await response.json()
                          alert(`Erreur de re-validation: ${errorData.detail || 'Erreur inconnue'}`)
                        }
                      } catch (error) {
                        console.error('Re-validation failed:', error)
                        alert(`Erreur de re-validation: ${error.message}`)
                      }
                    }}
                  >
                    🔄 Re-valider
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={async () => {
                      // Override validation (requires user confirmation and justification)
                      const confirmed = window.confirm(
                        'Êtes-vous sûr de vouloir ignorer la validation SIRET ? Cela peut affecter la conformité fiscale.'
                      )
                      if (confirmed) {
                        const justification = window.prompt(
                          'Veuillez fournir une justification pour ignorer cette validation SIRET (minimum 10 caractères):'
                        )
                        
                        if (!justification || justification.trim().length < 10) {
                          alert('Justification requise (minimum 10 caractères)')
                          return
                        }
                        
                        try {
                          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                          const token = document.cookie
                          .split('; ')
                          .find(row => row.startsWith('access_token='))
                          ?.split('=')[1]
                          
                          if (!token) {
                            alert('Token d\'authentification introuvable')
                            return
                          }
                          
                          // Find the most recent validation record for this invoice
                          // We need to call the validation history endpoint to get the latest record ID
                          const historyResponse = await fetch(`${apiUrl}/api/siret/validation-history/${invoiceId}`, {
                            headers: {
                              'Authorization': `Bearer ${token}`,
                            }
                          })
                          
                          if (!historyResponse.ok) {
                            alert('Impossible de récupérer l\'historique de validation')
                            return
                          }
                          
                          const historyData = await historyResponse.json()
                          
                          if (!historyData.history || historyData.history.length === 0) {
                            alert('Aucun enregistrement de validation trouvé')
                            return
                          }
                          
                          const latestRecord = historyData.history[0] // Most recent record
                          
                          // Submit the override
                          const overrideResponse = await fetch(`${apiUrl}/api/siret/override`, {
                            method: 'POST',
                            headers: {
                              'Authorization': `Bearer ${token}`,
                              'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                              validation_record_id: latestRecord.id,
                              user_action: 'ignore_validation',
                              justification: justification.trim()
                            })
                          })
                          
                          if (overrideResponse.ok) {
                            const result = await overrideResponse.json()
                            alert(`Override appliqué avec succès. Export ${result.export_allowed ? 'autorisé' : 'bloqué'}.`)
                            
                            if (onValidationUpdate) {
                              onValidationUpdate()
                            }
                          } else {
                            const errorData = await overrideResponse.json()
                            alert(`Erreur lors de l'override: ${errorData.detail || 'Erreur inconnue'}`)
                          }
                        } catch (error) {
                          console.error('Override failed:', error)
                          alert(`Erreur lors de l'override: ${error.message}`)
                        }
                      }
                    }}
                  >
                    ⚠️ Ignorer
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}