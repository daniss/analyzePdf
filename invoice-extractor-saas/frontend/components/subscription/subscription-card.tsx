'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { SubscriptionInfo } from '@/lib/types'
import { useState } from 'react'
import { UpgradeModal } from './upgrade-modal'

interface SubscriptionCardProps {
  subscription: SubscriptionInfo | null | undefined
}

const tierConfig = {
  FREE: {
    name: 'Gratuit',
    color: 'bg-gray-500',
    description: 'Parfait pour découvrir ComptaFlow'
  },
  PRO: {
    name: 'Pro',
    color: 'bg-blue-500',
    description: 'Pour les cabinets en croissance'
  },
  BUSINESS: {
    name: 'Business',
    color: 'bg-purple-500',
    description: 'Pour les cabinets établis'
  },
  ENTERPRISE: {
    name: 'Enterprise',
    color: 'bg-gold-500',
    description: 'Pour les gros cabinets et fiduciaires'
  }
}

const statusConfig = {
  ACTIVE: { name: 'Actif', color: 'bg-green-500' },
  CANCELED: { name: 'Annulé', color: 'bg-red-500' },
  PAST_DUE: { name: 'En retard', color: 'bg-orange-500' },
  TRIALING: { name: 'Essai', color: 'bg-blue-500' },
  INCOMPLETE: { name: 'Incomplet', color: 'bg-yellow-500' }
}

export function SubscriptionCard({ subscription }: SubscriptionCardProps) {
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  
  // Safely get tier and status with fallbacks - handle both uppercase and lowercase
  const tierKey = subscription?.pricing_tier?.toUpperCase() as keyof typeof tierConfig
  const statusKey = subscription?.status?.toUpperCase() as keyof typeof statusConfig
  const tier = tierConfig[tierKey] || tierConfig.FREE
  const status = statusConfig[statusKey] || statusConfig.ACTIVE
  
  const usagePercentage = subscription ? Math.round(
    (subscription.monthly_invoices_processed / subscription.monthly_invoice_limit) * 100
  ) : 0

  const getRemainingDays = () => {
    if (!subscription?.current_period_end) return null
    const endDate = new Date(subscription.current_period_end)
    const now = new Date()
    const diffTime = endDate.getTime() - now.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays > 0 ? diffDays : 0
  }

  const remainingDays = getRemainingDays()

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Badge className={`${tier.color} text-white`}>
                {tier.name}
              </Badge>
              <Badge variant="outline" className={`${status.color} text-white border-0`}>
                {status.name}
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1">
              {tier.description}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {subscription?.pricing_tier !== 'ENTERPRISE' && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowUpgradeModal(true)}
              >
                {subscription?.pricing_tier === 'FREE' ? 'Passer Pro' : 'Évoluer'}
              </Button>
            )}
            {subscription?.pricing_tier !== 'FREE' && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setShowUpgradeModal(true)}
              >
                Gérer
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Quota Usage */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span>Factures traitées ce mois</span>
            <span className="font-medium">
              {subscription?.monthly_invoices_processed?.toLocaleString() || '0'} / {subscription?.monthly_invoice_limit?.toLocaleString() || '0'}
            </span>
          </div>
          <Progress 
            value={usagePercentage} 
            className="h-2"
          />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{usagePercentage}% utilisé</span>
            <span>
              {((subscription?.monthly_invoice_limit || 0) - (subscription?.monthly_invoices_processed || 0)).toLocaleString()} restantes
            </span>
          </div>
        </div>

        {/* Billing Information */}
        {subscription?.status === 'ACTIVE' && remainingDays !== null && (
          <div className="text-sm text-muted-foreground">
            <span>Période se terminant dans {remainingDays} jour{remainingDays !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* Usage Warning */}
        {usagePercentage >= 90 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <div className="text-sm text-orange-800">
              <strong>Attention :</strong> Vous approchez de votre limite mensuelle. 
              {subscription?.pricing_tier === 'FREE' && (
                <span className="block mt-1">
                  Passez au plan Pro pour traiter plus de factures.
                </span>
              )}
            </div>
          </div>
        )}

        {/* Upgrade CTA for Free users */}
        {subscription?.pricing_tier === 'FREE' && usagePercentage >= 70 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="text-sm text-blue-800">
              <strong>Évoluez vers Pro :</strong> Traitez jusqu'à 500 factures/mois avec des fonctionnalités avancées.
            </div>
            <Button size="sm" className="mt-2">
              Passer au Pro - 29€/mois
            </Button>
          </div>
        )}
      </CardContent>
      
      {showUpgradeModal && (
        <UpgradeModal 
          currentSubscription={subscription || undefined}
          onClose={() => setShowUpgradeModal(false)}
        />
      )}
    </Card>
  )
}