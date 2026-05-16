import { Badge } from '@/components/ui/badge'
import type { TransactionStatus } from '@/types/api'

const STATUS_CONFIG: Record<TransactionStatus, { variant: 'secondary' | 'warning' | 'success' | 'destructive'; label: string }> = {
  draft_ai:       { variant: 'secondary',    label: 'Draft AI' },
  pending_review: { variant: 'warning',      label: 'Pending Review' },
  needs_info:     { variant: 'warning',      label: 'Needs Info' },
  accepted:       { variant: 'success',      label: 'Accepted' },
  rejected:       { variant: 'destructive',  label: 'Rejected' },
}

interface StatusBadgeProps {
  status: TransactionStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const { variant, label } = STATUS_CONFIG[status] ?? { variant: 'secondary', label: status }
  return <Badge variant={variant}>{label}</Badge>
}
