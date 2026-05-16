import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { TransactionOut } from '@/types/api'

export function useApproveTransaction(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api.post<TransactionOut>(`/transactions/${id}/approve`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transaction', id] })
    },
  })
}

export function useRejectTransaction(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) =>
      api.post<TransactionOut>(`/transactions/${id}/reject`, { reason }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transaction', id] })
    },
  })
}

export function useRequestInfo(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) =>
      api
        .post<TransactionOut>(`/transactions/${id}/request-info`, { reason })
        .then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transaction', id] })
    },
  })
}
