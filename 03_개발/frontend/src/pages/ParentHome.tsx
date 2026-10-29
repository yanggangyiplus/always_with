import { Link } from 'react-router-dom'
import { useSession } from '../lib/auth'
import { useLocation } from '../lib/location'
import { seenAt } from '../lib/seen'
import type { Msg, Need, Plan, Post } from '../lib/types'
import { useFetch } from '../lib/useFetch'
import { card, Empty } from '../components/ui'

const today = new Date().toLocaleDateString('sv') // YYYY-MM-DD
const after = (iso: string, ms: number) => new Date(iso + 'Z').getTime() > ms
const hm = (s: string) => new Date(s).toLocaleTimeString('ko-KR', { hour: 'numeric', minute: '2-digit' })
const day = (s: string) => (s.slice(0, 10) === today ? '오늘' : new Date(s).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' }))
const ago = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso + 'Z').getTime()) / 60_000)
  return m < 1 ? '방금 전' : m < 60 ? `${m}분 전` : `${Math.floor(m / 60)}시간 전`
}

const FEATURES = [
  ['/feed', '피드', '사진과 한마디로 오늘 안부를 전해요'],
  ['/chat', '채팅', '가족끼리 바로 이야기해요'],
  ['/plans', '일정', '병원, 모임 같은 일정을 같이 봐요'],
  ['/needs', '부탁해', '대신 해 줬으면 하는 일을 적어 두고 체크해요'],
  ['/where', '위치', '원할 때만 내 위치를 알려요'],
] as const

export default function ParentHome() {
  const { me } = useSession()
  const posts = useFetch<Post[]>('/posts')
  const needs = useFetch<Need[]>('/needs')
  const plans = useFetch<Plan[]>(`/plans?from=${today}`)
  const chat = useFetch<Msg[]>('/chat')
  const { data: loc } = useLocation()
  if (!posts.data || !needs.data || !plans.data || !chat.data) return <p aria-live="polite" className="py-8 text-lg text-slate-600">불러오는 중…</p>

  const newPosts = posts.data.filter((p) => p.author_id !== me?.id && after(p.created_at, seenAt('feed'))).length
  const newChat = chat.data.filter((m) => m.author_id !== me?.id && after(m.created_at, seenAt('chat'))).length
  const todo = needs.data.filter((n) => n.status !== 'delivered').length
  const todayPlans = plans.data.filter((p) => p.starts_at.startsWith(today))
  const todos = [
    newChat > 0 && ['/chat', `새 메시지 ${newChat}개`],
    newPosts > 0 && ['/feed', `새 피드 ${newPosts}개`],
    todayPlans.length > 0 && ['/plans', `오늘 일정 ${todayPlans.length}개 · ${hm(todayPlans[0].starts_at)} ${todayPlans[0].title}`],
    todo > 0 && ['/needs', `아직 안 끝난 부탁 ${todo}개`],
  ].filter(Boolean) as [string, string][]

  return (
    <div className="space-y-8 text-lg">
      <section aria-live="polite" className="space-y-3">
        <h1 className="text-4xl leading-tight">{todos.length ? `확인할 것이 ${todos.length}가지 있어요` : <>새로 확인할 것이 없어요<span className="m-dot" /></>}</h1>
        {todos.map(([to, label]) => (
          <Link key={to} to={to} className="flex min-h-14 items-center justify-between gap-2 rounded-[28px] bg-brand-50 px-5 font-semibold text-brand-800 hover:brightness-95 focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none">
            <span>{label}</span><span aria-hidden>›</span>
          </Link>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold">연결된 가족</h2>
        {!loc?.members.length && <Empty>연결된 가족이 아직 없어요.</Empty>}
        {loc?.members.map((m) => (
          <article key={m.user_id} className={card + ' flex items-center justify-between gap-3'}>
            <div>
              <p className="font-bold">{m.name}</p>
              <p className="text-base text-slate-600">{!m.sharing ? '위치를 공유하지 않아요' : m.updated_at ? `${ago(m.updated_at)} 위치 공유 중` : '위치 공유를 켰어요'}</p>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold">연결됨</span>
          </article>
        ))}
        <p className="text-base text-slate-600">내 위치 공유는 {loc?.me.sharing ? '켜져 있어요' : '꺼져 있어요'}. <Link to="/where" className="font-semibold text-brand-800 underline">바꾸러 가기</Link></p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold">다가오는 일정</h2>
        {!plans.data.length ? <Empty>다가오는 일정이 없어요.</Empty> : plans.data.slice(0, 3).map((p) => (
          <Link key={p.id} to="/plans" className={card + ' block hover:brightness-95'}>
            <p className="font-bold">{p.title}</p>
            <p className="text-base text-slate-600">{day(p.starts_at)} {hm(p.starts_at)}</p>
          </Link>
        ))}
      </section>

      <section className="space-y-3 rounded-[28px] bg-ink p-6 text-white">
        <h2 className="text-2xl font-bold">Always with는 이런 서비스예요</h2>
        <p className="text-white/80">멀리 있어도 서로 안부를 나누는 가족 앱이에요. 필요할 때만 알리고, 하고 싶은 것만 공유해요.</p>
        <ul className="space-y-1">
          {FEATURES.map(([to, name, desc]) => (
            <li key={to}><Link to={to} className="flex min-h-12 flex-col justify-center rounded-2xl px-3 hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none"><span className="font-bold">{name}</span><span className="text-base text-white/70">{desc}</span></Link></li>
          ))}
        </ul>
        <p className="text-base text-white/70">위치는 내가 켠 동안만 공유되고, 끄면 저장된 위치가 지워져요.</p>
      </section>
    </div>
  )
}
