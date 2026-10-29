import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { fmtDay, fmtTime, STATUS_LABEL, TYPE_LABEL, type AppEvent } from '../lib/types'
import { card, Empty, StatusBadge } from '../components/ui'

const chip = (on: boolean) => `min-h-12 rounded-full border px-4 font-semibold ${on ? 'border-ink bg-ink text-white' : 'border-ink/30 bg-white'}`

export default function Timeline() {
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [items, setItems] = useState<AppEvent[]>([])
  const [page, setPage] = useState(1)
  const [more, setMore] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => { setItems([]); setPage(1); setLoaded(false) }, [status])
  useEffect(() => {
    api<AppEvent[]>(`/events?page=${page}${status && `&status=${status}`}`).then((r) => {
      setItems((prev) => (page === 1 ? r : [...prev, ...r]))
      setMore(r.length === 20)
      setLoaded(true)
    })
  }, [page, status])

  const shown = items.filter((e) => !type || e.type === type)
  const days = [...new Set(shown.map((e) => fmtDay(e.occurred_at)))]
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">타임라인</h1>
      <div role="group" aria-label="상태" className="flex flex-wrap gap-2">
        {[['', '전체'], ...Object.entries(STATUS_LABEL)].map(([v, l]) => <button key={v} aria-pressed={status === v} onClick={() => setStatus(v)} className={chip(status === v)}>{l}</button>)}
      </div>
      <div role="group" aria-label="유형" className="flex flex-wrap gap-2">
        {[['', '모든 유형'], ...Object.entries(TYPE_LABEL)].map(([v, l]) => <button key={v} aria-pressed={type === v} onClick={() => setType(v)} className={chip(type === v)}>{l}</button>)}
      </div>
      {loaded && !shown.length && <Empty>조건에 맞는 이벤트가 없어요.</Empty>}
      {days.map((d) => (
        <section key={d} className="space-y-2">
          <h2 className="font-semibold text-slate-600">{d}</h2>
          {shown.filter((e) => fmtDay(e.occurred_at) === d).map((e) => (
            <Link key={e.id} to={`/events/${e.id}`} className={card + ' flex min-h-12 items-center justify-between gap-2 hover:brightness-95'}>
              <span><span className="block font-semibold">{TYPE_LABEL[e.type]} · {e.recipient_name}</span><span className="text-sm text-slate-600">{fmtTime(e.occurred_at)} · {e.camera_name}</span></span>
              <StatusBadge status={e.status} />
            </Link>
          ))}
        </section>
      ))}
      {more && <button onClick={() => setPage(page + 1)} className="min-h-12 w-full rounded-xl border border-slate-300 bg-white font-semibold">더 보기</button>}
    </div>
  )
}
