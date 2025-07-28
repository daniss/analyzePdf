'use client'

import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Download, X, CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { apiClient } from '@/lib/api'

interface BatchUploadProps {
  onComplete?: () => void
}

interface UploadedFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

interface BatchStatus {
  batch_id: string
  status: 'processing' | 'completed' | 'failed'
  total_invoices: number
  processed_invoices: number
  failed_invoices: number
  export_format: string
  export_file?: string
  error?: string
}

const exportFormats = [
  { value: 'csv', label: 'CSV (Excel)', description: 'Format CSV français pour Excel/LibreOffice' },
  { value: 'json', label: 'JSON', description: 'Format JSON structuré pour intégrations' },
  { value: 'excel', label: 'Excel (.xlsx)', description: 'Fichier Excel avec feuilles multiples' },
  { value: 'sage', label: 'Sage PNM', description: 'Format pour logiciels Sage' },
  { value: 'ebp', label: 'EBP ASCII', description: 'Format pour logiciels EBP' },
  { value: 'ciel', label: 'Ciel XIMPORT', description: 'Format pour logiciels Ciel' },
  { value: 'fec', label: 'FEC', description: 'Format pour administration fiscale française' }
]

export function BatchUpload({ onComplete }: BatchUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [selectedFormat, setSelectedFormat] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // Cleanup effect to clear intervals on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending'
    }))
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  })

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const clearAllFiles = () => {
    setFiles([])
    setBatchStatus(null)
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }

  const startBatchProcessing = async () => {
    if (files.length === 0) return

    // Clear any existing polling interval before starting new processing
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }

    console.log('🚀 Starting batch processing...')
    
    // Firefox compatibility check for file uploads
    const isFirefox = navigator.userAgent.toLowerCase().includes('firefox')
    
    setIsProcessing(true)
    setBatchStatus(null)
    
    try {
      // Create FormData for batch upload - just files, no export format
      const formData = new FormData()
      
      console.log('📁 Adding files to FormData:')
      files.forEach((fileItem, index) => {
        console.log(`  File ${index}: ${fileItem.file.name} (${fileItem.file.size} bytes)`)
        formData.append('files', fileItem.file, fileItem.file.name)
      })
      
      // Log final FormData
      console.log('📦 FormData created with entries:')
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(`  ${key}: File(${value.name}, ${value.size} bytes, ${value.type})`)
        } else {
          console.log(`  ${key}: ${value}`)
        }
      }

      // Firefox compatibility: Reconstruct files to avoid FormData upload issues
      if (isFirefox) {
        console.log('🦊 Firefox detected - using file reconstruction for compatibility')
        
        try {
          // Reconstruct files for Firefox compatibility
          const reconstructedFiles = await Promise.all(
            files.map(async (fileItem) => {
              const arrayBuffer = await fileItem.file.arrayBuffer()
              return new File([arrayBuffer], fileItem.file.name, { type: fileItem.file.type })
            })
          )
          
          // Create new FormData with reconstructed files
          const firefoxFormData = new FormData()
          reconstructedFiles.forEach((file) => {
            firefoxFormData.append('files', file, file.name)
          })
          
          console.log('🔧 Using reconstructed files for Firefox compatibility')
          const batchData = await apiClient.post('/api/batch/batch-process', firefoxFormData)
          console.log('✅ Firefox compatibility upload succeeded:', batchData)
          
          setBatchStatus({
            batch_id: batchData.batch_id,
            status: 'processing',
            total_invoices: batchData.invoice_count,
            processed_invoices: 0,
            failed_invoices: 0,
            export_format: 'pending_review'
          })

          // Start polling for status updates
          startStatusPolling(batchData.batch_id)
          return // Exit early on success
          
        } catch (firefoxError) {
          console.error('❌ Firefox compatibility upload failed:', firefoxError)
          console.log('🔄 Falling back to standard upload...')
          // Fall through to normal upload handling
        }
      }
      
      // Use apiClient.post with proper timeout handling
      console.log('Sending POST to batch-process via apiClient...')
      console.log('📡 Request details:', {
        url: '/api/batch/batch-process',
        formDataEntries: Array.from(formData.entries()).map(([key, value]) => ({
          key,
          valueType: value instanceof File ? 'File' : typeof value,
          fileName: value instanceof File ? value.name : undefined
        }))
      })
      
      const batchData = await apiClient.post('/api/batch/batch-process', formData)
      console.log('✅ Batch processing started successfully:', batchData)
      
      setBatchStatus({
        batch_id: batchData.batch_id,
        status: 'processing',
        total_invoices: batchData.invoice_count,
        processed_invoices: 0,
        failed_invoices: 0,
        export_format: 'pending_review'
      })

      // Start polling for status updates
      startStatusPolling(batchData.batch_id)
      
    } catch (error: any) {
      console.error('❌ Batch processing failed with detailed error:', {
        message: error.message,
        stack: error.stack,
        name: error.name,
        cause: error.cause,
        fullError: error
      })
      setIsProcessing(false)
      setBatchStatus(null)
      
      // Show user-friendly error message
      if (error.message?.includes('timeout')) {
        alert('Le traitement a pris trop de temps. Veuillez réessayer avec moins de fichiers.')
      } else if (error.message?.includes('401')) {
        alert('Session expirée. Veuillez vous reconnecter.')
      } else {
        alert('Erreur lors du traitement. Veuillez réessayer.')
      }
    }
  }


  const startStatusPolling = (batchId: string) => {
    let pollCount = 0
    const maxPolls = 60 // 2 minutes maximum (60 * 2 seconds)
    
    const interval = setInterval(async () => {
      pollCount++
      
      try {
        const statusResponse = await apiClient.get(`/api/batch/batch-status/${batchId}`)
        const status: BatchStatus = statusResponse
        
        setBatchStatus(status)

        if (status.status === 'completed' || status.status === 'failed') {
          console.log(`✅ Batch processing ${status.status}! Resetting UI state.`)
          clearInterval(interval)
          setPollingInterval(null)
          setIsProcessing(false)

          // Call onComplete callback to refresh the invoice list
          if (onComplete) {
            onComplete()
          }

          // No auto-download - invoices will be available for review
        } else if (pollCount >= maxPolls) {
          // Timeout after 2 minutes
          console.warn('⏰ Polling timeout reached - resetting UI state')
          clearInterval(interval)
          setPollingInterval(null)
          setIsProcessing(false)
          alert('Le traitement prend plus de temps que prévu. Veuillez vérifier la section "Factures en Attente de Révision".')
        }
      } catch (error) {
        console.error('❌ Failed to get batch status - resetting UI state:', error)
        // Reset processing state if polling fails
        setIsProcessing(false)
        clearInterval(interval)
        setPollingInterval(null)
        alert('Erreur lors du suivi du traitement. Veuillez vérifier la section "Factures en Attente de Révision".')
      }
    }, 2000)

    setPollingInterval(interval)
  }

  // Download functions removed - export only available after review and approval

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const canStartProcessing = files.length > 0 && !isProcessing
  const progressPercentage = batchStatus ? 
    Math.round((batchStatus.processed_invoices / batchStatus.total_invoices) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Processing Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Traitement par Lots
          </CardTitle>
          <CardDescription>
            Téléversez plusieurs factures pour extraction de données. Après traitement, vous pourrez réviser et choisir le format d'export.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Flux de traitement :</h4>
            <ol className="text-sm text-blue-700 space-y-1">
              <li>1. 📤 Téléversement et extraction des données</li>
              <li>2. 📋 Révision dans "Factures en Attente de Révision"</li>
              <li>3. ✅ Approbation des données validées</li>
              <li>4. 📊 Export dans le format de votre choix</li>
            </ol>
          </div>
        </CardContent>
      </Card>

      {/* File Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
Téléverser Plusieurs Fichiers
          </CardTitle>
          <CardDescription>
            Glissez-déposez plusieurs factures PDF/images ou cliquez pour sélectionner
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
              ${isProcessing ? 'pointer-events-none opacity-50' : ''}
            `}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            {isDragActive ? (
              <p className="text-blue-600">Déposez les fichiers ici...</p>
            ) : (
              <div>
                <p className="text-gray-600 mb-2">
                  Glissez-déposez vos factures ici, ou cliquez pour sélectionner
                </p>
                <p className="text-sm text-gray-500">
                  PDF, PNG, JPG jusqu'à 10 Mo par fichier
                </p>
              </div>
            )}
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="font-medium">Fichiers sélectionnés ({files.length})</h4>
                {!isProcessing && (
                  <Button variant="outline" size="sm" onClick={clearAllFiles}>
                    <X className="h-4 w-4 mr-1" />
                    Tout supprimer
                  </Button>
                )}
              </div>
              
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {files.map((fileItem) => (
                  <div key={fileItem.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-gray-500" />
                      <span className="text-sm font-medium">{fileItem.file.name}</span>
                      <Badge variant="secondary" className="text-xs">
                        {(fileItem.file.size / 1024 / 1024).toFixed(1)} MB
                      </Badge>
                    </div>
                    {!isProcessing && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => removeFile(fileItem.id)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Processing Status */}
      {batchStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon(batchStatus.status)}
              Traitement en Cours
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Progression</span>
                  <span>{batchStatus.processed_invoices} / {batchStatus.total_invoices}</span>
                </div>
                <Progress value={progressPercentage} className="w-full" />
              </div>
              
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{batchStatus.total_invoices}</div>
                  <div className="text-sm text-gray-500">Total</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{batchStatus.processed_invoices}</div>
                  <div className="text-sm text-gray-500">Traités</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{batchStatus.failed_invoices}</div>
                  <div className="text-sm text-gray-500">Erreurs</div>
                </div>
              </div>

              {batchStatus.status === 'completed' && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-green-800">
                      Traitement terminé ! Les factures sont prêtes pour révision.
                    </span>
                  </div>
                  <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-700">
                      <strong>📋 Prochaine étape :</strong> Vos {batchStatus.total_invoices} factures apparaissent maintenant dans 
                      "Factures en Attente de Révision". Révisez et approuvez-les pour débloquer l'export.
                    </p>
                  </div>
                  <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-xs text-yellow-700">
                      💡 <strong>Aucun téléchargement automatique</strong> - L'export sera disponible uniquement après validation des données.
                    </p>
                  </div>
                </div>
              )}

              {batchStatus.status === 'failed' && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                    <span className="font-medium text-red-800">Erreur de traitement</span>
                  </div>
                  {batchStatus.error && (
                    <p className="text-sm text-red-600 mt-1">{batchStatus.error}</p>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button 
          onClick={startBatchProcessing}
          disabled={!canStartProcessing}
          className="flex-1"
          size="lg"
        >
          {isProcessing ? (
            <>
              <Clock className="h-4 w-4 mr-2 animate-spin" />
              Traitement en cours...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Traiter les Factures ({files.length} fichiers)
            </>
          )}
        </Button>
        
        {!isProcessing && files.length > 0 && (
          <Button variant="outline" onClick={clearAllFiles}>
            Annuler
          </Button>
        )}
        
      </div>

    </div>
  )
}