'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  Download, 
  FileText, 
  Table, 
  Code, 
  Building2, 
  Calculator,
  FileCheck,
  ChevronDown,
  Loader2,
  CheckCircle,
  Package
} from 'lucide-react'

interface ExportFormat {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  extension: string
  category: 'standard' | 'accounting'
  recommended?: boolean
}

interface BulkExportSelectorProps {
  invoiceIds: string[]
  onExportComplete?: (format: string, success: boolean) => void
  disabled?: boolean
}

const exportFormats: ExportFormat[] = [
  {
    id: 'csv',
    name: 'CSV Français',
    description: 'Fichiers CSV individuels dans une archive ZIP',
    icon: <Table className="h-4 w-4" />,
    extension: '.csv',
    category: 'standard',
    recommended: true
  },
  {
    id: 'sage',
    name: 'Sage PNM',
    description: 'Fichier unique PNM avec toutes les factures',
    icon: <Building2 className="h-4 w-4" />,
    extension: '.pnm',
    category: 'accounting'
  },
  {
    id: 'json',
    name: 'JSON Structuré',
    description: 'Fichiers JSON individuels dans une archive ZIP',
    icon: <Code className="h-4 w-4" />,
    extension: '.json',
    category: 'standard'
  },
  {
    id: 'ebp',
    name: 'EBP ASCII',
    description: 'Fichier unique ASCII avec toutes les factures',
    icon: <Calculator className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  },
  {
    id: 'ciel',
    name: 'Ciel XIMPORT',
    description: 'Fichier unique XIMPORT avec toutes les factures',
    icon: <Building2 className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  },
  {
    id: 'fec',
    name: 'FEC (DGFiP)',
    description: 'Fichier unique FEC pour administration fiscale',
    icon: <FileCheck className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  }
]

export function BulkExportSelector({ invoiceIds, onExportComplete, disabled = false }: BulkExportSelectorProps) {
  const [isExporting, setIsExporting] = useState<string | null>(null)
  const [lastExported, setLastExported] = useState<string | null>(null)

  const handleBulkExport = async (format: ExportFormat) => {
    if (invoiceIds.length === 0) {
      alert('Aucune facture à exporter')
      return
    }

    setIsExporting(format.id)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1]
      
      if (!token) {
        alert('Token d\'authentification introuvable')
        return
      }

      // Call batch export endpoint
      const response = await fetch(`${apiUrl}/api/exports/batch?format=${format.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(invoiceIds)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Export failed')
      }

      // Create download link
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Get filename from Content-Disposition header or create default
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `export_${format.id}_${new Date().toISOString().split('T')[0]}.zip`
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      setLastExported(format.id)
      if (onExportComplete) {
        onExportComplete(format.id, true)
      }

    } catch (error) {
      console.error('Bulk export failed:', error)
      alert(`Erreur d'export en lot ${format.name}: ${error.message}`)
      if (onExportComplete) {
        onExportComplete(format.id, false)
      }
    } finally {
      setIsExporting(null)
    }
  }

  const standardFormats = exportFormats.filter(f => f.category === 'standard')
  const accountingFormats = exportFormats.filter(f => f.category === 'accounting')

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="default"
          size="sm"
          className="gap-2 bg-green-500 hover:bg-green-600 text-white border-0 shadow-lg"
          disabled={!!isExporting || disabled || invoiceIds.length === 0}
        >
          {isExporting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Export en cours...
            </>
          ) : (
            <>
              <Package className="h-4 w-4" />
              Exporter Toutes ({invoiceIds.length})
              <ChevronDown className="h-3 w-3" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Package className="h-4 w-4" />
          Export en Lot - {invoiceIds.length} Facture{invoiceIds.length > 1 ? 's' : ''}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {/* Standard Formats */}
        <div className="px-2 py-1">
          <div className="text-xs font-medium text-muted-foreground mb-1">Formats Standard</div>
          {standardFormats.map((format) => (
            <DropdownMenuItem
              key={format.id}
              onClick={() => handleBulkExport(format)}
              disabled={isExporting === format.id}
              className="cursor-pointer p-3 hover:bg-gray-50"
            >
              <div className="flex items-start gap-3 w-full">
                <div className="mt-0.5">
                  {format.icon}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{format.name}</span>
                    {format.recommended && (
                      <Badge variant="secondary" className="text-xs">Recommandé</Badge>
                    )}
                    {lastExported === format.id && (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {format.description}
                  </div>
                </div>
              </div>
            </DropdownMenuItem>
          ))}
        </div>
        
        <DropdownMenuSeparator />
        
        {/* Accounting Formats */}
        <div className="px-2 py-1">
          <div className="text-xs font-medium text-muted-foreground mb-1">Logiciels Comptables</div>
          {accountingFormats.map((format) => (
            <DropdownMenuItem
              key={format.id}
              onClick={() => handleBulkExport(format)}
              disabled={isExporting === format.id}
              className="cursor-pointer p-3 hover:bg-gray-50"
            >
              <div className="flex items-start gap-3 w-full">
                <div className="mt-0.5">
                  {format.icon}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{format.name}</span>
                    {lastExported === format.id && (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {format.description}
                  </div>
                </div>
              </div>
            </DropdownMenuItem>
          ))}
        </div>
        
        <DropdownMenuSeparator />
        
        <div className="px-3 py-2 text-xs text-muted-foreground">
          💡 Export de {invoiceIds.length} facture{invoiceIds.length > 1 ? 's' : ''} approuvée{invoiceIds.length > 1 ? 's' : ''}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}