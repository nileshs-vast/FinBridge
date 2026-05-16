import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { StatusBadge } from '@/components/transactions/StatusBadge'
import { useTransactions } from '@/hooks/useTransactions'
import { Button } from '@/components/ui/button'
import type { TransactionStatus } from '@/types/api'

const STATUS_TABS: { label: string; value: TransactionStatus | 'all' }[] = [
  { label: 'All',            value: 'all' },
  { label: 'Draft AI',       value: 'draft_ai' },
  { label: 'Pending Review', value: 'pending_review' },
  { label: 'Needs Info',     value: 'needs_info' },
  { label: 'Accepted',       value: 'accepted' },
  { label: 'Rejected',       value: 'rejected' },
]

function formatAmount(amount: string | null, currency: string): string {
  if (amount == null) return '—'
  const num = parseFloat(amount)
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: currency || 'INR', maximumFractionDigits: 2 }).format(num)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function TransactionHistoryPage() {
  const [activeStatus, setActiveStatus] = useState<TransactionStatus | 'all'>('all')

  const { data: transactions, isLoading, isError } = useTransactions(
    activeStatus !== 'all' ? { status: activeStatus } : undefined
  )

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transaction History</h1>
        <p className="text-gray-500 mt-1">View and track all your submitted documents.</p>
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-3">
        {STATUS_TABS.map(tab => (
          <button
            key={tab.value}
            onClick={() => setActiveStatus(tab.value)}
            className={[
              'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
              activeStatus === tab.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <p className="text-gray-500 text-sm">Loading…</p>
      )}

      {isError && (
        <p className="text-red-500 text-sm">Failed to load transactions. Please refresh.</p>
      )}

      {!isLoading && !isError && transactions?.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
          <p className="text-gray-500">No transactions yet.</p>
          <Link to="/company/upload">
            <Button variant="outline">Upload your first document →</Button>
          </Link>
        </div>
      )}

      {!isLoading && !isError && transactions && transactions.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Vendor</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Invoice #</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Amount</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(tx => (
                <React.Fragment key={tx.id}>
                  <tr className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3"><StatusBadge status={tx.status} /></td>
                    <td className="px-4 py-3 capitalize text-gray-700">{tx.transaction_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3 text-gray-700">{tx.vendor ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{tx.invoice_no ?? '—'}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatAmount(tx.amount, tx.currency)}</td>
                    <td className="px-4 py-3 text-gray-600">{formatDate(tx.transaction_date)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(tx.created_at)}</td>
                  </tr>
                  {tx.status === 'needs_info' && tx.info_request_reason && (
                    <tr key={`${tx.id}-info`} className="border-t border-yellow-100 bg-yellow-50">
                      <td colSpan={7} className="px-4 py-2">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex items-start gap-2 text-sm text-yellow-800">
                            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                            <span>{tx.info_request_reason}</span>
                          </div>
                          <Link to="/company/upload">
                            <Button size="sm" variant="outline" className="border-yellow-400 text-yellow-800 hover:bg-yellow-100 shrink-0">
                              Edit &amp; Resubmit
                            </Button>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
