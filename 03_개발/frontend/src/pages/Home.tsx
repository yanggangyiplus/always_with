import { Link } from 'react-router-dom'
import { CameraBadge, card, Empty, StatusBadge, TypeBadge, btn } from '../components/ui'
import { useFetch } from '../lib/useFetch'
import { fmtTime, isToday, TYPE_LABEL, type AppEvent, type Camera, type Recipient } from '../lib/types'

export default function Home() {
  const rec = useFetch<Recipient[]>('/recipients')
  const cams = useFetch<Camera[]>('/cameras')
  const evs = useFetch<AppEvent[]>('/events')
  const { data: cameras } = cams
  if (!rec.data || !cameras || !evs.data) return <p aria-live="polite" className="py-8 text-slate-600">불러오는 중…</p>

  const pending = evs.data.filter((e) => e.status === 'new')
  const today = evs.data.filter((e) => isToday(e.occurred_at)).length
  const online = cameras.filter((c) => c.status === 'connected').length

  return (
    <div className="space-y-8">
      <section aria-live="polite" className={pending.length ? 'rounded-[28px] bg-red-50 p-5 text-red-800' : 'py-2'}>
        <h1 className="text-4xl leading-tight">{pending.length ? `확인하지 않은 알림이 ${pending.length}건 있어요` : <>오늘은 이상 없어요<span className="m-dot" /></>}</h1>
        <p className={pending.length ? 'mt-2' : 'mt-2 text-slate-600'}>
          {cameras.length ? `카메라 ${cameras.length}대 중 ${online}대가 켜져 있고, 오늘 알림은 ${today}건이에요.` : '아직 등록된 카메라가 없어요.'}
        </p>
        {pending.slice(0, 3).map((e) => (
          <Link key={e.id} to={`/events/${e.id}`} className="mt-3 flex min-h-12 items-center justify-between rounded-xl bg-white px-4 font-semibold text-red-800 focus-visible:ring-4 focus-visible:ring-red-300 focus-visible:outline-none">
            <span>{TYPE_LABEL[e.type]} · {e.recipient_name}</span><span className="text-sm font-normal">{fmtTime(e.occurred_at)}</span>
          </Link>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between"><h2 className="text-xl font-bold">돌봄 대상</h2><Link to="/recipients/new" className="flex min-h-12 items-center px-2 font-semibold text-brand-800 underline">추가하기</Link></div>
        {!rec.data.length && (
          <div className="space-y-3"><Empty>부모님이나 아이를 추가하면 여기에서 상태를 볼 수 있어요.</Empty><Link to="/recipients/new" className={btn + ' w-full'}>돌봄 대상 추가</Link></div>
        )}
        {rec.data.map((r) => {
          const mine = cameras.filter((c) => c.recipient_id === r.id)
          return (
            <article key={r.id} className={card}>
              <div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold">{r.display_name}</h3><TypeBadge type={r.type} beta={r.beta} /></div>
              {!r.linked && (r.type === 'senior' || r.consent_confirmed) && <Link to={`/recipients/${r.id}/connect`} className="mt-2 inline-flex min-h-12 items-center font-semibold text-brand-800 underline">{r.type === 'senior' ? '코드로 부모님 연결하기' : '아이 휴대폰 연결하기 (선택)'}</Link>}
              {r.linked || r.type === 'child' ? (
                mine.length ? mine.map((c) => (
                  <p key={c.id} className="mt-2 flex items-center justify-between gap-2"><span>{c.name}{c.location_label && ` · ${c.location_label}`}</span><CameraBadge status={c.status} /></p>
                )) : <Link to="/cameras" className="mt-2 inline-flex min-h-12 items-center font-semibold text-brand-800 underline">카메라 등록하기</Link>
              ) : null}
            </article>
          )
        })}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold">최근 이벤트</h2>
        {!evs.data.length ? <Empty>아직 이벤트가 없어요.</Empty> : evs.data.slice(0, 3).map((e) => (
          <Link key={e.id} to={`/events/${e.id}`} className={card + ' flex min-h-12 items-center justify-between gap-2 hover:brightness-95'}>
            <span><span className="block font-semibold">{TYPE_LABEL[e.type]} · {e.camera_name}</span><span className="text-sm text-slate-600">{fmtTime(e.occurred_at)}</span></span>
            <StatusBadge status={e.status} />
          </Link>
        ))}
      </section>

      <p className="flex gap-4"><Link to="/timeline" className="flex min-h-12 items-center font-semibold text-brand-800 underline">전체 타임라인</Link><Link to="/report" className="flex min-h-12 items-center font-semibold text-brand-800 underline">리포트</Link></p>
    </div>
  )
}
