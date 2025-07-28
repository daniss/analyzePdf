'use client'

import { useState } from 'react'
import { FileText, Zap, Bot, DollarSign } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ProcessingMode } from '@/lib/types'
import { FileUploadProgressive } from './file-upload-progressive'

export function BatchProcessor() {
  const [batchMode, setBatchMode] = useState<ProcessingMode>('auto')
  const [isExpanded, setIsExpanded] = useState(false)

  const batchStats = {
    auto: {
      estimatedCost: '€0.15 - €4.50',
      timePerInvoice: '3-10s',
      accuracy: '95-99%'
    },
    fast: {
      estimatedCost: '€0.15',
      timePerInvoice: '2s',
      accuracy: '85-90%'
    },
    detailed: {
      estimatedCost: '€4.50',
      timePerInvoice: '10s',
      accuracy: '99%'
    }
  }

  return (
    <Card className="card-modern">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-2xl">Batch Processing</CardTitle>
            <CardDescription className="text-lg mt-2">
              Process multiple invoices with optimized tier selection
            </CardDescription>
          </div>
          <Button
            variant="outline"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        </div>
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="space-y-6">
          {/* Mode Selection */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Batch Processing Mode</h3>
            <Select value={batchMode} onValueChange={(value) => setBatchMode(value as ProcessingMode)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">
                  <div className="flex items-center gap-3">
                    <Zap className="h-4 w-4 text-blue-600" />
                    <span>Auto Mode - Smart tier selection per invoice</span>
                  </div>
                </SelectItem>
                <SelectItem value="fast">
                  <div className="flex items-center gap-3">
                    <Zap className="h-4 w-4 text-green-600" />
                    <span>Fast Mode - All invoices use Tier 1</span>
                  </div>
                </SelectItem>
                <SelectItem value="detailed">
                  <div className="flex items-center gap-3">
                    <Bot className="h-4 w-4 text-purple-600" />
                    <span>Detailed Mode - All invoices use full AI</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Batch Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <DollarSign className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Est. Cost (150 invoices)</p>
              <p className="text-sm font-semibold">{batchStats[batchMode].estimatedCost}</p>
            </div>
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <Zap className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Time per Invoice</p>
              <p className="text-sm font-semibold">{batchStats[batchMode].timePerInvoice}</p>
            </div>
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <FileText className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Accuracy</p>
              <p className="text-sm font-semibold">{batchStats[batchMode].accuracy}</p>
            </div>
          </div>

          {/* File Upload */}
          <div className="pt-4">
            <FileUploadProgressive maxFiles={150} />
          </div>

          {/* Batch Features */}
          <div className="grid grid-cols-2 gap-4 pt-4">
            <Card className="p-4 bg-muted/30">
              <h4 className="font-medium text-sm mb-2">Batch Features</h4>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li>• Parallel processing up to 10 invoices</li>
                <li>• Automatic retry on failures</li>
                <li>• Real-time progress tracking</li>
                <li>• Bulk export when complete</li>
              </ul>
            </Card>
            <Card className="p-4 bg-muted/30">
              <h4 className="font-medium text-sm mb-2">Cost Optimization</h4>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li>• Volume discounts available</li>
                <li>• Smart tier selection saves 80%+</li>
                <li>• Preview cost before processing</li>
                <li>• Monthly usage reports</li>
              </ul>
            </Card>
          </div>
        </CardContent>
      )}
    </Card>
  )
}