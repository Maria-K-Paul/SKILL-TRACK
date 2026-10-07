import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  /** Optional icon shown in a tinted chip before the title */
  icon?: ReactNode
  children: ReactNode
  className?: string
}

export default function Card({ title, icon, children, className = '' }: CardProps) {
  return (
    <section className={`rounded-3xl border border-slate-200/60 bg-white p-6 shadow-xl shadow-slate-200/40 transition-all hover:shadow-2xl hover:shadow-slate-200/50 ${className}`}>
      {title && (
        <h2 className="mb-5 flex items-center gap-3 text-lg font-bold tracking-tight text-slate-800">
          {icon && (
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-100/50">
              {icon}
            </span>
          )}
          {title}
        </h2>
      )}
      {children}
    </section>
  )
}
