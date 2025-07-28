'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, FileText, Bot, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useAuth, withAuth } from '@/lib/auth-context'
import { DataReviewTable } from '@/components/invoice/data-review-table'
import { apiClient } from '@/lib/api'
import { Invoice } from '@/lib/types'
import toast from 'react-hot-toast'

function InvoiceReviewPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const invoiceId = params.id as string

  useEffect(() => {
    const fetchInvoice = async () => {
      try {
        setIsLoading(true)
        const fetchedInvoice = await apiClient.getInvoice(invoiceId)
        setInvoice(fetchedInvoice)
      } catch (err) {
        console.error('Failed to fetch invoice:', err)
        setError('Impossible de charger la facture. Veuillez réessayer.')
      } finally {
        setIsLoading(false)
      }
    }

    if (invoiceId) {
      fetchInvoice()
    }
  }, [invoiceId])

  const handleInvoiceUpdate = (updatedInvoice: Invoice) => {
    setInvoice(updatedInvoice)
    // Also invalidate the invoices cache so dashboard shows updated data
    queryClient.invalidateQueries({ queryKey: ['invoices'] })
  }

  const navigateToDashboard = async () => {
    // Invalidate invoices cache to ensure fresh data on dashboard
    await queryClient.invalidateQueries({ queryKey: ['invoices'] })
    router.push('/dashboard')
  }

  const handleApprove = async () => {
    try {
      // Update invoice status to approved
      await apiClient.updateInvoiceReviewStatus(invoiceId, 'approved')
      
      // Invalidate invoices cache to refresh dashboard data
      await queryClient.invalidateQueries({ queryKey: ['invoices'] })
      
      // Show success message
      toast.success('Facture approuvée avec succès')
      
      // Navigate back to dashboard
      navigateToDashboard()
    } catch (error) {
      console.error('Failed to approve invoice:', error)
      toast.error('Erreur lors de l\'approbation de la facture')
    }
  }

  const handleReject = async () => {
    try {
      // Update invoice status to rejected
      await apiClient.updateInvoiceReviewStatus(invoiceId, 'rejected')
      
      // Invalidate invoices cache to refresh dashboard data
      await queryClient.invalidateQueries({ queryKey: ['invoices'] })
      
      // Show success message
      toast.success('Facture rejetée')
      
      // Navigate back to dashboard
      navigateToDashboard()
    } catch (error) {
      console.error('Failed to reject invoice:', error)
      toast.error('Erreur lors du rejet de la facture')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background gradient-mesh">
        <div className="container py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Chargement des données de révision...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !invoice) {
    return (
      <div className="min-h-screen bg-background gradient-mesh">
        <div className="container py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <Card className="w-full max-w-md">
              <CardContent className="pt-6 text-center">
                <div className="text-red-500 mb-4">
                  <FileText className="h-12 w-12 mx-auto" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Erreur de Chargement</h3>
                <p className="text-muted-foreground mb-4">
                  {error || 'Facture introuvable'}
                </p>
                <Button onClick={() => navigateToDashboard()} variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Retour au Tableau de Bord
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  if (invoice.status !== 'completed') {
    return (
      <div className="min-h-screen bg-background gradient-mesh">
        <div className="container py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <Card className="w-full max-w-md">
              <CardContent className="pt-6 text-center">
                <div className="text-yellow-500 mb-4">
                  <Bot className="h-12 w-12 mx-auto" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Traitement en Cours</h3>
                <p className="text-muted-foreground mb-4">
                  Cette facture est encore en cours de traitement. Veuillez patienter.
                </p>
                <Button onClick={() => navigateToDashboard()} variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Retour au Tableau de Bord
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background gradient-mesh">
      {/* Header */}
      <header className="glass border-b border-white/10 sticky top-0 z-40">
        <div className="container flex h-20 items-center px-4">
          <div className="flex items-center space-x-3">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => navigateToDashboard()}
              className="mr-4"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour
            </Button>
            <div className="relative">
              <div className="absolute inset-0 gradient-primary rounded-lg blur opacity-75"></div>
              <div className="relative bg-white rounded-lg p-1.5">
                <FileText className="h-6 w-6 text-primary" />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold">Révision des Données</h1>
              <p className="text-sm text-muted-foreground">{invoice.filename}</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted-foreground">
                {user.email}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="container py-8">
        {/* Invoice Overview */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-2xl mb-2">Aperçu de la Facture</CardTitle>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>📄 {invoice.filename}</span>
                  <span>📅 {new Date(invoice.created_at).toLocaleDateString('fr-FR')}</span>
                  <span>🤖 Traité automatiquement</span>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {invoice.review_status === 'pending_review' && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-100 text-yellow-700 text-sm">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    En Attente de Révision
                  </div>
                )}
                {invoice.review_status === 'in_review' && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    En Cours de Révision
                  </div>
                )}
                {invoice.review_status === 'approved' && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 text-green-700 text-sm">
                    <CheckCircle className="w-4 h-4" />
                    Approuvé
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
          
          {invoice.data && (
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-primary">
                    €{(invoice.data.total_ttc || invoice.data.total || 0).toLocaleString('fr-FR')}
                  </div>
                  <div className="text-sm text-muted-foreground">Montant Total TTC</div>
                </div>
                
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-xl font-semibold">
                    {invoice.data.vendor?.name || invoice.data.vendor_name || 'N/A'}
                  </div>
                  <div className="text-sm text-muted-foreground">Fournisseur</div>
                </div>
                
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-xl font-semibold">
                    {invoice.data.invoice_number || 'N/A'}
                  </div>
                  <div className="text-sm text-muted-foreground">N° Facture</div>
                </div>
              </div>
            </CardContent>
          )}
        </Card>

        <Separator className="my-8" />

        {/* Data Review Table */}
        <DataReviewTable
          invoice={invoice}
          onUpdate={handleInvoiceUpdate}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      </main>
    </div>
  )
}

export default withAuth(InvoiceReviewPage)