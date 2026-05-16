import { useDashboardSummary } from '@/hooks/useDashboard'
import { StatusBadge } from '@/components/transactions/StatusBadge'
import type { TransactionStatus } from '@/types/api'

const ALL_STATUSES: TransactionStatus[] = [
  'draft_ai',
  'pending_review',
  'needs_info',
  'accepted',
  'rejected',
]

export default function DashboardPage() {
  const { data, isLoading, isError } = useDashboardSummary()

  if (isLoading) return <div className="p-6">Loading...</div>
  if (isError) return <div className="p-6 text-red-600">Failed to load dashboard.</div>

  const countMap = Object.fromEntries(
    (data?.counts_by_status ?? []).map(s => [s.status, s.count])
  )

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Status counts */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Transaction Status</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {ALL_STATUSES.map(status => (
            <div key={status} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-3xl font-bold text-gray-900">
                {countMap[status] ?? 0}
              </div>
              <div className="mt-1">
                <StatusBadge status={status} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Top expense heads */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Top Expense Heads</h2>
        {(!data?.top_expense_heads || data.top_expense_heads.length === 0) ? (
          <p className="text-gray-500">No accepted transactions yet</p>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Payment Head</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Total (INR)</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.top_expense_heads.map(h => (
                  <tr key={h.payment_head_id}>
                    <td className="px-4 py-3">{h.name}</td>
                    <td className="px-4 py-3 text-right font-medium">
                      {Number(h.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Recent transactions */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Recent Transactions</h2>
        {(!data?.recent_transactions || data.recent_transactions.length === 0) ? (
          <p className="text-gray-500">No transactions yet.</p>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Vendor</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Amount</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.recent_transactions.map(tx => (
                  <tr key={tx.id}>
                    <td className="px-4 py-3">{tx.vendor ?? '—'}</td>
                    <td className="px-4 py-3 capitalize">{tx.transaction_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3 text-right">
                      {tx.amount
                        ? `${tx.currency} ${Number(tx.amount).toLocaleString()}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tx.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {(tx.transaction_date ?? tx.created_at).slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
