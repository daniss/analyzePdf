'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { 
  DollarSign, 
  TrendingUp, 
  FileText, 
  Users, 
  Calendar,
  Download,
  BarChart3
} from 'lucide-react'
import { apiClient } from '@/lib/api'

interface CostSummary {
  period: {
    start_date: string
    end_date: string
    days: number
  }
  summary: {
    total_cost_eur: number
    total_invoices: number
    total_requests: number
    avg_cost_per_invoice: number
    avg_cost_per_day: number
  }
  daily_breakdown: Array<{
    date: string
    total_cost_eur: number
    total_invoices: number
    total_requests: number
  }>
  provider_breakdown: Array<{
    provider: string
    cost_eur: number
    invoices: number
  }>
}

interface MonthlySummary {
  period: string
  summary: {
    total_cost_eur: number
    total_invoices: number
    active_users: number
    cost_per_invoice: number
  }
}

export function CostMonitor() {
  const [dailySummary, setDailySummary] = useState<CostSummary | null>(null)
  const [monthlySummary, setMonthlySummary] = useState<MonthlySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    // Set default dates (last 30 days)
    const today = new Date()
    const thirtyDaysAgo = new Date(today)
    thirtyDaysAgo.setDate(today.getDate() - 30)
    
    setEndDate(today.toISOString().split('T')[0])
    setStartDate(thirtyDaysAgo.toISOString().split('T')[0])
    
    loadCostData()
    loadMonthlyData()
  }, [])

  const loadCostData = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      
      const response = await apiClient.get(`/api/admin/cost-summary/daily?${params}`)
      setDailySummary(response)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement des données de coût')
      console.error('Failed to load cost data:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadMonthlyData = async () => {
    try {
      const response = await apiClient.get('/api/admin/cost-summary/current-month')
      setMonthlySummary(response)
    } catch (err: any) {
      console.error('Failed to load monthly data:', err)
    }
  }

  const handleDateChange = () => {
    if (startDate && endDate) {
      loadCostData()
    }
  }

  if (loading && !dailySummary) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">Chargement des données de coût...</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6">
            <div className="text-center text-red-700">
              Erreur: {error}
              <br />
              <Button 
                variant="outline" 
                className="mt-4" 
                onClick={loadCostData}
              >
                Réessayer
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Monitoring des Coûts</h1>
          <p className="text-muted-foreground">
            Surveillance interne des coûts d'API et analytics business
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          Admin Only
        </Badge>
      </div>

      {/* Date Range Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Période d'Analyse
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="start-date">Date de début</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="end-date">Date de fin</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <Button onClick={handleDateChange} className="mt-6">
              Actualiser
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Monthly Summary */}
      {monthlySummary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Résumé du Mois en Cours ({monthlySummary.period})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {monthlySummary.summary.total_cost_eur.toFixed(4)} €
                </div>
                <div className="text-sm text-muted-foreground">Coût Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {monthlySummary.summary.total_invoices}
                </div>
                <div className="text-sm text-muted-foreground">Factures Traitées</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {monthlySummary.summary.active_users}
                </div>
                <div className="text-sm text-muted-foreground">Utilisateurs Actifs</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {monthlySummary.summary.cost_per_invoice.toFixed(4)} €
                </div>
                <div className="text-sm text-muted-foreground">Coût/Facture</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Daily Summary */}
      {dailySummary && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Coût Total
                </CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dailySummary.summary.total_cost_eur.toFixed(4)} €
                </div>
                <p className="text-xs text-muted-foreground">
                  Sur {dailySummary.period.days} jours
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Factures Traitées
                </CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dailySummary.summary.total_invoices}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dailySummary.summary.total_requests} requêtes
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Coût par Facture
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dailySummary.summary.avg_cost_per_invoice.toFixed(4)} €
                </div>
                <p className="text-xs text-muted-foreground">
                  Moyenne par facture
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Coût Quotidien Moyen
                </CardTitle>
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dailySummary.summary.avg_cost_per_day.toFixed(4)} €
                </div>
                <p className="text-xs text-muted-foreground">
                  Par jour en moyenne
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Provider Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Répartition par Fournisseur</CardTitle>
              <CardDescription>
                Coûts par provider d'API
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {dailySummary.provider_breakdown.map((provider) => (
                  <div key={provider.provider} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{provider.provider}</Badge>
                      <span className="text-sm text-muted-foreground">
                        {provider.invoices} factures
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {provider.cost_eur.toFixed(4)} €
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Daily Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Données Quotidiennes Récentes</CardTitle>
              <CardDescription>
                Détail des 7 derniers jours
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {dailySummary.daily_breakdown.slice(-7).map((day) => (
                  <div key={day.date} className="flex items-center justify-between p-2 rounded border">
                    <div className="flex items-center gap-4">
                      <span className="font-medium">{day.date}</span>
                      <Badge variant="secondary">{day.total_invoices} factures</Badge>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{day.total_cost_eur.toFixed(4)} €</div>
                      <div className="text-xs text-muted-foreground">
                        {day.total_requests} requêtes
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}