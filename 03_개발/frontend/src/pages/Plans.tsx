import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { type Plan } from '../lib/types'
import { useFetch } from '../lib/useFetch'
import { useTarget } from '../lib/useTarget'
import { btn, card, ErrorText, input } from '../components/ui'

const pad = (n: number) => String(n).padStart(2, '0')
const ymd = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`
const hm = (s: string) => new Date(s).toLocaleTimeString('ko-KR', { hour: 'numeric', minute: '2-digit' })
const WEEK = ['일', '월', '화', '수', '목', '금', '토']

export default function Plans() {
  const now = new Date()
  const todayKey = ymd(now.getFullYear(), now.getMonth(), now.getDate())
  const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() })
  const [sel, setSel] = useState(todayKey)
  const [error, setError] = useState('')
  const last = new Date(ym.y, ym.m + 1, 0).getDate()
  const plans = useFetch<Plan[]>(`/plans?from=${ymd(ym.y, ym.m, 1)}&to=${ymd(ym.y, ym.m, last)}`)
  const { rid, picker, ready } = useTarget()

  const byDay: Record<string, Plan[]> = {}
  for (const p of plans.data ?? []) (byDay[p.starts_at.slice(0, 10)] ??= []).push(p) // 서버가 시각순으로 준다
  const lead = new Date(ym.y, ym.m, 1).getDay()
  const go = (d: number) => { const t = new Date(ym.y, ym.m + d, 1); setYm({ y: t.getFullYear(), m: t.getMonth() }) }

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const f = new FormData(form)
    try {
      await api('/plans', { method: 'POST', json: { recipient_id: rid, title: f.get('title'), starts_at: `${sel}T${f.get('time')}`, note: f.get('note') || null } })
      form.reset()
      setError('')
      plans.reload()
    } catch (err) { setError((err as Error).message) }
  }
  const remove = (id: number) => api(`/plans/${id}`, { method: 'DELETE' }).then(plans.reload, (e) => setError(e.message))

  return (
    <div className="space-y-6">
      <h1 className="text-3xl">일정<span className="m-dot" /></h1>

      <section aria-label="달력" className={card}>
        <div className="mb-3 flex items-center justify-between">
          <button onClick={() => go(-1)} aria-label="이전 달" className="min-h-12 min-w-12 rounded-full hover:bg-white">‹</button>
          <h2 className="font-sans text-lg font-bold tracking-normal" aria-live="polite">{ym.y}년 {ym.m + 1}월</h2>
          <button onClick={() => go(1)} aria-label="다음 달" className="min-h-12 min-w-12 rounded-full hover:bg-white">›</button>
        </div>
        <div className="grid grid-cols-7 text-center text-sm text-slate-600">{WEEK.map((w) => <span key={w}>{w}</span>)}</div>
        <div className="mt-1 grid grid-cols-7 gap-1">
          {Array.from({ length: lead }, (_, i) => <span key={`b${i}`} />)}
          {Array.from({ length: last }, (_, i) => {
            const key = ymd(ym.y, ym.m, i + 1)
            const n = byDay[key]?.length ?? 0
            return (
              <button key={key} onClick={() => setSel(key)} aria-pressed={sel === key} aria-label={`${ym.m + 1}월 ${i + 1}일${n ? `, 일정 ${n}개` : ''}`}
                className={`flex min-h-12 flex-col items-center justify-center rounded-2xl text-base focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none ${sel === key ? 'bg-ink text-white' : key === todayKey ? 'bg-white font-bold ring-2 ring-brand-600' : 'hover:bg-white'}`}>
                {i + 1}
                <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${n ? 'bg-brand-600' : 'bg-transparent'}`} />
              </button>
            )
          })}
        </div>
      </section>

      <section aria-label={`${sel} 일정`} className="space-y-2">
        <h2 className="font-sans text-base font-bold tracking-normal">{new Date(sel).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' })}</h2>
        {!byDay[sel] && <p className="text-slate-600">이 날은 일정이 없어요.</p>}
        {byDay[sel]?.map((p) => (
          <article key={p.id} className={card + ' flex items-center justify-between gap-3'}>
            <div><p className="font-semibold">{hm(p.starts_at)} · {p.title}</p><p className="text-sm text-slate-600">{p.author_name}{p.note && ` · ${p.note}`}</p></div>
            <button onClick={() => remove(p.id)} aria-label={`${p.title} 삭제`} className="min-h-12 px-2 text-sm underline">삭제</button>
          </article>
        ))}
      </section>

      <form onSubmit={add} className="space-y-3" key={sel}>
        <h2 className="font-sans text-base font-bold tracking-normal">이 날 일정 추가</h2>
        {picker}
        <label className="block"><span className="mb-1 block font-semibold">무슨 일정인가요?</span><input name="title" required maxLength={50} placeholder="병원 진료, 가족 식사" className={input} /></label>
        <label className="block"><span className="mb-1 block font-semibold">몇 시인가요?</span><input name="time" type="time" required defaultValue="10:00" className={input} /></label>
        <label className="block"><span className="mb-1 block font-semibold">메모 (선택)</span><input name="note" maxLength={200} className={input} /></label>
        <ErrorText>{error}</ErrorText>
        <button disabled={!ready} className={btn + ' w-full'}>일정 추가</button>
      </form>
    </div>
  )
}
