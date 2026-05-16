import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { usePaymentHeadsOnboarding, useAddPaymentHead } from '@/hooks/useOnboarding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import type { PaymentHeadOut } from '@/types/api'

function HeadTree({ heads }: { heads: PaymentHeadOut[] }) {
  const parents = heads.filter(h => !h.parent_head_id)
  return (
    <ul className="space-y-2">
      {parents.map(p => (
        <li key={p.id}>
          <span className="font-semibold text-gray-900">{p.name}</span>
          {p.children && p.children.length > 0 && (
            <ul className="ml-6 mt-1 space-y-1">
              {p.children.map(c => (
                <li key={c.id} className="text-gray-700">— {c.name}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  )
}

export default function PaymentHeadsPage() {
  const { companyId = '' } = useParams<{ companyId: string }>()
  const { data: heads = [], isLoading, isError } = usePaymentHeadsOnboarding(companyId)
  const addHead = useAddPaymentHead(companyId)

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [parentId, setParentId] = useState('')

  const topLevelHeads = heads.filter(h => !h.parent_head_id)

  const handleAdd = () => {
    if (!name.trim()) { toast.error('Name is required'); return }
    addHead.mutate(
      { name: name.trim(), parent_head_id: parentId || undefined },
      {
        onSuccess: () => {
          toast.success('Payment head added')
          setOpen(false)
          setName(''); setParentId('')
        },
        onError: (err: unknown) => {
          const status = (err as any).response?.status
          const detail = (err as any).response?.data?.detail || 'Failed to add head'
          if (status === 409) toast.warning(detail)
          else toast.error(detail)
        },
      }
    )
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Payment Heads</h1>
        <Button onClick={() => setOpen(true)}>+ Add Head</Button>
      </div>

      {isLoading && <p className="text-gray-500">Loading...</p>}
      {isError && <p className="text-red-600">Failed to load payment heads.</p>}

      {!isLoading && !isError && heads.length === 0 && (
        <p className="text-gray-500">No payment heads yet.</p>
      )}

      {!isLoading && heads.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <HeadTree heads={heads} />
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Add Payment Head</h2>
            <div>
              <Label>Name</Label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Office Expenses" />
            </div>
            <div>
              <Label>Parent Head (optional)</Label>
              <Select value={parentId} onChange={e => setParentId(e.target.value)}>
                <option value="">— top level —</option>
                {topLevelHeads.map(h => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </Select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={addHead.isPending}>Cancel</Button>
              <Button onClick={handleAdd} disabled={addHead.isPending}>
                {addHead.isPending ? 'Adding…' : 'Add'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
