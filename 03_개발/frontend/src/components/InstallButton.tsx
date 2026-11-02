import { useInstall } from '../lib/install'

export default function InstallButton({ className = '' }: { className?: string }) {
  const { kind, install } = useInstall()
  if (kind === 'none') return null
  return <button onClick={install} className={`min-h-11 shrink-0 rounded-full border border-brand-600 px-3 text-sm font-semibold text-brand-800 ${className}`}>앱 설치</button>
}
