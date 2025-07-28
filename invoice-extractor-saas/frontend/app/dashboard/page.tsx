'use client'

import { useAuth, withAuth } from '@/lib/auth-context'
import { useInvoices, useDashboardStats } from '@/lib/hooks'
import { ProgressiveInvoiceCard } from '@/components/invoice/progressive-invoice-card'
import { BatchUpload } from '@/components/invoice/batch-upload'
import { BulkExportSelector } from '@/components/invoice/bulk-export-selector'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Download, DollarSign, Bot, Zap, TrendingUp, Clock, Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'

function DashboardPage() {
  const { user, logout } = useAuth()
  const { data: invoices = [], isLoading, error, refetch } = useInvoices()
  const { data: statsData } = useDashboardStats()

  const handleUpload = () => {
    // Refetch invoices to get the latest data
    refetch()
  }

  const handleApproveAll = async () => {
    const pendingInvoices = invoices.filter(invoice => 
      invoice.status === 'completed' && 
      invoice.processing_source === 'batch' &&
      (!invoice.review_status || invoice.review_status === 'pending_review')
    )

    if (pendingInvoices.length === 0) return

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

      // Approve all pending invoices
      const approvalPromises = pendingInvoices.map(invoice => 
        fetch(`${apiUrl}/api/invoices/${invoice.id}/review-status`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ status: 'approved' })
        })
      )

      const results = await Promise.all(approvalPromises)
      const successCount = results.filter(response => response.ok).length

      if (successCount === pendingInvoices.length) {
        toast.success(`${successCount} facture${successCount > 1 ? 's' : ''} approuvée${successCount > 1 ? 's' : ''} avec succès`)
      } else {
        toast.error(`${successCount}/${pendingInvoices.length} factures approuvées. Certaines ont échoué.`)
      }

      // Refresh the invoice list
      refetch()
    } catch (error) {
      console.error('Error approving all invoices:', error)
      toast.error('Erreur lors de l\'approbation des factures')
    }
  }

  const handleRemoveFromExport = async (invoiceId: string) => {
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

      // Reset invoice status from approved back to reviewed/pending
      const response = await fetch(`${apiUrl}/api/invoices/${invoiceId}/review-status`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: 'reviewed' })
      })

      if (response.ok) {
        // Refresh the invoice list
        refetch()
      } else {
        toast.error('Erreur lors de la suppression de la file d\'export')
      }
    } catch (error) {
      console.error('Error removing from export:', error)
      toast.error('Erreur lors de la suppression de la file d\'export')
    }
  }


  const pendingReviewCount = invoices.filter(invoice => 
    invoice.status === 'completed' && 
    invoice.processing_source === 'batch' &&
    (!invoice.review_status || invoice.review_status === 'pending_review')
  ).length


  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background gradient-mesh">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Chargement de votre tableau de bord...</p>
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
            <div className="relative">
              <div className="absolute inset-0 gradient-primary rounded-lg blur opacity-75"></div>
              <div className="relative bg-white rounded-lg p-1.5">
                <Bot className="h-6 w-6 text-primary" />
              </div>
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
              FacturePro
            </h1>
          </div>
          <div className="ml-auto flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted-foreground">
                Bienvenue, {user.email}
              </span>
            )}
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-muted-foreground hover:text-foreground"
              onClick={logout}
            >
              Déconnexion
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-8">
        {/* Welcome Section */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-2">Bon retour !</h2>
          <p className="text-lg text-muted-foreground">Transformez vos factures avec l'extraction intelligente</p>
        </div>


        {/* Compact Stats */}
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-5 mb-6">
          <Card className="card-modern p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">{statsData?.total_invoices || 0}</div>
                <div className="text-xs text-muted-foreground">Total</div>
              </div>
              <FileText className="h-4 w-4 text-primary" />
            </div>
          </Card>

          <Card className="card-modern p-3 border-orange-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold text-orange-600">{pendingReviewCount}</div>
                <div className="text-xs text-muted-foreground">En Attente</div>
              </div>
              <Clock className="h-4 w-4 text-orange-600" />
            </div>
          </Card>
          
          <Card className="card-modern p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">€{(statsData?.total_amount || 0).toLocaleString('fr-FR')}</div>
                <div className="text-xs text-muted-foreground">Montant</div>
              </div>
              <DollarSign className="h-4 w-4 text-green-600" />
            </div>
          </Card>
          
          <Card className="card-modern p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">
                  {statsData?.average_processing_time 
                    ? `${statsData.average_processing_time.toFixed(1)}s`
                    : '~10s'
                  }
                </div>
                <div className="text-xs text-muted-foreground">Moyenne</div>
              </div>
              <Zap className="h-4 w-4 text-orange-600" />
            </div>
          </Card>
          
          <Card className="card-modern p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">
                  {statsData?.time_savings_percentage 
                    ? `${statsData.time_savings_percentage}%`
                    : '~85%'
                  }
                </div>
                <div className="text-xs text-muted-foreground">Économies</div>
              </div>
              <TrendingUp className="h-4 w-4 text-purple-600" />
            </div>
          </Card>
        </div>

        {/* Error State */}
        {error && (
          <Card className="card-modern mb-12 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 text-red-700">
                <TrendingUp className="h-5 w-5" />
                <p>Échec du chargement des données du tableau de bord. Veuillez actualiser la page.</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => refetch()}
                  className="ml-auto"
                >
                  Réessayer
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Batch Upload Section */}
        <Card className="card-modern mb-12 overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 gradient-primary"></div>
          <CardHeader className="pb-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl mb-2">Traitement par Lots</CardTitle>
                <CardDescription className="text-lg">
                  Téléversez plusieurs factures et obtenez vos données exportées en une étape
                </CardDescription>
              </div>
              <div className="hidden md:flex items-center gap-2">
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-green-100 text-sm font-medium text-green-700">
                  <Zap className="h-4 w-4" />
                  Traitement Intelligent
                </div>
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 text-sm font-medium text-blue-700">
                  <Download className="h-4 w-4" />
                  Export Automatique
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <BatchUpload onComplete={handleUpload} />
          </CardContent>
        </Card>

        
        {/* Pending Review Section */}
        {(() => {
          const pendingInvoices = invoices.filter(invoice => 
            invoice.status === 'completed' && 
            invoice.processing_source === 'batch' &&
            (!invoice.review_status || invoice.review_status === 'pending_review')
          )
          
          if (pendingInvoices.length > 0) {
            return (
              <Card className="card-modern mb-12 border-orange-200 bg-orange-50/30">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-orange-400 to-yellow-500"></div>
                <CardHeader className="pb-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-2xl mb-2 flex items-center gap-2">
                        <Clock className="h-6 w-6 text-orange-600" />
                        Factures en Attente de Révision
                      </CardTitle>
                      <CardDescription className="text-lg">
                        {pendingInvoices.length} facture{pendingInvoices.length > 1 ? 's' : ''} prête{pendingInvoices.length > 1 ? 's' : ''} à réviser avant export
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-orange-100 text-orange-700">
                        <Clock className="h-4 w-4" />
                        Action requise
                      </div>
                      <Button
                        onClick={handleApproveAll}
                        size="sm"
                        className="bg-green-600 hover:bg-green-700 text-white"
                      >
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Approuver Tout
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {pendingInvoices.slice(0, 5).map((invoice) => (
                      <ProgressiveInvoiceCard
                        key={invoice.id}
                        invoice={invoice}
                        onUpdate={() => {
                          refetch()
                        }}
                        expanded={false}
                      />
                    ))}
                  </div>
                  
                  {pendingInvoices.length > 5 && (
                    <div className="mt-6 text-center">
                      <p className="text-sm text-muted-foreground mb-3">
                        Affichage de 5 sur {pendingInvoices.length} factures en attente
                      </p>
                      <Button variant="outline" size="sm">
                        Voir Toutes les Factures en Attente
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          }
          return null
        })()}

        {/* Approved Invoices Ready for Export */}
        {(() => {
          const approvedInvoices = invoices.filter(invoice => 
            invoice.status === 'completed' && 
            invoice.review_status === 'approved'
          )
          
          if (approvedInvoices.length > 0) {
            return (
              <Card className="card-modern mb-12 border-green-200 bg-green-50/30">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-green-400 to-blue-500"></div>
                <CardHeader className="pb-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-2xl mb-2 flex items-center gap-2">
                        <Download className="h-6 w-6 text-green-600" />
                        Factures Approuvées - Prêtes pour Export
                      </CardTitle>
                      <CardDescription className="text-lg">
                        {approvedInvoices.length} facture{approvedInvoices.length > 1 ? 's' : ''} approuvée{approvedInvoices.length > 1 ? 's' : ''} et disponible{approvedInvoices.length > 1 ? 's' : ''} pour export
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <BulkExportSelector
                        invoiceIds={approvedInvoices.map(inv => inv.id)}
                        onExportComplete={(format, success) => {
                          if (success) {
                            console.log(`Bulk export ${format} completed successfully`)
                            // Refresh invoice list to reflect cleared approved status
                            refetch()
                          }
                        }}
                      />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {approvedInvoices.slice(0, 3).map((invoice) => (
                      <div key={invoice.id} className="relative">
                        <ProgressiveInvoiceCard
                          invoice={invoice}
                          onUpdate={() => {
                            refetch()
                          }}
                          expanded={false}
                          showReviewButton={false}
                        />
                        <button
                          onClick={() => handleRemoveFromExport(invoice.id)}
                          className="absolute top-2 right-2 p-1 rounded-full bg-red-100 hover:bg-red-200 text-red-600 transition-colors"
                          title="Retirer de la file d'export"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                  
                  {approvedInvoices.length > 3 && (
                    <div className="mt-6 text-center">
                      <p className="text-sm text-muted-foreground mb-3">
                        Affichage de 3 sur {approvedInvoices.length} factures approuvées
                      </p>
                      <Button variant="outline" size="sm">
                        Voir Toutes les Factures Approuvées
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          }
          return null
        })()}



        {/* Small footer info */}
        <div className="text-center text-xs text-muted-foreground mt-6">
          <Bot className="h-4 w-4 text-primary inline mr-2" />
          Traitement automatique • 7 formats d'export disponibles
        </div>
      </main>
    </div>
  )
}

export default withAuth(DashboardPage)