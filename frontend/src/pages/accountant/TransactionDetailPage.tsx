import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useTransaction, usePatchTransaction } from '@/hooks/useTransactions'
import { useApproveTransaction, useRejectTransaction, useRequestInfo } from '@/hooks/useAccountant'
import { usePaymentHeads } from '@/hooks/usePaymentHeads'
import { useTransactionAudit } from '@/hooks/useAudit'
import { api } from '@/lib/api'
import { StatusBadge } from '@/components/transactions/StatusBadge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { TransactionDirection } from '@/types/api'

function confidencePct(v: number): string {
  return `${Math.round(v * 100)}%`
}

function ConfidenceBadge({ value }: { value: number | undefined }) {
  if (value == null) return null
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? 'text-green-700 bg-green-50' : pct >= 50 ? 'text-yellow-700 bg-yellow-50' : 'text-red-700 bg-red-50'
  return (
    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-medium ${color}`}>
      {confidencePct(value)}
    </span>
  )
}

const ACTION_LABELS: Record<string, string> = {
  'transaction.upload': 'Uploaded',
  'transaction.submit': 'Submitted for review',
  'transaction.approve': 'Approved',
  'transaction.reject': 'Rejected',
  'transaction.request_info': 'Requested more info',
  'transaction.patch': 'Edited',
}

function ReasonDialog({
  title,
  open,
  onClose,
  onSubmit,
  loading,
}: {
  title: string
  open: boolean
  onClose: () => void
  onSubmit: (reason: string) => void
  loading: boolean
}) {
  const [reason, setReason] = useState('')
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>
        <Textarea
          placeholder="Enter reason..."
          value={reason}
          onChange={e => setReason(e.target.value)}
          rows={4}
        />
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={() => { if (reason.trim()) onSubmit(reason.trim()) }}
            disabled={loading || !reason.trim()}
          >
            Submit
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function TransactionDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: tx, isLoading, isError } = useTransaction(id)
  const patch = usePatchTransaction(id)
  const approve = useApproveTransaction(id)
  const reject = useRejectTransaction(id)
  const requestInfo = useRequestInfo(id)

  const { data: heads = [] } = usePaymentHeads(tx?.company_id)
  const { data: auditLog = [] } = useTransactionAudit(id)

  // Form state
  const [vendor, setVendor] = useState('')
  const [invoiceNo, setInvoiceNo] = useState('')
  const [txDate, setTxDate] = useState('')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('INR')
  const [direction, setDirection] = useState<TransactionDirection | ''>('')
  const [parentHeadId, setParentHeadId] = useState('')
  const [childHeadId, setChildHeadId] = useState('')
  const [notes, setNotes] = useState('')

  const [rejectOpen, setRejectOpen] = useState(false)
  const [requestInfoOpen, setRequestInfoOpen] = useState(false)
  const [attachmentUrl, setAttachmentUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let objectUrl: string
    api.get(`/transactions/${id}/attachment`, { responseType: 'blob' })
      .then(r => {
        objectUrl = URL.createObjectURL(r.data)
        setAttachmentUrl(objectUrl)
      })
      .catch(() => {})
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [id])

  // Effect 1: reset main form fields only when the transaction ID changes
  useEffect(() => {
    if (!tx) return
    setVendor(tx.vendor ?? '')
    setInvoiceNo(tx.invoice_no ?? '')
    setTxDate(tx.transaction_date ?? '')
    setAmount(tx.amount ?? '')
    setCurrency(tx.currency ?? 'INR')
    setDirection(tx.direction ?? '')
    setNotes(tx.notes ?? '')
  }, [tx?.id])

  // Tracks the last (tx.id, payment_head_id) combination we initialized selectors for.
  // Prevents background heads refetches from overwriting the accountant's unsaved edits.
  const headsInitKeyRef = useRef<string | null>(null)

  // Effect 2: set payment head selectors once per (tx.id, payment_head_id) combination
  useEffect(() => {
    const key = tx?.payment_head_id ? `${tx?.id}:${tx?.payment_head_id}` : null
    if (!key) {
      setParentHeadId('')
      setChildHeadId('')
      headsInitKeyRef.current = null
      return
    }
    if (headsInitKeyRef.current === key || heads.length === 0) return
    const head = heads.find(h => h.id === tx?.payment_head_id)
    if (head?.parent_head_id) {
      setParentHeadId(head.parent_head_id)
      setChildHeadId(head.id)
    } else if (head) {
      setParentHeadId(head.id)
      setChildHeadId('')
    }
    headsInitKeyRef.current = key
  }, [tx?.id, tx?.payment_head_id, heads])

  const parentHeads = heads.filter(h => !h.parent_head_id)
  const childHeads = heads.filter(h => h.parent_head_id === parentHeadId)

  const handleSave = () => {
    const data: Record<string, unknown> = {
      vendor: vendor || null,
      invoice_no: invoiceNo || null,
      transaction_date: txDate || null,
      amount: amount || null,
      currency,
      direction: direction || null,
      payment_head_id: childHeadId || parentHeadId || null,
      notes: notes || null,
    }
    patch.mutate(data, {
      onSuccess: () => toast.success('Changes saved'),
      onError: (err: unknown) => {
        const msg = (err as any).response?.data?.detail || 'Save failed'
        toast.error(msg)
      },
    })
  }

  const handleApprove = () => {
    approve.mutate(undefined, {
      onSuccess: () => {
        toast.success('Transaction approved')
        navigate('/accountant/queue')
      },
      onError: (err: unknown) => {
        toast.error((err as any).response?.data?.detail || 'Approve failed')
      },
    })
  }

  const handleReject = (reason: string) => {
    reject.mutate(reason, {
      onSuccess: () => {
        toast.success('Transaction rejected')
        setRejectOpen(false)
        navigate('/accountant/queue')
      },
      onError: (err: unknown) => {
        toast.error((err as any).response?.data?.detail || 'Reject failed')
      },
    })
  }

  const handleRequestInfo = (reason: string) => {
    requestInfo.mutate(reason, {
      onSuccess: () => {
        toast.success('Info requested')
        setRequestInfoOpen(false)
        navigate('/accountant/queue')
      },
      onError: (err: unknown) => {
        toast.error((err as any).response?.data?.detail || 'Request info failed')
      },
    })
  }

  if (isLoading) return <div className="p-6">Loading...</div>
  if (isError || !tx) return <div className="p-6 text-red-600">Failed to load transaction.</div>

  const attachment = tx.attachments?.[0]
  const isPdf = attachment?.mime_type === 'application/pdf'
  const isImage = attachment?.mime_type?.startsWith('image/')
  const isPending = tx.status === 'pending_review'

  const confidence = (tx.raw_extraction as any)?.confidence as Record<string, number> | undefined
  const conf = (field: string) => confidence?.[field]

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      {/* LEFT PANEL */}
      <div className="w-1/2 overflow-y-auto border-r border-gray-200 p-6 bg-gray-50">
        <h2 className="text-lg font-semibold mb-4">Original Document</h2>
        {attachment ? (
          <>
            {isImage && attachmentUrl && (
              <img
                src={attachmentUrl}
                alt="document"
                className="max-w-full rounded border"
              />
            )}
            {isPdf && attachmentUrl && (
              <iframe
                src={attachmentUrl}
                className="w-full min-h-[600px] rounded border"
                title="document"
              />
            )}
            {attachmentUrl && (
              <a
                href={attachmentUrl}
                download={attachment.original_name}
                className="inline-block mt-3 text-sm text-blue-600 hover:underline"
              >
                Download original ({attachment.original_name})
              </a>
            )}
          </>
        ) : (
          <p className="text-gray-500 text-sm">No attachment.</p>
        )}

        {tx.raw_extraction && (
          <details className="mt-6">
            <summary className="cursor-pointer text-sm font-medium text-gray-600">
              Raw extraction JSON
            </summary>
            <pre className="mt-2 text-xs bg-white rounded border p-3 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(tx.raw_extraction, null, 2)}
            </pre>
          </details>
        )}

        {auditLog.length > 0 && (
          <details className="mt-4" open>
            <summary className="cursor-pointer text-sm font-medium text-gray-600">
              Audit trail ({auditLog.length})
            </summary>
            <ol className="mt-3 space-y-2">
              {auditLog.map(entry => (
                <li key={entry.id} className="flex items-start gap-2 text-xs text-gray-600">
                  <span className="mt-0.5 w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                  <div>
                    <span className="font-medium text-gray-800">
                      {ACTION_LABELS[entry.action] ?? entry.action}
                    </span>
                    <span className="text-gray-400 ml-1">
                      · {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div className="w-1/2 overflow-y-auto p-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Review</h2>
          <StatusBadge status={tx.status} />
        </div>

        {tx.possible_duplicate_of && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-yellow-800">
            ⚠ Possible duplicate of transaction {tx.possible_duplicate_of}
          </div>
        )}
        {tx.info_request_reason && (
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
            Info requested: {tx.info_request_reason}
          </div>
        )}
        {tx.rejection_reason && (
          <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
            Rejected: {tx.rejection_reason}
          </div>
        )}

        {/* Editable fields */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Vendor<ConfidenceBadge value={conf('vendor')} /></Label>
            <Input value={vendor} onChange={e => setVendor(e.target.value)} disabled={!isPending} />
          </div>
          <div>
            <Label>Invoice #<ConfidenceBadge value={conf('invoice_no')} /></Label>
            <Input value={invoiceNo} onChange={e => setInvoiceNo(e.target.value)} disabled={!isPending} />
          </div>
          <div>
            <Label>Date<ConfidenceBadge value={conf('invoice_date')} /></Label>
            <Input type="date" value={txDate} onChange={e => setTxDate(e.target.value)} disabled={!isPending} />
          </div>
          <div>
            <Label>Amount<ConfidenceBadge value={conf('total')} /></Label>
            <Input type="number" value={amount} onChange={e => setAmount(e.target.value)} disabled={!isPending} />
          </div>
          <div>
            <Label>Currency</Label>
            <Input value={currency} onChange={e => setCurrency(e.target.value)} disabled={!isPending} />
          </div>
          <div>
            <Label>Direction</Label>
            <Select
              value={direction}
              onChange={e => setDirection(e.target.value as TransactionDirection | '')}
              disabled={!isPending}
            >
              <option value="">— none —</option>
              <option value="purchase">Purchase</option>
              <option value="sales">Sales</option>
              <option value="payment_in">Payment In</option>
              <option value="payment_out">Payment Out</option>
            </Select>
          </div>
        </div>

        {/* Payment head cascade */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Payment Head (parent)</Label>
            <Select
              value={parentHeadId}
              onChange={e => { setParentHeadId(e.target.value); setChildHeadId('') }}
              disabled={!isPending}
            >
              <option value="">— none —</option>
              {parentHeads.map(h => (
                <option key={h.id} value={h.id}>{h.name}</option>
              ))}
            </Select>
          </div>
          {childHeads.length > 0 && (
            <div>
              <Label>Payment Head (sub)</Label>
              <Select
                value={childHeadId}
                onChange={e => setChildHeadId(e.target.value)}
                disabled={!isPending}
              >
                <option value="">— none —</option>
                {childHeads.map(h => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </Select>
            </div>
          )}
        </div>

        <div>
          <Label>Notes</Label>
          <Textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={3}
            disabled={!isPending}
          />
        </div>

        {isPending && (
          <Button onClick={handleSave} disabled={patch.isPending} variant="outline">
            {patch.isPending ? 'Saving…' : 'Save Changes'}
          </Button>
        )}

        {/* Action bar */}
        {isPending && (
          <div className="flex gap-3 pt-2 border-t border-gray-200 mt-auto">
            <Button
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={handleApprove}
              disabled={approve.isPending}
            >
              {approve.isPending ? 'Approving…' : 'Approve'}
            </Button>
            <Button
              variant="destructive"
              onClick={() => setRejectOpen(true)}
              disabled={reject.isPending}
            >
              Reject
            </Button>
            <Button
              className="bg-orange-500 hover:bg-orange-600 text-white"
              onClick={() => setRequestInfoOpen(true)}
              disabled={requestInfo.isPending}
            >
              Request Info
            </Button>
          </div>
        )}
      </div>

      <ReasonDialog
        title="Reject Transaction"
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        onSubmit={handleReject}
        loading={reject.isPending}
      />
      <ReasonDialog
        title="Request More Information"
        open={requestInfoOpen}
        onClose={() => setRequestInfoOpen(false)}
        onSubmit={handleRequestInfo}
        loading={requestInfo.isPending}
      />
    </div>
  )
}
