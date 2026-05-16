import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateManualTransaction } from '@/hooks/useTransactions'
import { usePaymentHeads } from '@/hooks/usePaymentHeads'
import { useAuthStore } from '@/store/authStore'
import type { PaymentHeadOut } from '@/types/api'

function flattenHeads(
  heads: PaymentHeadOut[],
  prefix = '',
): { id: string; label: string }[] {
  const result: { id: string; label: string }[] = []
  for (const h of heads) {
    const label = prefix ? `${prefix} › ${h.name}` : h.name
    result.push({ id: h.id, label })
    if (h.children?.length) {
      result.push(...flattenHeads(h.children, label))
    }
  }
  return result
}

export default function ManualTransactionPage() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)
  const companyId = user?.company_id ?? ''

  const [txType, setTxType] = useState<'payment' | 'salary_register'>('payment')
  const [direction, setDirection] = useState<'payment_in' | 'payment_out'>('payment_out')
  const [vendor, setVendor] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState('')
  const [paymentHeadId, setPaymentHeadId] = useState<string>('none')
  const [notes, setNotes] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const mutation = useCreateManualTransaction()
  const { data: rawHeads = [] } = usePaymentHeads(companyId)
  const paymentHeads = flattenHeads(rawHeads)

  function validate() {
    const e: Record<string, string> = {}
    if (!vendor.trim()) e.vendor = 'Vendor / description is required.'
    const amt = parseFloat(amount)
    if (!amount || isNaN(amt) || amt <= 0) e.amount = 'A positive amount is required.'
    if (!date) e.date = 'Transaction date is required.'
    return e
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) {
      setErrors(errs)
      return
    }
    setErrors({})
    try {
      await mutation.mutateAsync({
        transaction_type: txType,
        direction: txType === 'salary_register' ? null : direction,
        vendor: vendor.trim(),
        transaction_date: date,
        amount: parseFloat(amount),
        currency: 'INR',
        payment_head_id: paymentHeadId === 'none' ? null : paymentHeadId,
        notes: notes.trim() || null,
      })
      toast.success('Transaction submitted for review.')
      navigate('/company/transactions')
    } catch {
      toast.error('Submission failed. Please try again.')
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Manual Transaction Entry</h1>
        <p className="text-gray-500 mt-1">
          Enter transaction details directly without uploading a document.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Transaction Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>Transaction Type</Label>
                <Select
                  value={txType}
                  onValueChange={v => setTxType(v as 'payment' | 'salary_register')}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="payment">Payment</SelectItem>
                    <SelectItem value="salary_register">Salary Register</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {txType === 'payment' && (
                <div className="space-y-1">
                  <Label>Direction</Label>
                  <Select
                    value={direction}
                    onValueChange={v => setDirection(v as 'payment_in' | 'payment_out')}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="payment_out">Money Out</SelectItem>
                      <SelectItem value="payment_in">Money In</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="vendor">
                Vendor / Description <span className="text-red-500">*</span>
              </Label>
              <Input
                id="vendor"
                value={vendor}
                onChange={e => setVendor(e.target.value)}
                placeholder="e.g. HDFC Bank"
              />
              {errors.vendor && <p className="text-xs text-red-500">{errors.vendor}</p>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label htmlFor="amount">
                  Amount (INR) <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="0.00"
                />
                {errors.amount && <p className="text-xs text-red-500">{errors.amount}</p>}
              </div>

              <div className="space-y-1">
                <Label htmlFor="date">
                  Transaction Date <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="date"
                  type="date"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                />
                {errors.date && <p className="text-xs text-red-500">{errors.date}</p>}
              </div>
            </div>

            {paymentHeads.length > 0 && (
              <div className="space-y-1">
                <Label>
                  Payment Head{' '}
                  <span className="text-gray-400 text-xs">(optional)</span>
                </Label>
                <Select value={paymentHeadId} onValueChange={setPaymentHeadId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a payment head…" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {paymentHeads.map(ph => (
                      <SelectItem key={ph.id} value={ph.id}>
                        {ph.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-1">
              <Label htmlFor="notes">
                Notes <span className="text-gray-400 text-xs">(optional)</span>
              </Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Any additional context…"
                rows={3}
              />
            </div>

            <Button type="submit" disabled={mutation.isPending} className="w-full">
              {mutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting…
                </>
              ) : (
                'Submit for Review'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
