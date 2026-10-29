import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import type { Recipient } from '../lib/types'
import { btn, btn2, card, ErrorText, input } from '../components/ui'

type Invite = { code: string; expires_at: string }

export function Code({ recipientId, name }: { recipientId: number; name: string }) {
  const [invite, setInvite] = useState<Invite>()
  const [linked, setLinked] = useState(false)
  const [left, setLeft] = useState(0)
  const [error, setError] = useState('')
  const issue = () => api<Invite>('/invites', { method: 'POST', json: { recipient_id: recipientId } }).then(setInvite, (e) => setError(e.message))
  useEffect(() => { issue() }, [])
  useEffect(() => {
    const t = setInterval(() => {
      if (invite) setLeft(Math.max(0, Math.round((new Date(invite.expires_at + 'Z').getTime() - Date.now()) / 1000)))
      api<Recipient[]>('/recipients').then((l) => setLinked(!!l.find((r) => r.id === recipientId)?.linked))
    }, 1000)
    return () => clearInterval(t)
  }, [invite, recipientId])

  if (linked) return <div className={card} aria-live="polite"><p className="text-xl font-bold">{name}님과 연결됐어요</p><Link to="/cameras" className={btn + ' mt-4 w-full'}>카메라 등록하기</Link></div>
  return (
    <div className={card + ' space-y-3'} aria-live="polite">
      <p>{name}님께 이 코드를 알려 주세요. 부모님·아이용 계정으로 가입해 코드를 입력하고 동의하면 연결돼요.</p>
      {invite && <p className="text-center font-mono text-5xl font-bold tracking-[0.3em] text-brand-800">{invite.code}</p>}
      <p className="text-center text-slate-600">{left > 0 ? `${Math.floor(left / 60)}분 ${left % 60}초 남았어요 · 연결을 기다리는 중` : '코드가 만료됐어요. 새로 발급해 주세요.'}</p>
      <ErrorText>{error}</ErrorText>
      <button onClick={issue} className={btn2 + ' w-full'}>코드 다시 발급</button>
    </div>
  )
}

export function ConnectRecipient() {
  const { id } = useParams()
  const rec = useFetch<Recipient[]>('/recipients')
  const r = rec.data?.find((x) => x.id === Number(id))
  return r ? <Code recipientId={r.id} name={r.display_name} /> : null
}

export default function AddRecipient() {
  const [type, setType] = useState<'senior' | 'child'>('senior')
  const [consent, setConsent] = useState(false)
  const [created, setCreated] = useState<Recipient>()
  const [error, setError] = useState('')

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const year = f.get('birth_year')
    try {
      setCreated(await api<Recipient>('/recipients', { method: 'POST', json: { type, display_name: f.get('name'), birth_year: year ? Number(year) : null, consent_confirmed: consent } }))
    } catch (err) { setError((err as Error).message) }
  }

  if (created) return created.type === 'senior' ? <Code recipientId={created.id} name={created.display_name} /> : (
    <div className={card + ' space-y-3'}><p className="text-xl font-bold">{created.display_name} 프로필을 만들었어요</p><Link to="/cameras" className={btn + ' w-full'}>카메라 등록하기</Link><Link to={`/recipients/${created.id}/connect`} className={btn2 + ' w-full'}>아이 휴대폰도 연결하기</Link></div>
  )
  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="text-2xl font-bold">돌봄 대상 추가</h1>
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="sr-only">유형</legend>
        {([['senior', '부모님'], ['child', '아이']] as const).map(([v, label]) => (
          <label key={v} className={`flex min-h-12 cursor-pointer items-center justify-center rounded-[28px] border-[1.5px] p-3 font-bold has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-300 ${type === v ? 'border-brand-600 bg-brand-50' : 'border-transparent bg-pale'}`}>
            <input type="radio" name="type" className="sr-only" checked={type === v} onChange={() => setType(v)} />{label}
          </label>
        ))}
      </fieldset>
      <label className="block"><span className="mb-1 block font-semibold">이름</span><input name="name" required maxLength={30} className={input} /></label>
      <label className="block"><span className="mb-1 block font-semibold">출생연도 (선택)</span><input name="birth_year" type="number" min={1900} max={2100} className={input} /></label>
      {type === 'child' ? (
        <>
          <p className="rounded-2xl bg-amber-100 p-4 text-amber-900">아이 감지는 베타예요. 성인 데이터로 학습한 모델을 쓰기 때문에 놀이 동작을 낙상으로 잘못 알릴 수 있어요.</p>
          <label className="flex min-h-12 items-start gap-3"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-6 w-6 shrink-0" /><span>법정대리인으로서 아이의 영상 분석에 동의해요. 영상은 저장되지 않아요.</span></label>
        </>
      ) : <p className="text-slate-600">저장하면 부모님께 알려 줄 초대 코드가 나와요.</p>}
      <ErrorText>{error}</ErrorText>
      <button disabled={type === 'child' && !consent} className={btn + ' w-full'}>{type === 'senior' ? '저장하고 코드 받기' : '프로필 저장'}</button>
    </form>
  )
}
