import { useEffect, useRef, useState, useCallback } from 'react'
import { apiClient } from '@/lib/api'
import { Invoice } from '@/lib/types'

export function useInvoiceProgress(invoiceId: string | null) {
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<NodeJS.Timeout | null>(null)
  const maxPollsRef = useRef(0)

  const startPolling = useCallback(async () => {
    if (!invoiceId) return
    
    setIsConnected(true)
    setError(null)
    maxPollsRef.current = 0

    const poll = async () => {
      try {
        // Poll for invoice status every 2 seconds
        const updatedInvoice = await apiClient.getInvoice(invoiceId)
        setInvoice(updatedInvoice)
        
        // Stop polling if completed or failed, or after 60 polls (2 minutes)
        if (updatedInvoice.status === 'completed' || updatedInvoice.status === 'failed' || maxPollsRef.current >= 60) {
          stopPolling()
          return
        }
        
        maxPollsRef.current++
        pollingRef.current = setTimeout(poll, 2000)
      } catch (err) {
        console.error('Failed to poll invoice status:', err)
        setError('Échec de récupération du statut de la facture')
        stopPolling()
      }
    }

    // Start immediate poll
    poll()
  }, [invoiceId])

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }
    setIsConnected(false)
    maxPollsRef.current = 0
  }, [])

  useEffect(() => {
    if (invoiceId) {
      startPolling()
    }
    
    return () => {
      stopPolling()
    }
  }, [invoiceId, startPolling, stopPolling])

  return {
    invoice,
    isConnected,
    error,
    reconnect: startPolling,
    disconnect: stopPolling
  }
}