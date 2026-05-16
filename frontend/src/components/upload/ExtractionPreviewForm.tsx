import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { usePaymentHeads } from '@/hooks/usePaymentHeads'
import type { ExtractedInvoice, TransactionDirection } from '@/types/api'
import { ChevronDown, ChevronUp } from 'lucide-react'

export interface PatchData {
  vendor?: string
  invoice_no?: string
  transaction_date?: string
  amount?: number
  currency?: string
  direction?: TransactionDirection
  notes?: string
}

interface Props {
  extracted: ExtractedInvoice
  companyId: string
  onSubmit: (patch: PatchData, paymentHeadId: string | null) => void
  isSubmitting: boolean
}

function confidencePct(value: number): string {
  return `${Math.round(value * 100)}% confident`
}

export function ExtractionPreviewForm({ extracted, companyId, onSubmit, isSubmitting }: Props) {
  const [vendor, setVendor] = useState(extracted.vendor ?? '')
  const [invoiceNo, setInvoiceNo] = useState(extracted.invoice_no ?? '')
  const [date, setDate] = useState(extracted.invoice_date ?? '')
  const [amount, setAmount] = useState<string>(extracted.total != null ? String(extracted.total) : '')
  const [currency, setCurrency] = useState(extracted.currency ?? 'INR')
  const [direction, setDirection] = useState<TransactionDirection>(
    extracted.suggested_direction ?? 'purchase'
  )
  const [notes, setNotes] = useState(extracted.notes ?? '')
  const [parentHeadId, setParentHeadId] = useState<string | null>(null)
  const [childHeadId, setChildHeadId] = useState<string | null>(null)
  const [lineItemsOpen, setLineItemsOpen] = useState(false)

  const { data: heads = [] } = usePaymentHeads(companyId)

  const selectedParent = heads.find(h => h.id === parentHeadId)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const patch: PatchData = {
      vendor: vendor || undefined,
      invoice_no: invoiceNo || undefined,
      transaction_date: date || undefined,
      amount: amount ? parseFloat(amount) : undefined,
      currency: currency || undefined,
      direction,
      notes: notes || undefined,
    }
    onSubmit(patch, childHeadId ?? parentHeadId)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Vendor */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Label htmlFor="vendor">Vendor</Label>
          {extracted.confidence?.vendor != null && (
            <Badge variant="secondary" className="text-xs">
              {confidencePct(extracted.confidence.vendor)}
            </Badge>
          )}
        </div>
        <Input id="vendor" value={vendor} onChange={e => setVendor(e.target.value)} placeholder="Vendor name" />
      </div>

      {/* Invoice # */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Label htmlFor="invoice_no">Invoice #</Label>
          {extracted.confidence?.invoice_no != null && (
            <Badge variant="secondary" className="text-xs">
              {confidencePct(extracted.confidence.invoice_no)}
            </Badge>
          )}
        </div>
        <Input id="invoice_no" value={invoiceNo} onChange={e => setInvoiceNo(e.target.value)} placeholder="INV-001" />
      </div>

      {/* Date */}
      <div className="space-y-1">
        <Label htmlFor="date">Date</Label>
        <Input id="date" type="date" value={date} onChange={e => setDate(e.target.value)} />
      </div>

      {/* Amount + Currency */}
      <div className="flex gap-3">
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor="amount">Amount</Label>
            {extracted.confidence?.total != null && (
              <Badge variant="secondary" className="text-xs">
                {confidencePct(extracted.confidence.total)}
              </Badge>
            )}
          </div>
          <Input
            id="amount"
            type="number"
            step="0.01"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="w-28 space-y-1">
          <Label htmlFor="currency">Currency</Label>
          <Input id="currency" value={currency} onChange={e => setCurrency(e.target.value)} placeholder="INR" />
        </div>
      </div>

      {/* Direction */}
      <div className="space-y-1">
        <Label>Direction</Label>
        <Select value={direction} onValueChange={v => setDirection(v as TransactionDirection)}>
          <SelectTrigger>
            <SelectValue placeholder="Select direction" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="purchase">Purchase</SelectItem>
            <SelectItem value="sales">Sales</SelectItem>
            <SelectItem value="payment_in">Payment In</SelectItem>
            <SelectItem value="payment_out">Payment Out</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Payment Head — two-level */}
      {heads.length > 0 && (
        <div className="space-y-2">
          <Label>Payment Head</Label>
          <Select value={parentHeadId ?? ''} onValueChange={v => { setParentHeadId(v || null); setChildHeadId(null) }}>
            <SelectTrigger>
              <SelectValue placeholder="Select category" />
            </SelectTrigger>
            <SelectContent>
              {heads.map(h => (
                <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedParent && selectedParent.children.length > 0 && (
            <Select value={childHeadId ?? ''} onValueChange={v => setChildHeadId(v || null)}>
              <SelectTrigger>
                <SelectValue placeholder="Select sub-category" />
              </SelectTrigger>
              <SelectContent>
                {selectedParent.children.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      {/* Notes */}
      <div className="space-y-1">
        <Label htmlFor="notes">Notes</Label>
        <Textarea id="notes" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Any additional notes…" rows={3} />
      </div>

      {/* GST Summary */}
      {(extracted.cgst != null || extracted.igst != null) && (
        <div className="rounded-md bg-gray-50 border border-gray-200 p-3 text-sm space-y-1">
          <p className="font-medium text-gray-700">GST Summary</p>
          {extracted.cgst != null && <p className="text-gray-600">CGST: ₹{extracted.cgst.toFixed(2)}</p>}
          {extracted.sgst != null && <p className="text-gray-600">SGST: ₹{extracted.sgst.toFixed(2)}</p>}
          {extracted.igst != null && <p className="text-gray-600">IGST: ₹{extracted.igst.toFixed(2)}</p>}
        </div>
      )}

      {/* Line Items */}
      {extracted.line_items.length > 0 && (
        <div className="rounded-md border border-gray-200 overflow-hidden">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-2 bg-gray-50 text-sm font-medium text-gray-700 hover:bg-gray-100"
            onClick={() => setLineItemsOpen(o => !o)}
          >
            <span>Line Items ({extracted.line_items.length})</span>
            {lineItemsOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {lineItemsOpen && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 border-t border-gray-200">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Description</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Qty</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Unit Price</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {extracted.line_items.map((item, i) => (
                    <tr key={i} className="border-t border-gray-100">
                      <td className="px-3 py-2 text-gray-700">{item.description}</td>
                      <td className="px-3 py-2 text-right text-gray-600">{item.quantity ?? '-'}</td>
                      <td className="px-3 py-2 text-right text-gray-600">{item.unit_price != null ? `₹${item.unit_price}` : '-'}</td>
                      <td className="px-3 py-2 text-right text-gray-700">₹{item.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? 'Submitting…' : 'Submit for Review'}
      </Button>
    </form>
  )
}
