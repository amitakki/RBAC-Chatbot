interface RoleBadgeProps {
  role: string
  className?: string
}

const ROLE_STYLES: Record<string, string> = {
  finance: 'bg-blue-100 text-blue-800',
  hr: 'bg-green-100 text-green-800',
  marketing: 'bg-orange-100 text-orange-800',
  engineering: 'bg-purple-100 text-purple-800',
  executive: 'bg-red-100 text-red-800',
}

export function RoleBadge({ role, className = '' }: RoleBadgeProps) {
  const styles = ROLE_STYLES[role.toLowerCase()] ?? 'bg-gray-100 text-gray-800'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${styles} ${className}`}
      aria-label={`Role: ${role}`}
    >
      {role}
    </span>
  )
}
