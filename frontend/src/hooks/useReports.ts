import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ReportOut } from '@/types/api'

export function useReports(company_id?: string) {
  return useQuery({
    queryKey: ['reports', company_id],
    queryFn: () => api.get<ReportOut[]>('/reports', { params: { company_id } }).then(r => r.data),
  })
}
