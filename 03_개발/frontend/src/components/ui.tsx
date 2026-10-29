import type { ReactNode } from 'react'
import { STATUS_LABEL, type AppEvent, type Camera } from '../lib/types'

export const btn = 'inline-flex min-h-12 items-center justify-center rounded-full bg-brand-700 before:mr-2.5 before:h-2 before:w-2 before:rounded-full before:bg-current px-5 font-semibold text-white hover:bg-brand-800 focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none disabled:bg-slate-300 disabled:text-slate-600'
export const btn2 = 'inline-flex min-h-12 items-center justify-center rounded-full border-[1.5px] border-ink bg-white px-5 font-semibold text-slate-900 hover:bg-slate-100 focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none'
export const input = 'min-h-12 w-full rounded-none border-0 border-b-[1.5px] border-ink/40 bg-transparent px-0 py-2 text-base focus-visible:border-brand-600 focus-visible:shadow-[0_2px_0_#6c3cff] focus-visible:outline-none'
export const card = 'rounded-[28px] bg-pale p-5'

const pill = 'inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold '

export const TypeBadge = ({ type, beta }: { type: 'senior' | 'child'; beta?: boolean }) => (
  <>
    <span className={pill + (type === 'senior' ? 'bg-sky-100 text-sky-900' : 'bg-violet-100 text-violet-900')}>{type === 'senior' ? '부모님' : '아이'}</span>
    {beta && <span className={pill + 'bg-amber-100 text-amber-900'}>베타</span>}
  </>
)

const CAM = {
  connected: ['bg-emerald-50 text-emerald-800', '● 연결됨'],
  offline: ['bg-amber-100 text-amber-900', '▲ 오프라인'],
  paused: ['bg-amber-100 text-amber-900', '❚❚ 일시정지'],
} as const
export const CameraBadge = ({ status }: { status: Camera['status'] }) => <span className={pill + CAM[status][0]}>{CAM[status][1]}</span>

const EV = { new: ['bg-red-50 text-red-800', '! '], acknowledged: ['bg-emerald-50 text-emerald-800', '✓ '], false_alarm: ['bg-slate-100 text-slate-700', '– '] } as const
export const StatusBadge = ({ status }: { status: AppEvent['status'] }) => <span className={pill + EV[status][0]}>{EV[status][1] + STATUS_LABEL[status]}</span>

export const ErrorText = ({ children }: { children?: ReactNode }) => (children ? <p role="alert" className="mt-2 text-sm font-medium text-red-800">{children}</p> : null)
export const Empty = ({ children }: { children: ReactNode }) => <p className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-slate-600">{children}</p>
