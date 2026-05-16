import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { FirmOut, CompanyOut, PaymentHeadOut, UserOut } from '@/types/api'

export function useFirms() {
  return useQuery({
    queryKey: ['firms'],
    queryFn: () => api.get<FirmOut[]>('/firms').then(r => r.data),
  })
}

export function useCreateFirm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; admin_email: string; admin_password: string }) =>
      api.post<FirmOut>('/firms', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['firms'] }),
  })
}

export function useCompanies() {
  return useQuery({
    queryKey: ['companies'],
    queryFn: () => api.get<CompanyOut[]>('/companies').then(r => r.data),
  })
}

export function useCreateCompany() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      name: string
      business_type: 'manufacturing' | 'it' | 'services'
      admin_email: string
      admin_password: string
    }) => api.post<CompanyOut>('/companies', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  })
}

export function usePaymentHeadsOnboarding(companyId?: string) {
  return useQuery({
    queryKey: ['payment-heads', companyId],
    queryFn: () =>
      api.get<PaymentHeadOut[]>(`/companies/${companyId}/payment-heads`).then(r => r.data),
    enabled: !!companyId,
  })
}

export function useAddPaymentHead(companyId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; parent_head_id?: string }) =>
      api.post<PaymentHeadOut>(`/companies/${companyId}/payment-heads`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['payment-heads', companyId] }),
  })
}

export function useUsers(role?: string) {
  return useQuery({
    queryKey: ['users', role],
    queryFn: () => api.get<UserOut[]>('/users', { params: { role } }).then(r => r.data),
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      role: string
      email: string
      password: string
      company_id?: string
    }) => api.post<UserOut>('/users', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}
