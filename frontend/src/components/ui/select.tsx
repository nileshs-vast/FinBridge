import { cn } from '@/lib/utils'
import { SelectHTMLAttributes, forwardRef } from 'react'
import React from 'react'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  onValueChange?: (value: string) => void
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, onValueChange, onChange, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50',
        className
      )}
      onChange={(e) => {
        onChange?.(e)
        onValueChange?.(e.target.value)
      }}
      {...props}
    >
      {children}
    </select>
  )
)
Select.displayName = 'Select'

export function SelectTrigger(_props: { children?: React.ReactNode; className?: string }) {
  return null
}
export function SelectValue(_props: { placeholder?: string }) {
  return null
}
export function SelectContent({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
export function SelectItem({ value, children }: { value: string; children: React.ReactNode }) {
  return <option value={value}>{children}</option>
}
