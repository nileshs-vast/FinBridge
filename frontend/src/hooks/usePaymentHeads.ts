import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PaymentHeadOut } from '@/types/api'

export function usePaymentHeads(company_id?: string) {
  return useQuery({
    queryKey: ['payment-heads', company_id],
    queryFn: () =>
      api.get<PaymentHeadOut[]>(`/companies/${company_id}/payment-heads`).then(r => r.data),
    enabled: !!company_id,
  })
}
