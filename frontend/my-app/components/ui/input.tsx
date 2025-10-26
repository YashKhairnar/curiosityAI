import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "file:text-foreground placeholder:text-dark-400 selection:bg-neon-blue selection:text-white dark:bg-dark-800/50 border-dark-600 h-12 w-full min-w-0 rounded-xl border bg-dark-900/50 px-4 py-3 text-base text-white shadow-lg backdrop-blur-sm transition-all duration-300 outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        "focus:border-neon-blue focus:ring-2 focus:ring-neon-blue/20 focus:shadow-neon-glow",
        "hover:border-dark-500 hover:shadow-lg",
        "aria-invalid:border-red-500 aria-invalid:ring-2 aria-invalid:ring-red-500/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
