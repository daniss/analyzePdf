'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Check, Crown, Zap, Shield, X } from 'lucide-react'
import { SubscriptionInfo } from '@/lib/types'
import toast from 'react-hot-toast'

interface UpgradeModalProps {
  currentSubscription?: SubscriptionInfo
  onClose: () => void
}

const pricingTiers = [
  {
    tier: 'FREE',
    name: 'Gratuit',
    price: 0,
    description: 'Parfait pour découvrir ComptaFlow',
    invoiceLimit: 10,
    features: [
      'Extraction automatique de données',
      'Export CSV basique',
      'Support communautaire',
      '10 factures/mois'
    ],
    icon: Shield,
    color: 'bg-gray-500',
    popular: false
  },
  {
    tier: 'PRO',
    name: 'Pro',
    price: 29,
    description: 'Pour les cabinets en croissance',
    invoiceLimit: 500,
    features: [
      'Tout du plan Gratuit',
      'Validation SIRET/SIREN avancée',
      'Exports comptables (Sage, EBP, Ciel)',
      'Support prioritaire',
      'Traitement par lots',
      '500 factures/mois'
    ],
    icon: Zap,
    color: 'bg-blue-500',
    popular: true
  },
  {
    tier: 'BUSINESS',
    name: 'Business',
    price: 59,
    description: 'Pour les cabinets établis',
    invoiceLimit: 2000,
    features: [
      'Tout du plan Pro',
      'Accès API complet',
      'Formats d\'export personnalisés',
      'Validation avancée des TVA',
      'Intégration directe logiciels comptables',
      '2000 factures/mois'
    ],
    icon: Crown,
    color: 'bg-purple-500',
    popular: false
  },
  {
    tier: 'ENTERPRISE',
    name: 'Enterprise',
    price: 99,
    description: 'Pour les gros cabinets et fiduciaires',
    invoiceLimit: 10000,
    features: [
      'Tout du plan Business',
      'Factures illimitées',
      'SLA garanti 99.9%',
      'Support dédié',
      'Formation personnalisée',
      'Conformité audit avancée'
    ],
    icon: Crown,
    color: 'bg-gold-500',
    popular: false
  }
]

