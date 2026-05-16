import { cn } from '@/lib/utils'
import { ButtonHTMLAttributes, forwardRef } from 'react'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none',
        {
          default: 'bg-blue-600 text-white hover:bg-blue-700',
          destructive: 'bg-red-600 text-white hover:bg-red-700',
          outline: 'border border-gray-300 bg-white hover:bg-gray-50 text-gray-700',
          ghost: 'hover:bg-gray-100 text-gray-700',
          link: 'text-blue-600 underline-offset-4 hover:underline p-0',
        }[variant],
        { default: 'px-4 py-2', sm: 'px-3 py-1.5 text-xs', lg: 'px-6 py-3 text-base' }[size],
        className
      )}
      {...props}
    />
  )
)
Button.displayName = 'Button'
