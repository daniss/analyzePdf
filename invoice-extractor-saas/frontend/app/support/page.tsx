'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  MessageCircle, 
  Mail, 
  Phone, 
  FileText, 
  HelpCircle, 
  CheckCircle,
  Clock,
  Users,
  Zap
} from 'lucide-react'
import toast from 'react-hot-toast'

const supportCategories = [
  {
    id: 'technical',
    name: 'Problème Technique',
    description: 'Erreurs, bugs, problèmes de traitement',
    icon: Zap,
    color: 'bg-red-100 text-red-600'
  },
  {
    id: 'billing',
    name: 'Facturation & Abonnement',
    description: 'Questions sur votre plan, paiements',
    icon: FileText,
    color: 'bg-blue-100 text-blue-600'
  },
  {
    id: 'feature',
    name: 'Demande de Fonctionnalité',
    description: 'Suggestions d\'améliorations',
    icon: HelpCircle,
    color: 'bg-purple-100 text-purple-600'
  },
  {
    id: 'general',
    name: 'Question Générale',
    description: 'Aide générale, comment faire',
    icon: MessageCircle,
    color: 'bg-green-100 text-green-600'
  }
]

const faqData = [
  {
    question: 'Comment fonctionne l\'extraction de données ?',
    answer: 'Notre IA analyse vos factures PDF et images pour extraire automatiquement les informations importantes : montants, dates, données fournisseur, SIRET, etc. Les données sont ensuite validées selon les standards français.'
  },
  {
    question: 'Quels formats de fichiers sont supportés ?',
    answer: 'ComptaFlow accepte les fichiers PDF, JPG, PNG et autres formats d\'images couramment utilisés pour les factures. Taille maximum : 10 MB par fichier.'
  },
  {
    question: 'Les données sont-elles sécurisées ?',
    answer: 'Oui, toutes les données sont chiffrées (AES-256) et traitées en conformité RGPD. Les fichiers sont traités en mémoire uniquement, sans stockage permanent non chiffré.'
  },
  {
    question: 'Comment changer de plan d\'abonnement ?',
    answer: 'Rendez-vous dans votre tableau de bord, section "Abonnement", puis cliquez sur "Gérer l\'abonnement" pour accéder au portail Stripe et modifier votre plan.'
  },
  {
    question: 'Puis-je exporter vers mon logiciel comptable ?',
    answer: 'Oui, ComptaFlow supporte les formats d\'export pour Sage, EBP, Ciel, ainsi que le format FEC pour l\'administration fiscale et les exports CSV personnalisables.'
  },
  {
    question: 'Que faire si l\'extraction n\'est pas correcte ?',
    answer: 'Utilisez l\'interface de révision des données pour corriger les informations extraites. Vos corrections améliorent également notre IA pour les futures extractions.'
  }
]

export default function SupportPage() {
  const [selectedCategory, setSelectedCategory] = useState('')
  const [formData, setFormData] = useState({
    subject: '',
    description: '',
    priority: 'normal'
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedCategory || !formData.subject || !formData.description) {
      toast.error('Veuillez remplir tous les champs requis')
      return
    }

    setIsSubmitting(true)

    try {
      // In a real implementation, this would send to a support system
      // For now, we'll simulate the request
      await new Promise(resolve => setTimeout(resolve, 2000))

      toast.success('Votre demande de support a été envoyée avec succès !')
      
      // Reset form
      setSelectedCategory('')
      setFormData({
        subject: '',
        description: '',
        priority: 'normal'
      })
    } catch (error) {
      toast.error('Erreur lors de l\'envoi de votre demande')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Centre d'Aide & Support</h1>
        <p className="text-muted-foreground">
          Nous sommes là pour vous aider avec ComptaFlow
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Support Contact */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Contacter le Support</CardTitle>
              <CardDescription>
                Décrivez votre problème et nous vous aiderons rapidement
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Category Selection */}
                <div>
                  <label className="text-sm font-medium mb-3 block">
                    Type de demande *
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {supportCategories.map((category) => {
                      const Icon = category.icon
                      return (
                        <button
                          key={category.id}
                          type="button"
                          onClick={() => setSelectedCategory(category.id)}
                          className={`p-4 rounded-lg border text-left transition-colors ${
                            selectedCategory === category.id
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded-full ${category.color}`}>
                              <Icon className="h-4 w-4" />
                            </div>
                            <div>
                              <h4 className="font-medium text-sm">{category.name}</h4>
                              <p className="text-xs text-muted-foreground mt-1">
                                {category.description}
                              </p>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Subject */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Sujet *
                  </label>
                  <Input
                    value={formData.subject}
                    onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
                    placeholder="Résumez votre problème en quelques mots"
                    required
                  />
                </div>

                {/* Priority */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Priorité
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value }))}
                    className="w-full p-2 border border-gray-200 rounded-md"
                  >
                    <option value="low">Faible</option>
                    <option value="normal">Normale</option>
                    <option value="high">Élevée</option>
                    <option value="urgent">Urgente</option>
                  </select>
                </div>

                {/* Description */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Description détaillée *
                  </label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Décrivez votre problème en détail : que s'est-il passé ? Quelles étaient vos attentes ?"
                    rows={6}
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Plus vous donnez de détails, plus nous pourrons vous aider efficacement.
                  </p>
                </div>

                <Button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="w-full"
                >
                  {isSubmitting ? 'Envoi en cours...' : 'Envoyer la demande'}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* FAQ */}
          <Card>
            <CardHeader>
              <CardTitle>Questions Fréquentes</CardTitle>
              <CardDescription>
                Trouvez rapidement des réponses aux questions les plus courantes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {faqData.map((faq, index) => (
                  <details key={index} className="border border-gray-200 rounded-lg">
                    <summary className="p-4 cursor-pointer hover:bg-gray-50 font-medium">
                      {faq.question}
                    </summary>
                    <div className="p-4 pt-0 text-sm text-muted-foreground">
                      {faq.answer}
                    </div>
                  </details>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Contact Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Informations de Contact</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="font-medium">Email</p>
                  <p className="text-sm text-muted-foreground">support@comptaflow.fr</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-medium">Téléphone</p>
                  <p className="text-sm text-muted-foreground">+33 (0)1 XX XX XX XX</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Clock className="h-5 w-5 text-purple-600" />
                <div>
                  <p className="font-medium">Horaires</p>
                  <p className="text-sm text-muted-foreground">
                    Lun-Ven : 9h-18h<br />
                    Support technique 24/7
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Response Times */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Temps de Réponse</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Plan Gratuit</span>
                <Badge variant="outline">24-48h</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Plan Pro</span>
                <Badge className="bg-blue-500">12-24h</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Plan Business</span>
                <Badge className="bg-purple-500">4-8h</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Plan Enterprise</span>
                <Badge className="bg-gold-500">1-4h</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">État du Service</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Tous les services opérationnels</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Dernière vérification : il y a 2 minutes
              </p>
            </CardContent>
          </Card>

          {/* Resources */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Ressources Utiles</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button variant="outline" className="w-full justify-start">
                <FileText className="h-4 w-4 mr-2" />
                Guide d'Utilisation
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <Users className="h-4 w-4 mr-2" />
                Communauté
              </Button>
              <Button variant="outline" className="w-full justify-start">
                <MessageCircle className="h-4 w-4 mr-2" />
                Base de Connaissances
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}