export function UpgradeModal({ currentSubscription, onClose }: UpgradeModalProps) {
  const [loading, setLoading] = useState<string | null>(null)

  const handleUpgrade = async (tier: string) => {
    if (tier === 'FREE' || tier === currentSubscription?.pricing_tier) {
      return
    }

    setLoading(tier)
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1]

      if (!token) {
        toast.error('Token d\'authentification introuvable')
        return
      }

      const response = await fetch(`${apiUrl}/api/payments/create-checkout-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          pricing_tier: tier,
          success_url: `${window.location.origin}/dashboard?payment=success`,
          cancel_url: `${window.location.origin}/dashboard?payment=cancelled`
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail?.error || data.detail || 'Erreur lors de la création de la session de paiement')
      }

      // Redirect to Stripe checkout
      window.location.href = data.checkout_url

    } catch (error) {
      console.error('Upgrade error:', error)
      toast.error(error instanceof Error ? error.message : 'Erreur lors de la mise à niveau')
    } finally {
      setLoading(null)
    }
  }

  const handleManageSubscription = async () => {
    if (!currentSubscription || currentSubscription.pricing_tier === 'FREE') {
      return
    }

    setLoading('manage')
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1]

      if (!token) {
        toast.error('Token d\'authentification introuvable')
        return
      }

      const response = await fetch(`${apiUrl}/api/payments/create-portal-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          return_url: `${window.location.origin}/dashboard`
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail?.error || data.detail || 'Erreur lors de l\'accès au portail')
      }

      // Redirect to Stripe customer portal
      window.location.href = data.portal_url

    } catch (error) {
      console.error('Portal error:', error)
      toast.error(error instanceof Error ? error.message : 'Erreur lors de l\'accès au portail client')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-7xl w-full max-h-[95vh] flex flex-col">
        <div className="flex justify-between items-start p-4 border-b">
          <div className="flex-1">
            <h2 className="text-xl font-bold">Choisir votre plan</h2>
            <p className="text-sm text-muted-foreground">Évoluez selon vos besoins de traitement de factures</p>
            {currentSubscription && (
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline" className="text-xs">
                  Plan actuel: {pricingTiers.find(t => t.tier.toUpperCase() === currentSubscription.pricing_tier?.toUpperCase())?.name || currentSubscription.pricing_tier}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {currentSubscription.monthly_invoices_processed || 0} / {currentSubscription.monthly_invoice_limit || 0} factures
                </Badge>
              </div>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {pricingTiers.map((tier) => {
              const Icon = tier.icon
              const isCurrentTier = currentSubscription?.pricing_tier?.toUpperCase() === tier.tier.toUpperCase()
              const isDowngrade = currentSubscription && 
                pricingTiers.findIndex(t => t.tier.toUpperCase() === currentSubscription.pricing_tier?.toUpperCase()) > 
                pricingTiers.findIndex(t => t.tier === tier.tier)

              return (
                <Card key={tier.tier} className={`relative transition-all duration-200 ${
                  isCurrentTier 
                    ? 'border-green-500 shadow-lg ring-2 ring-green-200 bg-green-50/50' 
                    : tier.popular 
                      ? 'border-blue-500 shadow-lg' 
                      : 'hover:shadow-md'
                }`}>
                  {isCurrentTier && (
                    <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-green-500 text-white">✓ Plan Actuel</Badge>
                    </div>
                  )}
                  {tier.popular && !isCurrentTier && (
                    <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-blue-500 text-white">Le Plus Populaire</Badge>
                    </div>
                  )}
                  
                  <CardHeader className="text-center pb-3">
                    <div className="flex justify-center mb-2">
                      <div className={`p-2 rounded-full ${tier.color} text-white`}>
                        <Icon className="h-5 w-5" />
                      </div>
                    </div>
                    <CardTitle className="text-lg">
                      {tier.name}
                    </CardTitle>
                    <CardDescription className="text-xs">{tier.description}</CardDescription>
                    <div className="text-2xl font-bold">
                      {tier.price === 0 ? 'Gratuit' : `${tier.price}€`}
                      {tier.price > 0 && <span className="text-xs font-normal text-muted-foreground">/mois</span>}
                    </div>
                  </CardHeader>

                  <CardContent className="pt-0">
                    <ul className="space-y-1 mb-4">
                      {tier.features.map((feature, index) => (
                        <li key={index} className="flex items-start gap-2 text-xs">
                          <Check className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>

                    {isCurrentTier ? (
                      <div className="space-y-2">
                        {currentSubscription && (
                          <div className="bg-green-50 border border-green-200 rounded-md p-2">
                            <div className="text-xs text-green-800 text-center">
                              <div className="font-medium">Utilisation</div>
                              <div className="text-sm font-bold">
                                {currentSubscription.monthly_invoices_processed || 0} / {currentSubscription.monthly_invoice_limit || 0}
                              </div>
                              <div className="text-xs text-green-600">
                                {Math.round(((currentSubscription.monthly_invoices_processed || 0) / (currentSubscription.monthly_invoice_limit || 1)) * 100)}% utilisé
                              </div>
                            </div>
                          </div>
                        )}
                        <Button 
                          variant="outline" 
                          className="w-full border-green-500 text-green-700 hover:bg-green-50" 
                          size="sm"
                          disabled
                        >
                          ✓ Plan Actuel
                        </Button>
                        {tier.tier !== 'FREE' && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="w-full text-xs"
                            onClick={handleManageSubscription}
                            disabled={loading === 'manage'}
                          >
                            {loading === 'manage' ? 'Chargement...' : 'Gérer l\'abonnement'}
                          </Button>
                        )}
                      </div>
                    ) : tier.tier === 'FREE' ? (
                      <Button 
                        variant="outline" 
                        className="w-full" 
                        disabled
                      >
                        Plan de Base
                      </Button>
                    ) : (
                      <Button 
                        className={`w-full ${tier.popular ? 'bg-blue-500 hover:bg-blue-600' : ''}`}
                        variant={tier.popular ? 'default' : 'outline'}
                        onClick={() => handleUpgrade(tier.tier)}
                        disabled={loading === tier.tier || isDowngrade}
                      >
                        {loading === tier.tier ? 'Chargement...' : 
                         isDowngrade ? 'Rétrogradation non disponible' : 
                         'Passer à ce plan'}
                      </Button>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            <p>✅ Tous les plans incluent le chiffrement des données et la conformité RGPD</p>
            <p>✅ Annulation possible à tout moment • 🇫🇷 Support en français</p>
          </div>
        </div>
      </div>
    </div>
  )
}