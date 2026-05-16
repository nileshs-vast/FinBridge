import { cn } from '@/lib/utils'
import { LabelHTMLAttributes, forwardRef } from 'react'

export const Label = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label ref={ref} className={cn('text-sm font-medium text-gray-700', className)} {...props} />
  )
)
Label.displayName = 'Label'
