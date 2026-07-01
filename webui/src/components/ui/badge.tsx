import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-mono transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default:
          'border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 text-cyber-neon-cyan',
        secondary:
          'border-cyber-border-DEFAULT bg-cyber-bg-tertiary text-cyber-text-secondary',
        destructive:
          'border-cyber-neon-pink/30 bg-cyber-neon-pink/10 text-cyber-neon-pink',
        outline:
          'border-cyber-border-DEFAULT text-cyber-text-primary',
        success:
          'border-cyber-neon-green/30 bg-cyber-neon-green/10 text-cyber-neon-green shadow-glow-green-sm',
        warning:
          'border-cyber-neon-orange/30 bg-cyber-neon-orange/10 text-cyber-neon-orange',
        idle:
          'border-cyber-border-DEFAULT bg-cyber-bg-tertiary text-cyber-text-muted',
        running:
          'border-cyber-neon-green/50 bg-cyber-neon-green/20 text-cyber-neon-green shadow-glow-green-sm animate-pulse-fast',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
