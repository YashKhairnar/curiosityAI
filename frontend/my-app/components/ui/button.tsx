import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-300 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-neon-blue focus-visible:ring-opacity-50 hover:scale-105 active:scale-95",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-neon-blue to-neon-purple text-white shadow-lg hover:shadow-neon-glow-lg hover:shadow-neon-blue/30",
        destructive:
          "bg-gradient-to-r from-red-500 to-red-600 text-white shadow-lg hover:shadow-red-500/30 hover:shadow-lg",
        outline:
          "border border-dark-700 bg-dark-800/50 text-dark-100 shadow-lg backdrop-blur-sm hover:bg-dark-700/50 hover:border-neon-blue hover:text-neon-blue hover:shadow-neon-glow",
        secondary:
          "bg-dark-700 text-dark-100 shadow-lg hover:bg-dark-600 hover:shadow-dark",
        ghost:
          "text-dark-300 hover:bg-dark-800/50 hover:text-neon-blue backdrop-blur-sm",
        link: "text-neon-blue underline-offset-4 hover:underline hover:text-neon-cyan",
        neon: "bg-gradient-to-r from-neon-blue via-neon-purple to-neon-pink text-white shadow-neon-glow-lg hover:shadow-neon-glow-lg animate-glow-pulse",
        glass: "glass text-white hover:bg-white/10 hover:shadow-neon-glow",
      },
      size: {
        default: "h-10 px-6 py-2",
        sm: "h-8 rounded-md gap-1.5 px-4 text-xs",
        lg: "h-12 rounded-lg px-8 text-base",
        icon: "size-10",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
