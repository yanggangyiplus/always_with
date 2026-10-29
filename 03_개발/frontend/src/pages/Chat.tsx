import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation as useRoute, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useSession } from '../lib/auth'
import { useLocation as useFamily } from '../lib/location'
import { useSeen } from '../lib/seen'
import type { Msg, Quote } from '../lib/types'
import { btn, ErrorText, input } from '../components/ui'

const hm = (s: string) => new Date(s + 'Z').toLocaleTimeString('ko-KR', { hour: 'numeric', minute: '2-digit' })

type Reply = { id: number; author_name: string; text: string }

function QuoteBox({ q, mine }: { q: Quote; mine: boolean }) {
  const tone = mine ? 'border-white/60 text-white/90' : 'border-ink/30 text-slate-700'
  return (
    <Link to="/feed" className={`mb-1 block rounded-xl border-l-4 bg-black/5 px-3 py-1 text-sm ${tone}`}>
      {'hidden' in q ? '볼 수 없는 글에 대한 답장이에요' : 'gone' in q ? '지워진 글이에요' : (
        <><span className="font-bold">{q.author_name}님의 글</span>{q.photos > 0 && ` · 사진 ${q.photos}장`}<span className="block truncate">{q.text}</span></>
      )}
    </Link>
  )
}

export default function Chat() {
  const { me } = useSession()
  const nav = useNavigate()
  const route = useRoute()
  const family = useFamily().data?.members ?? []
  // 피드에서 '채팅으로 답장'을 눌러 넘어온 글. 새로고침해도 남지 않도록 주소의 기록에서는 지운다.
  const [reply, setReply] = useState<Reply | null>((route.state as { reply?: Reply } | null)?.reply ?? null)
  useEffect(() => { if (route.state) nav(route.pathname, { replace: true, state: null }) }, [])
  const [msgs, setMsgs] = useState<Msg[]>([])
  useSeen('chat')
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const last = useRef(0)
  const end = useRef<HTMLDivElement>(null)

  // shortcut: 3초마다 새 글만 가져온다, 사용자가 많아지면 WebSocket으로 바꾼다
  const poll = () => api<Msg[]>(`/chat?after=${last.current}`).then((n) => {
    if (!n.length) return
    last.current = n[n.length - 1].id
    setMsgs((old) => [...old, ...n])
  }, (e) => setError(e.message))
  useEffect(() => { poll(); const t = setInterval(poll, 3000); return () => clearInterval(t) }, [])
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [msgs.length])

  async function send(e: FormEvent) {
    e.preventDefault()
    try { await api('/chat', { method: 'POST', json: { text, post_id: reply?.id } }); setText(''); setReply(null); setError(''); poll() } catch (err) { setError((err as Error).message) }
  }

  return (
    <div className="flex min-h-[calc(100svh-10rem)] flex-col gap-4">
      <h1 className="text-3xl">채팅<span className="m-dot" /></h1>
      <section aria-label="대화 참여자" className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-600">참여 {family.length + 1}명</span>
        {['나', ...family.map((m) => m.name)].map((n, i) => (
          <span key={n + i} className="inline-flex min-h-9 items-center gap-2 rounded-full bg-pale py-1 pr-3 pl-1 text-sm font-semibold">
            <span aria-hidden className="grid h-7 w-7 place-items-center rounded-full bg-brand-600 text-xs text-white">{n.slice(0, 1)}</span>{n}
          </span>
        ))}
      </section>
      <section aria-label="대화" className="flex-1 space-y-2">
        {!msgs.length && <p className="py-8 text-center text-slate-600">가족에게 첫 인사를 건네 보세요.</p>}
        {msgs.map((m) => {
          const mine = m.author_id === me?.id
          return (
            <div key={m.id} className={mine ? 'flex flex-col items-end' : 'flex flex-col items-start'}>
              {!mine && <span className="px-2 text-sm text-slate-600">{m.author_name}</span>}
              <div className={`max-w-[80%] rounded-[22px] px-4 py-2 text-lg break-words ${mine ? 'bg-brand-700 text-white' : 'bg-pale'}`}>
                {m.quote && <QuoteBox q={m.quote} mine={mine} />}
                {m.text}
              </div>
              <span className="px-2 text-xs text-slate-600">{hm(m.created_at)}</span>
            </div>
          )
        })}
        <div ref={end} />
      </section>
      {reply && (
        <p className="flex items-center justify-between gap-2 rounded-2xl bg-brand-50 px-4 py-2 text-sm text-brand-800">
          <span className="min-w-0"><span className="font-bold">{reply.author_name}님의 글에 답장</span><span className="block truncate">{reply.text}</span></span>
          <button type="button" onClick={() => setReply(null)} aria-label="답장 취소" className="min-h-12 min-w-12 text-xl">×</button>
        </p>
      )}
      <form onSubmit={send} className="sticky bottom-0 flex items-end gap-2 bg-white py-2">
        <label className="flex-1"><span className="sr-only">메시지</span><input value={text} onChange={(e) => setText(e.target.value)} maxLength={500} required placeholder="메시지 입력" className={input} /></label>
        <button disabled={!text.trim()} className={btn}>보내기</button>
      </form>
      <ErrorText>{error}</ErrorText>
    </div>
  )
}
