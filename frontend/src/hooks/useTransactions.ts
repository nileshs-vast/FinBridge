import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { TransactionOut, TransactionUploadResponse } from '@/types/api'

export function useTransactions(params?: { status?: string; type?: string; company_id?: string }) {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: () => api.get<TransactionOut[]>('/transactions', { params }).then(r => r.data),
  })
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: ['transaction', id],
    queryFn: () => api.get<TransactionOut>(`/transactions/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

export function useUploadTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.post<TransactionUploadResponse>('/transactions/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}

export function usePatchTransaction(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<TransactionOut>) =>
      api.patch<TransactionOut>(`/transactions/${id}`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transaction', id] })
    },
  })
}

export function useSubmitTransaction(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<TransactionOut>(`/transactions/${id}/submit`).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transaction', id] })
    },
  })
}

export interface ManualTransactionPayload {
  transaction_type: 'payment' | 'salary_register'
  direction: 'payment_in' | 'payment_out' | null
  vendor: string
  invoice_no?: string | null
  transaction_date: string
  amount: number
  currency: string
  payment_head_id?: string | null
  notes?: string | null
}

export function useCreateManualTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ManualTransactionPayload) =>
      api.post<TransactionOut>('/transactions/manual', payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })
}
