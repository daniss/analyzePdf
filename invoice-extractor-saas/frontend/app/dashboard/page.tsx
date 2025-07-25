'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/invoice/file-upload'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Download, Calendar, DollarSign, Bot, Zap, TrendingUp, Clock, ArrowRight } from 'lucide-react'

export default function DashboardPage() {
  const [recentInvoices, setRecentInvoices] = useState<any[]>([])

  const handleUpload = async (files: File[]) => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Add mock invoices
    const newInvoices = files.map((file, index) => ({
      id: Date.now() + index,
      filename: file.name,
      uploadDate: new Date().toISOString(),
      status: 'completed',
      total: Math.floor(Math.random() * 10000) + 100,
      invoiceNumber: `INV-${Math.floor(Math.random() * 10000)}`
    }))
    
    setRecentInvoices(prev => [...newInvoices, ...prev])
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
          <div className="ml-auto">
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
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
              <div className="text-3xl font-bold mb-1">{recentInvoices.length}</div>
              <p className="text-sm flex items-center gap-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                Ready to process
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
                ${recentInvoices.reduce((sum, inv) => sum + inv.total, 0).toLocaleString()}
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
                <Button variant="outline" className="hidden md:flex">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
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
                            <span className="font-medium">{invoice.invoiceNumber}</span>
                            <span>·</span>
                            <span className="font-semibold text-foreground">${invoice.total.toLocaleString()}</span>
                            <span>·</span>
                            <span>{new Date(invoice.uploadDate).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-green-100 text-green-800 border border-green-200">
                          <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                          Completed
                        </span>
                        <Button size="sm" className="gradient-primary text-white border-0 shadow-md hover:shadow-lg transition-shadow">
                          <Download className="h-4 w-4 mr-2" />
                          Export
                        </Button>
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