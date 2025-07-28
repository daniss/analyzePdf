import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './api'
// Types are imported but not directly used in this hooks file
// import { Invoice, User } from './types'

// Invoice hooks
export function useInvoices() {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: () => apiClient.getInvoices(),
    staleTime: 30 * 1000, // 30 seconds
  })
}

export function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => apiClient.getInvoice(invoiceId),
    enabled: !!invoiceId,
  })
}

export function useUploadInvoice() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (file: File) => apiClient.uploadInvoice(file),
    onSuccess: () => {
      // Invalidate and refetch invoices
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (invoiceId: string) => apiClient.deleteInvoice(invoiceId),
    onSuccess: () => {
      // Invalidate and refetch invoices
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

// Export hooks
export function useExportInvoicesCSV() {
  return useMutation({
    mutationFn: () => apiClient.exportInvoicesCSV(),
    onSuccess: (blob) => {
      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoices-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
  })
}

export function useExportInvoicesJSON() {
  return useMutation({
    mutationFn: () => apiClient.exportInvoicesJSON(),
    onSuccess: (blob) => {
      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoices-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
  })
}

export function useExportInvoiceCSV() {
  return useMutation({
    mutationFn: (invoiceId: string) => apiClient.exportInvoiceCSV(invoiceId),
    onSuccess: (blob, invoiceId) => {
      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoice-${invoiceId}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
  })
}

export function useExportInvoiceJSON() {
  return useMutation({
    mutationFn: (invoiceId: string) => apiClient.exportInvoiceJSON(invoiceId),
    onSuccess: (blob, invoiceId) => {
      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoice-${invoiceId}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    },
  })
}

// Derived data hooks
export function useDashboardStats() {
  const { data: invoices = [] } = useInvoices()
  
  // Calculate real processing times for completed invoices
  const completedInvoices = invoices.filter(inv => 
    inv.status === 'completed' && 
    inv.processing_started_at && 
    inv.processing_completed_at
  )
  
  const processingTimes = completedInvoices.map(inv => {
    const startTime = new Date(inv.processing_started_at).getTime()
    const endTime = new Date(inv.processing_completed_at).getTime()
    return (endTime - startTime) / 1000 // Convert to seconds
  })
  
  const averageProcessingTime = processingTimes.length > 0
    ? processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length
    : null
  
  // Calculate time-based savings percentage (compared to manual processing)
  // Assume manual processing takes ~300 seconds (5 minutes) per invoice
  const manualProcessingTime = 300
  const savingsPercentage = averageProcessingTime 
    ? Math.max(0, Math.min(95, Math.round(((manualProcessingTime - averageProcessingTime) / manualProcessingTime) * 100)))
    : null
  
  const stats = {
    total_invoices: invoices.length,
    // Use total_ttc for French invoices, fallback to total
    total_amount: invoices.reduce((sum, inv) => {
      const amount = inv.data?.total_ttc || inv.data?.total || 0
      return sum + amount
    }, 0),
    completed_invoices: invoices.filter(inv => inv.status === 'completed').length,
    processing_invoices: invoices.filter(inv => inv.status === 'processing').length,
    failed_invoices: invoices.filter(inv => inv.status === 'failed').length,
    average_processing_time: averageProcessingTime,
    time_savings_percentage: savingsPercentage
  }

  return { data: stats }
}