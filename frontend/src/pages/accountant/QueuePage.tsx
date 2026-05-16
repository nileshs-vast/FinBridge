import { useNavigate } from 'react-router-dom'
import { useTransactions } from '@/hooks/useTransactions'
import { StatusBadge } from '@/components/transactions/StatusBadge'
import { Badge } from '@/components/ui/badge'
import type { TransactionOut } from '@/types/api'

function TransactionCard({ tx }: { tx: TransactionOut }) {
  const navigate = useNavigate()
  const date = tx.transaction_date ?? tx.created_at.slice(0, 10)
  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-4 cursor-pointer hover:shadow-md transition-shadow"
      onClick={() => navigate(`/accountant/transactions/${tx.id}`)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">
              {tx.vendor ?? 'Unknown vendor'}
            </span>
            <Badge variant="secondary" className="capitalize">
              {tx.transaction_type.replace('_', ' ')}
            </Badge>
            {tx.possible_duplicate_of && (
              <Badge variant="warning">⚠ Possible duplicate</Badge>
            )}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            Company: {tx.company_id} &nbsp;·&nbsp; {date}
            {tx.invoice_no && <> &nbsp;·&nbsp; #{tx.invoice_no}</>}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="font-semibold text-gray-900">
            {tx.amount ? `${tx.currency} ${Number(tx.amount).toLocaleString()}` : '—'}
          </div>
          <div className="mt-1">
            <StatusBadge status={tx.status} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function QueuePage() {
  const { data: transactions, isLoading, isError } = useTransactions({ status: 'pending_review' })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Review Queue</h1>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-gray-100 rounded-lg h-20 animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="bg-red-50 text-red-700 rounded p-4">Failed to load queue.</div>
      )}

      {!isLoading && !isError && transactions?.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          Queue is empty — all transactions reviewed!
        </div>
      )}

      {!isLoading && !isError && transactions && transactions.length > 0 && (
        <div className="space-y-3">
          {transactions.map(tx => (
            <TransactionCard key={tx.id} tx={tx} />
          ))}
        </div>
      )}
    </div>
  )
}
