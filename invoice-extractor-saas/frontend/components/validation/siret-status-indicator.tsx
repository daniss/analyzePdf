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

// French translation functions for SIRET validation
const translateStatus = (status: string): string => {
  const translations: Record<string, string> = {
    'valid': 'Valide',
    'not_found': 'Non trouvé',
    'inactive': 'Inactif',
    'name_mismatch': 'Nom divergent',
    'malformed': 'Format invalide',
    'foreign': 'Fournisseur étranger',
    'government': 'Entité gouvernementale',
    'error': 'Erreur technique'
  }
  return translations[status] || status
}

const translateBlockingLevel = (level: string): string => {
  const translations: Record<string, string> = {
    'auto_allowed': 'Export automatique autorisé',
    'warning': 'Confirmation requise',
    'warning_allowed': 'Export autorisé avec avertissement',
    'blocked_override': 'Bloqué - override possible',
    'blocked_correction': 'Bloqué - correction requise'
  }
  return translations[level] || level
}

const translateRisk = (risk: string): string => {
  const translations: Record<string, string> = {
    'low': 'Faible',
    'medium': 'Moyen',
    'high': 'Élevé',
    'critical': 'Critique'
  }
  return translations[risk] || risk
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
    if (overall.requires_user_action) return 'SIRET Non Valide'
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
            {translateRisk(overall.highest_risk)}
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
              <span>{translateStatus(vendor.status)}</span>
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
              <span>{translateStatus(customer.status)}</span>
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

      {/* SIRET validation warning */}
      {overall.requires_user_action && !overall.any_export_blocked && (
        <div className="flex items-center gap-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs">
          <AlertTriangle className="h-3 w-3 text-orange-500" />
          <span className="text-orange-700 font-medium">SIRET non valide - export autorisé avec avertissement</span>
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
                  <div>Statut: <span className="font-medium">{translateStatus(vendor.status)}</span></div>
                  <div>Niveau de blocage: <span className="font-medium">{translateBlockingLevel(vendor.blocking_level)}</span></div>
                  <div>Risque: <span className="font-medium">{translateRisk(vendor.compliance_risk)}</span></div>
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
                  <div>Statut: <span className="font-medium">{translateStatus(customer.status)}</span></div>
                  <div>Niveau de blocage: <span className="font-medium">{translateBlockingLevel(customer.blocking_level)}</span></div>
                  <div>Risque: <span className="font-medium">{translateRisk(customer.compliance_risk)}</span></div>
                  {customer.french_error_message && (
                    <div className="text-red-600">⚠️ {customer.french_error_message}</div>
                  )}
                  {customer.user_options_available && (
                    <div className="text-blue-600">💡 Actions utilisateur disponibles</div>
                  )}
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  )
}