import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface AuditLogEntry {
  id: number
  actor_user_id: string
  action: string
  entity_type: string
  entity_id: string
  payload: Record<string, unknown> | null
  created_at: string
}

export function useTransactionAudit(transactionId: string) {
  return useQuery({
    queryKey: ['audit', transactionId],
    queryFn: () =>
      api
        .get<AuditLogEntry[]>('/audit', { params: { entity_id: transactionId } })
        .then(r => r.data),
    enabled: !!transactionId,
  })
}
