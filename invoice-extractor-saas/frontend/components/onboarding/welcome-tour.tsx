'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, Upload, FileText, Download, ArrowRight, X } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'

interface WelcomeTourProps {
  onComplete: () => void
}

const tourSteps = [
  {
    id: 1,
    title: 'Bienvenue sur ComptaFlow !',
    description: 'Votre plateforme d\'extraction intelligente de données de factures',
    content: (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-full">
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h4 className="font-medium">Extraction automatique</h4>
            <p className="text-sm text-muted-foreground">IA avancée pour extraire toutes les données importantes</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-full">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h4 className="font-medium">Validation française</h4>
            <p className="text-sm text-muted-foreground">Vérification SIRET, TVA et conformité fiscale</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-full">
            <Download className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h4 className="font-medium">Exports comptables</h4>
            <p className="text-sm text-muted-foreground">Sage, EBP, Ciel, FEC - compatibilité totale</p>
          </div>
        </div>
      </div>
    )
  },
  {
    id: 2,
    title: 'Votre plan actuel',
    description: 'Découvrez ce qui est inclus dans votre abonnement',
    content: (
      <div className="space-y-4">
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">Plan Gratuit</h4>
            <Badge variant="outline">Actuel</Badge>
          </div>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              10 factures par mois
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Extraction automatique de données
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Export CSV basique
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              Support communautaire
            </li>
          </ul>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <h4 className="font-medium text-blue-900 mb-1">Envie de plus ?</h4>
          <p className="text-sm text-blue-800 mb-3">
            Le plan Pro débloque 500 factures/mois, la validation SIRET avancée, 
            et les exports vers tous les logiciels comptables français.
          </p>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
            Découvrir le plan Pro
          </Button>
        </div>
      </div>
    )
  },
  {
    id: 3,
    title: 'Comment ça marche',
    description: 'En 3 étapes simples, transformez vos factures en données comptables',
    content: (
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-blue-600">1</span>
          </div>
          <div>
            <h4 className="font-medium">Importez vos factures</h4>
            <p className="text-sm text-muted-foreground">
              Glissez-déposez vos PDF ou images de factures. 
              Formats supportés : PDF, JPG, PNG
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-green-600">2</span>
          </div>
          <div>
            <h4 className="font-medium">Vérifiez les données extraites</h4>
            <p className="text-sm text-muted-foreground">
              Notre IA extrait automatiquement toutes les informations. 
              Vous pouvez réviser et corriger si nécessaire.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-purple-600">3</span>
          </div>
          <div>
            <h4 className="font-medium">Exportez vers votre logiciel</h4>
            <p className="text-sm text-muted-foreground">
              Téléchargez au format de votre choix et importez 
              directement dans votre logiciel comptable.
            </p>
          </div>
        </div>
      </div>
    )
  },
  {
    id: 4,
    title: 'Prêt à commencer !',
    description: 'Vous avez tout ce qu\'il faut pour traiter votre première facture',
    content: (
      <div className="space-y-4 text-center">
        <div className="p-6 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg">
          <Upload className="h-12 w-12 text-blue-600 mx-auto mb-3" />
          <h4 className="font-medium mb-2">Importez votre première facture</h4>
          <p className="text-sm text-muted-foreground mb-4">
            Testez la puissance de ComptaFlow dès maintenant avec une facture de démonstration.
          </p>
          <Button>
            Commencer l'extraction
          </Button>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <h4 className="font-medium text-green-900 mb-1">✅ Conformité RGPD garantie</h4>
          <p className="text-sm text-green-800">
            Vos données sont chiffrées et traitées en France. 
            Nous respectons toutes les réglementations européennes.
          </p>
        </div>
      </div>
    )
  }
]

export function WelcomeTour({ onComplete }: WelcomeTourProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isVisible, setIsVisible] = useState(false)
  const { user } = useAuth()

  useEffect(() => {
    // Check if user has seen the tour before
    const hasSeenTour = localStorage.getItem('comptaflow_tour_completed')
    if (!hasSeenTour && user) {
      setIsVisible(true)
    }
  }, [user])

  const nextStep = () => {
    if (currentStep < tourSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      completeTour()
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const completeTour = () => {
    localStorage.setItem('comptaflow_tour_completed', 'true')
    setIsVisible(false)
    onComplete()
  }

  const skipTour = () => {
    localStorage.setItem('comptaflow_tour_completed', 'true')
    setIsVisible(false)
    onComplete()
  }

  if (!isVisible) return null

  const step = tourSteps[currentStep]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex space-x-1">
                {tourSteps.map((_, index) => (
                  <div
                    key={index}
                    className={`w-2 h-2 rounded-full ${
                      index === currentStep ? 'bg-blue-600' : 
                      index < currentStep ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  />
                ))}
              </div>
              <span className="text-sm text-muted-foreground">
                {currentStep + 1} / {tourSteps.length}
              </span>
            </div>
            <Button variant="ghost" size="sm" onClick={skipTour}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <CardTitle>{step.title}</CardTitle>
          <CardDescription>{step.description}</CardDescription>
        </CardHeader>
        
        <CardContent>
          <div className="mb-6">
            {step.content}
          </div>
          
          <div className="flex justify-between">
            <Button 
              variant="outline" 
              onClick={prevStep}
              disabled={currentStep === 0}
            >
              Précédent
            </Button>
            
            <div className="flex gap-2">
              <Button variant="ghost" onClick={skipTour}>
                Passer
              </Button>
              <Button onClick={nextStep}>
                {currentStep === tourSteps.length - 1 ? 'Commencer' : 'Suivant'}
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}