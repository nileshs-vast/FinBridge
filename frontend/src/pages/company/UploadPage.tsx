import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2, AlertTriangle } from 'lucide-react'
import { AppLayout } from '@/components/layout/AppLayout'
import { FileDropzone } from '@/components/upload/FileDropzone'
import { ExtractionPreviewForm, type PatchData } from '@/components/upload/ExtractionPreviewForm'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useUploadTransaction, usePatchTransaction, useSubmitTransaction } from '@/hooks/useTransactions'
import { useAuthStore } from '@/store/authStore'
import type { TransactionType, TransactionDirection, TransactionUploadResponse } from '@/types/api'

type Stage = 'idle' | 'uploading' | 'preview' | 'submitting' | 'submitted'

export default function UploadPage() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const companyId = user?.company_id ?? ''

  const [stage, setStage] = useState<Stage>('idle')
  const [txType, setTxType] = useState<TransactionType>('invoice')
  const [direction, setDirection] = useState<TransactionDirection>('purchase')
  const [uploadResult, setUploadResult] = useState<TransactionUploadResponse | null>(null)

  // Manual form fields (non-invoice types)
  const [manualVendor, setManualVendor] = useState('')
  const [manualAmount, setManualAmount] = useState('')
  const [manualDate, setManualDate] = useState('')
  const [manualNotes, setManualNotes] = useState('')

  const uploadMutation = useUploadTransaction()

  const transactionId = uploadResult?.transaction.id ?? ''
  const patchMutation = usePatchTransaction(transactionId)
  const submitMutation = useSubmitTransaction(transactionId)

  async function handleFile(file: File) {
    setStage('uploading')
    const fd = new FormData()
    fd.append('file', file)
    fd.append('transaction_type', txType)
    if (direction) fd.append('direction', direction)

    try {
      const result = await uploadMutation.mutateAsync(fd)
      setUploadResult(result)
      setStage('preview')
    } catch {
      toast.error('Upload failed. Please try again.')
      setStage('idle')
    }
  }

  async function handlePreviewSubmit(patch: PatchData, paymentHeadId: string | null) {
    if (!transactionId) return
    setStage('submitting')
    try {
      await patchMutation.mutateAsync({ ...patch, payment_head_id: paymentHeadId ?? undefined } as never)
      const submitted = await submitMutation.mutateAsync()
      if (submitted.possible_duplicate_of) {
        toast.warning('Possible duplicate of an existing transaction.')
      } else {
        toast.success('Transaction submitted for review.')
      }
      navigate('/company/transactions')
    } catch {
      toast.error('Submission failed. Please try again.')
      setStage('preview')
    }
  }

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!transactionId) return
    setStage('submitting')
    try {
      await patchMutation.mutateAsync({
        vendor: manualVendor || undefined,
        amount: manualAmount ? parseFloat(manualAmount) : undefined,
        transaction_date: manualDate || undefined,
        direction,
        notes: manualNotes || undefined,
      } as never)
      await submitMutation.mutateAsync()
      toast.success('Transaction submitted for review.')
      navigate('/company/transactions')
    } catch {
      toast.error('Submission failed. Please try again.')
      setStage('preview')
    }
  }

  const hasExtractionError =
    uploadResult?.transaction?.raw_extraction != null &&
    'error' in (uploadResult.transaction.raw_extraction as Record<string, unknown>)

  const isSubmitting = stage === 'submitting'

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Document</h1>
        <p className="text-gray-500 mt-1">Upload an invoice, payment record, or salary register for AI extraction.</p>
      </div>

      {/* Step 1: idle */}
      {stage === 'idle' && (
        <Card>
          <CardHeader>
            <CardTitle>Select document type</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>Document Type</Label>
                <Select value={txType} onValueChange={v => setTxType(v as TransactionType)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="invoice">Invoice</SelectItem>
                    <SelectItem value="payment">Payment</SelectItem>
                    <SelectItem value="salary_register">Salary Register</SelectItem>
                    <SelectItem value="bank_statement">Bank Statement</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Direction</Label>
                <Select value={direction} onValueChange={v => setDirection(v as TransactionDirection)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="purchase">Purchase</SelectItem>
                    <SelectItem value="sales">Sales</SelectItem>
                    <SelectItem value="payment_in">Payment In</SelectItem>
                    <SelectItem value="payment_out">Payment Out</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <FileDropzone onFile={handleFile} />
          </CardContent>
        </Card>
      )}

      {/* Step 2: uploading */}
      {stage === 'uploading' && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-4">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="text-gray-600 font-medium">AI extracting your document…</p>
            <p className="text-sm text-gray-400">(may take up to 15s)</p>
          </CardContent>
        </Card>
      )}

      {/* Step 3a: preview — invoice type */}
      {stage === 'preview' && uploadResult && txType === 'invoice' && (
        <Card>
          <CardHeader>
            <CardTitle>Review Extracted Data</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {hasExtractionError && (
              <div className="flex items-start gap-2 rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm text-yellow-800">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>AI extraction encountered an issue. Please review and correct the fields below.</span>
              </div>
            )}
            <ExtractionPreviewForm
              extracted={uploadResult.extracted}
              companyId={companyId}
              onSubmit={handlePreviewSubmit}
              isSubmitting={isSubmitting}
            />
          </CardContent>
        </Card>
      )}

      {/* Step 3b: preview — non-invoice type (manual form) */}
      {stage === 'preview' && uploadResult && txType !== 'invoice' && (
        <Card>
          <CardHeader>
            <CardTitle>Enter Details</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="m-vendor">Vendor / Description</Label>
                <Input id="m-vendor" value={manualVendor} onChange={e => setManualVendor(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="m-amount">Amount</Label>
                  <Input id="m-amount" type="number" step="0.01" value={manualAmount} onChange={e => setManualAmount(e.target.value)} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="m-date">Date</Label>
                  <Input id="m-date" type="date" value={manualDate} onChange={e => setManualDate(e.target.value)} />
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="m-notes">Notes</Label>
                <Textarea id="m-notes" value={manualNotes} onChange={e => setManualNotes(e.target.value)} rows={3} />
              </div>
              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? 'Submitting…' : 'Submit for Review'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Step 4: submitting — button is disabled inline, no separate screen needed */}
    </div>
  )
}
