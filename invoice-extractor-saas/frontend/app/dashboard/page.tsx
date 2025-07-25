'use client'

import { useAuth, withAuth } from '@/lib/auth-context'
import { useInvoices, useDashboardStats, useExportInvoicesCSV, useExportInvoicesJSON } from '@/lib/hooks'
import { FileUpload } from '@/components/invoice/file-upload'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Download, Calendar, DollarSign, Bot, Zap, TrendingUp, Clock, ArrowRight, Loader2 } from 'lucide-react'
import { Invoice } from '@/lib/types'

function DashboardPage() {
  const { user, logout } = useAuth()
  const { data: invoices = [], isLoading, error, refetch } = useInvoices()
  const stats = useDashboardStats()
  const exportCSV = useExportInvoicesCSV()
  const exportJSON = useExportInvoicesJSON()

  const handleUpload = (newInvoices: Invoice[]) => {
    // Refetch invoices to get the latest data
    refetch()
  }

  const handleExportCSV = () => {
    exportCSV.mutate()
  }

  const handleExportJSON = () => {
    exportJSON.mutate()
  }

  const recentInvoices = invoices.slice(0, 5) // Show latest 5 invoices

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background gradient-mesh">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading your dashboard...</p>
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
              InvoiceAI
            </h1>
          </div>
          <div className="ml-auto flex items-center gap-4">
            {user && (
              <span className="text-sm text-muted-foreground">
                Welcome, {user.email}
              </span>
            )}
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-muted-foreground hover:text-foreground"
              onClick={logout}
            >
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="container py-8">
        {/* Welcome Section */}
        <div className="mb-12">
          <h2 className="text-3xl font-bold mb-2">Welcome back!</h2>
          <p className="text-lg text-muted-foreground">Transform your invoices with AI-powered extraction</p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-6 md:grid-cols-4 mb-12">
          <Card className="card-modern group hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Invoices</CardTitle>
              <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                <FileText className="h-5 w-5 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold mb-1">{stats.total_invoices}</div>
              <p className="text-sm flex items-center gap-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                {stats.completed_invoices} completed
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-modern group hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Amount</CardTitle>
              <div className="p-2 rounded-lg bg-green-500/10 group-hover:bg-green-500/20 transition-colors">
                <DollarSign className="h-5 w-5 text-green-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold mb-1">
                ${stats.total_amount.toLocaleString()}
              </div>
              <p className="text-sm flex items-center gap-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                Extracted value
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-modern group hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Processing Time</CardTitle>
              <div className="p-2 rounded-lg bg-orange-500/10 group-hover:bg-orange-500/20 transition-colors">
                <Clock className="h-5 w-5 text-orange-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold mb-1">8.2s</div>
              <p className="text-sm flex items-center gap-1 text-muted-foreground">
                <Zap className="h-4 w-4" />
                Average per invoice
              </p>
            </CardContent>
          </Card>
          
          <Card className="card-modern group hover:shadow-xl transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Accuracy Rate</CardTitle>
              <div className="p-2 rounded-lg bg-purple-500/10 group-hover:bg-purple-500/20 transition-colors">
                <TrendingUp className="h-5 w-5 text-purple-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold mb-1">99.2%</div>
              <p className="text-sm flex items-center gap-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                Claude 4 powered
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Error State */}
        {error && (
          <Card className="card-modern mb-12 border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 text-red-700">
                <TrendingUp className="h-5 w-5" />
                <p>Failed to load dashboard data. Please try refreshing the page.</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => refetch()}
                  className="ml-auto"
                >
                  Retry
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Upload Section */}
        <Card className="card-modern mb-12 overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 gradient-primary"></div>
          <CardHeader className="pb-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl mb-2">Process New Invoices</CardTitle>
                <CardDescription className="text-lg">
                  Upload your PDF invoices and let Claude 4 AI extract the data instantly
                </CardDescription>
              </div>
              <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-sm font-medium text-primary">
                <Zap className="h-4 w-4" />
                AI Powered
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <FileUpload onUpload={handleUpload} />
          </CardContent>
        </Card>

        {/* Recent Invoices */}
        {recentInvoices.length > 0 && (
          <Card className="card-modern">
            <CardHeader className="pb-6">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl mb-2">Recent Invoices</CardTitle>
                  <CardDescription className="text-lg">
                    Your recently processed invoices ready for export
                  </CardDescription>
                </div>
                <div className="hidden md:flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleExportCSV}
                    disabled={exportCSV.isPending}
                  >
                    {exportCSV.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4 mr-2" />
                    )}
                    CSV
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleExportJSON}
                    disabled={exportJSON.isPending}
                  >
                    {exportJSON.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4 mr-2" />
                    )}
                    JSON
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentInvoices.map((invoice) => (
                  <Card
                    key={invoice.id}
                    className="p-6 hover:shadow-lg transition-all duration-300 hover:scale-[1.02] bg-gradient-to-r from-background to-muted/30"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="p-3 rounded-xl bg-primary/10">
                          <FileText className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <p className="font-semibold text-lg mb-1">{invoice.filename}</p>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span className="font-medium">{invoice.data?.invoice_number || 'N/A'}</span>
                            <span>·</span>
                            <span className="font-semibold text-foreground">
                              ${(invoice.data?.total || 0).toLocaleString()}
                            </span>
                            <span>·</span>
                            <span>{new Date(invoice.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium border ${
                          invoice.status === 'completed' 
                            ? 'bg-green-100 text-green-800 border-green-200'
                            : invoice.status === 'processing'
                            ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                            : 'bg-red-100 text-red-800 border-red-200'
                        }`}>
                          <div className={`w-2 h-2 rounded-full mr-2 ${
                            invoice.status === 'completed' 
                              ? 'bg-green-500'
                              : invoice.status === 'processing'
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}></div>
                          {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                        </span>
                        {invoice.status === 'completed' && (
                          <Button size="sm" className="gradient-primary text-white border-0 shadow-md hover:shadow-lg transition-shadow">
                            <Download className="h-4 w-4 mr-2" />
                            Export
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Empty State */}
        {recentInvoices.length === 0 && (
          <Card className="card-modern text-center py-16">
            <CardContent>
              <div className="mx-auto w-24 h-24 bg-primary/10 rounded-full flex items-center justify-center mb-6">
                <FileText className="h-12 w-12 text-primary" />
              </div>
              <h3 className="text-2xl font-semibold mb-4">No invoices yet</h3>
              <p className="text-lg text-muted-foreground mb-8 max-w-md mx-auto">
                Upload your first invoice above to see the power of AI-driven data extraction
              </p>
              <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-primary" />
                  10s processing
                </div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  99% accuracy
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}

export default withAuth(DashboardPage)