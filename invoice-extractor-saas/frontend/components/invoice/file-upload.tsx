'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api'
import { Invoice } from '@/lib/types'

interface FileUploadProps {
  onUpload?: (invoices: Invoice[]) => void
  accept?: Record<string, string[]>
  maxSize?: number
  maxFiles?: number
}

export function FileUpload({
  onUpload,
  accept = {
    'application/pdf': ['.pdf'],
    'image/*': ['.png', '.jpg', '.jpeg']
  },
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10
}: FileUploadProps) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResults, setUploadResults] = useState<Invoice[]>([])
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles].slice(0, maxFiles))
  }, [maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles: maxFiles - files.length,
    disabled: uploading
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    setUploading(true)
    setUploadProgress(0)
    setError(null)
    setUploadResults([])

    try {
      const results: Invoice[] = []
      const totalFiles = files.length

      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        
        try {
          // Update progress
          setUploadProgress(((i) / totalFiles) * 90)
          
          // Upload file to backend
          const invoice = await apiClient.uploadInvoice(file)
          results.push(invoice)
          
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          // Continue with other files even if one fails
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          results.push({
            id: `error-${i}`,
            filename: file.name,
            status: 'failed',
            processing_mode: 'auto',
            created_at: new Date().toISOString(),
            error_message: errorMessage
          })
        }
      }
      
      setUploadProgress(100)
      setUploadResults(results)
      
      // Call onUpload callback if provided
      if (onUpload) {
        onUpload(results)
      }
      
      // Clear files after successful upload
      setTimeout(() => {
        setFiles([])
        setUploadProgress(0)
        setUploadResults([])
      }, 3000)
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      setError(errorMessage)
      console.error('Upload failed:', error)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center transition-colors",
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
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="text-sm font-medium mb-2">Selected files:</h3>
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-muted rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              {!uploading && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {uploadProgress > 0 && uploadProgress < 100 && (
        <div className="mt-4">
          <Progress value={uploadProgress} className="h-2" />
          <p className="text-sm text-muted-foreground mt-2">
            Processing invoices... {Math.round(uploadProgress)}%
          </p>
        </div>
      )}

      {error && (
        <div className="mt-4 flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {files.length > 0 && !uploading && (
        <Button
          className="mt-4 w-full"
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload {files.length} {files.length === 1 ? 'file' : 'files'}
            </>
          )}
        </Button>
      )}
      
      {/* Processing completed state */}
      {uploadResults.length > 0 && (
        <div className="mt-6 space-y-4">
          {uploadResults.map((invoice) => (
            <div 
              key={invoice.id}
              className={cn(
                "p-4 rounded-lg border",
                invoice.status === 'completed' ? "bg-green-50 border-green-200" :
                invoice.status === 'failed' ? "bg-red-50 border-red-200" :
                "bg-yellow-50 border-yellow-200"
              )}
            >
              <div className="flex items-center gap-3">
                <div className={cn(
                  "p-1 rounded-full",
                  invoice.status === 'completed' ? "bg-green-500" :
                  invoice.status === 'failed' ? "bg-red-500" :
                  "bg-yellow-500"
                )}>
                  {invoice.status === 'completed' ? (
                    <Check className="h-4 w-4 text-white" />
                  ) : invoice.status === 'failed' ? (
                    <X className="h-4 w-4 text-white" />
                  ) : (
                    <Loader2 className="h-4 w-4 text-white animate-spin" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={cn(
                    "font-medium",
                    invoice.status === 'completed' ? "text-green-800" :
                    invoice.status === 'failed' ? "text-red-800" :
                    "text-yellow-800"
                  )}>
                    {invoice.filename}
                  </p>
                  <p className={cn(
                    "text-sm",
                    invoice.status === 'completed' ? "text-green-600" :
                    invoice.status === 'failed' ? "text-red-600" :
                    "text-yellow-600"
                  )}>
                    {invoice.status === 'completed' && 'Successfully processed and ready for export'}
                    {invoice.status === 'failed' && (invoice.error_message || 'Processing failed')}
                    {invoice.status === 'processing' && 'Processing with Claude AI...'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}