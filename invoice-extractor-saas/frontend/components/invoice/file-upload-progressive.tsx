'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2, Check, AlertCircle, DollarSign, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { Invoice } from '@/lib/types'

interface FileUploadProgressiveProps {
  onUpload?: (invoices: Invoice[]) => void
  accept?: Record<string, string[]>
  maxSize?: number
  maxFiles?: number
}

interface FileWithProgress extends File {
  id: string
  invoiceId?: string
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string
}

// Simplified: Single processing mode - always use Claude Vision for reliability

export function FileUploadProgressive({
  onUpload,
  accept = {
    'application/pdf': ['.pdf'],
    'image/*': ['.png', '.jpg', '.jpeg']
  },
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10
}: FileUploadProgressiveProps) {
  const [files, setFiles] = useState<FileWithProgress[]>([])
  const [uploading, setUploading] = useState(false)
  const [currentProcessingId, setCurrentProcessingId] = useState<string | null>(null)
  
  // Simplified: Direct processing without tier tracking

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file, index) => {
      console.log('File properties:', { name: file.name, size: file.size, type: file.type });
      const fileWithProgress = file as FileWithProgress;
      fileWithProgress.id = `${Date.now()}-${index}`;
      fileWithProgress.status = 'pending';
      fileWithProgress.progress = 0;
      return fileWithProgress;
    })
    setFiles(prev => [...prev, ...newFiles].slice(0, maxFiles))
  }, [maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles: maxFiles - files.length,
    disabled: uploading
  })

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(file => file.id !== id))
  }


  const handleUpload = async () => {
    if (files.length === 0) return

    setUploading(true)
    const results: Invoice[] = []

    try {
      for (const file of files) {
        try {
          // Update file status to uploading
          setFiles(prev => prev.map(f => 
            f.id === file.id ? { ...f, status: 'uploading', progress: 20 } : f
          ))
          
          // Simplified: Always use standard Claude Vision processing
          const invoice = await apiClient.uploadInvoice(file)
          console.log('Invoice uploaded:', invoice)
          
          // Update file with invoice ID
          setFiles(prev => prev.map(f => 
            f.id === file.id ? { 
              ...f, 
              invoiceId: invoice.id, 
              status: 'processing',
              progress: 50,
            } : f
          ))
          
          // Set current processing ID for WebSocket (only for non-privacy modes)
          setCurrentProcessingId(invoice.id)
          
          // Simulate progress updates (in real app, this would come from WebSocket)
          const progressInterval = setInterval(() => {
            setFiles(prev => prev.map(f => {
              if (f.id === file.id && f.progress < 90) {
                return { ...f, progress: f.progress + 10 }
              }
              return f
            }))
          }, 500)
          
          // Wait for processing completion
          await new Promise<void>((resolve) => {
            setTimeout(() => {
              clearInterval(progressInterval)
              setFiles(prev => prev.map(f => 
                f.id === file.id ? { ...f, status: 'completed', progress: 100 } : f
              ))
              results.push(invoice)
              resolve()
            }, 3000)
          })
          
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          
          let errorMessage = 'Échec du téléversement'
          if (error instanceof Error) {
            if (error.message.includes('Google API key not configured') || error.message.includes('Gemini API')) {
              errorMessage = '⚠️ Gemini API key not configured. Please contact administrator to set GOOGLE_API_KEY.'
            } else {
              errorMessage = error.message
            }
          }
          
          setFiles(prev => prev.map(f => 
            f.id === file.id ? { 
              ...f, 
              status: 'failed', 
              error: errorMessage
            } : f
          ))
        }
      }
      
      console.log('All uploads completed, results:', results)
      
      // Call onUpload callback if provided
      if (onUpload && results.length > 0) {
        onUpload(results)
      }
      
      // Clear completed files after delay
      setTimeout(() => {
        setFiles(prev => prev.filter(f => f.status !== 'completed'))
      }, 5000)
      
    } finally {
      setUploading(false)
      setCurrentProcessingId(null)
    }
  }


  return (
    <div className="w-full space-y-6">

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center transition-all",
          isDragActive ? "border-primary bg-primary/5" : "border-border/60",
          uploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="p-4 bg-primary/10 rounded-full">
            <Upload className="h-8 w-8 text-primary" />
          </div>
          
          <div>
            <p className="text-lg font-medium">
              {isDragActive ? "Drop your files here" : "Drag & drop files here"}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              or click to browse (PDF, PNG, JPG up to 10MB)
            </p>
          </div>
          
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              <span>Extraction automatique</span>
            </div>
          </div>
        </div>
      </div>

      {/* Files List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Processing queue:</h3>
          {files.map((file) => (
            <Card key={file.id} className={cn(
              "transition-all duration-300",
              file.status === 'completed' && "border-green-200 bg-green-50/50",
              file.status === 'failed' && "border-red-200 bg-red-50/50"
            )}>
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <FileText className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {file.size ? (file.size / 1024 / 1024).toFixed(2) : '0.00'} MB
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {file.status === 'completed' && (
                        <Badge variant="success">Completed</Badge>
                      )}
                      {file.status === 'failed' && (
                        <Badge variant="error">Échec</Badge>
                      )}
                      {file.status === 'processing' && (
                        <Badge variant="warning">Processing</Badge>
                      )}
                      {file.status === 'pending' && !uploading && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(file.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  {/* Progress Bar */}
                  {(file.status === 'uploading' || file.status === 'processing') && (
                    <div className="space-y-2">
                      <Progress value={file.progress} className="h-2" />
                      <p className="text-xs text-muted-foreground">
                        {file.status === 'uploading' ? 'Téléversement...' : 'Traitement en cours...'}
                      </p>
                    </div>
                  )}
                  
                  
                  {/* Error Message */}
                  {file.error && (
                    <div className="flex items-center gap-2 text-sm text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      <span>{file.error}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Upload Button */}
      {files.length > 0 && !uploading && (
        <Button
          className="w-full"
          onClick={handleUpload}
          disabled={uploading || files.every(f => f.status !== 'pending')}
        >
          <Upload className="mr-2 h-4 w-4" />
          Process {files.filter(f => f.status === 'pending').length} {files.filter(f => f.status === 'pending').length === 1 ? 'file' : 'files'}
        </Button>
      )}
      
      {/* Cost Estimate */}
      {files.length > 0 && (
        <Card className="bg-muted/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                €{(files.length * 0.001).toFixed(3)} - €{(files.length * 0.01).toFixed(3)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Smart processing: €0.001 for clean text, €0.01 for image processing (Gemini 2.5 Flash)
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Reliable Gemini Vision processing with multilingual support
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}