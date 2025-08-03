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
  CheckCircle
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

interface ExportFormatSelectorProps {
  invoiceId: string
  onExportComplete?: (format: string, success: boolean) => void
}

const exportFormats: ExportFormat[] = [
  {
    id: 'csv',
    name: 'CSV Français',
    description: 'Format CSV avec séparateur point-virgule',
    icon: <Table className="h-4 w-4" />,
    extension: '.csv',
    category: 'standard',
    recommended: true
  },
  {
    id: 'json',
    name: 'JSON Structuré',
    description: 'Format JSON avec terminologie française',
    icon: <Code className="h-4 w-4" />,
    extension: '.json',
    category: 'standard'
  },
  {
    id: 'sage',
    name: 'Sage PNM',
    description: 'Format PNM pour logiciels Sage',
    icon: <Building2 className="h-4 w-4" />,
    extension: '.pnm',
    category: 'accounting'
  },
  {
    id: 'ebp',
    name: 'EBP ASCII',
    description: 'Format ASCII pour logiciels EBP',
    icon: <Calculator className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  },
  {
    id: 'ciel',
    name: 'Ciel XIMPORT',
    description: 'Format XIMPORT pour logiciels Ciel',
    icon: <Building2 className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  },
  {
    id: 'fec',
    name: 'FEC (DGFiP)',
    description: 'Format obligatoire administration fiscale',
    icon: <FileCheck className="h-4 w-4" />,
    extension: '.txt',
    category: 'accounting'
  }
]

export function ExportFormatSelector({ invoiceId, onExportComplete }: ExportFormatSelectorProps) {
  const [isExporting, setIsExporting] = useState<string | null>(null)
  const [lastExported, setLastExported] = useState<string | null>(null)

  const handleExport = async (format: ExportFormat) => {
    setIsExporting(format.id)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1]
      
      const response = await fetch(`${apiUrl}/api/exports/approved/${invoiceId}/${format.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        }
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
      let filename = `facture_approuvee_${invoiceId}${format.extension}`
      
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
      console.error('Export failed:', error)
      const errorMessage = error instanceof Error ? error.message : 'Export failed'
      alert(`Erreur d'export ${format.name}: ${errorMessage}`)
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
          disabled={!!isExporting}
        >
          {isExporting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Export...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              Exporter
              <ChevronDown className="h-3 w-3" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Download className="h-4 w-4" />
          Formats d'Export Disponibles
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {/* Standard Formats */}
        <div className="px-2 py-1">
          <div className="text-xs font-medium text-muted-foreground mb-1">Formats Standard</div>
          {standardFormats.map((format) => (
            <DropdownMenuItem
              key={format.id}
              onClick={() => handleExport(format)}
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
              onClick={() => handleExport(format)}
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
          💡 Les exports utilisent les données révisées et approuvées
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}