import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import type { Camera, Recipient } from '../lib/types'
import { btn, btn2, CameraBadge, card, Empty, ErrorText, input, TypeBadge } from '../components/ui'

export default function Cameras() {
  const cams = useFetch<Camera[]>('/cameras')
  const rec = useFetch<Recipient[]>('/recipients')
  const [error, setError] = useState('')
  const ready = rec.data?.filter((r) => (r.type === 'senior' ? r.linked : r.consent_confirmed)) ?? []

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget // await 이후에는 currentTarget이 null이 된다
    const f = new FormData(form)
    try {
      await api('/cameras', { method: 'POST', json: { recipient_id: Number(f.get('recipient')), name: f.get('name'), location_label: f.get('location') || null } })
      form.reset()
      setError('')
      cams.reload()
    } catch (err) { setError((err as Error).message) }
  }
  const toggle = (c: Camera) => api(`/cameras/${c.id}`, { method: 'PATCH', json: { paused: c.status !== 'paused' } }).then(cams.reload)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">카메라</h1>
      <section className="space-y-3" aria-live="polite">
        {cams.data && !cams.data.length && <Empty>등록된 카메라가 없어요. 아래에서 첫 카메라를 등록해 보세요.</Empty>}
        {cams.data?.map((c) => (
          <article key={c.id} className={card}>
            <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold">{c.name}</h2><CameraBadge status={c.status} /></div>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-slate-600">{c.recipient_name} <TypeBadge type={c.recipient_type} beta={c.beta} />{c.location_label && <span>· {c.location_label}</span>}</p>
            <Link to={`/cameras/${c.id}/stream`} className={btn + ' mt-3 mr-2'}>이 기기의 카메라 켜기</Link>
            <button onClick={() => toggle(c)} className={btn2 + ' mt-3'}>{c.status === 'paused' ? '모니터링 다시 시작' : '모니터링 일시정지'}</button>
          </article>
        ))}
      </section>

      <form onSubmit={add} className={card + ' space-y-4'}>
        <h2 className="text-lg font-bold">카메라 등록</h2>
        {rec.data && !ready.length ? (
          <p className="text-slate-600">카메라를 등록하려면 연결이 끝난 부모님이나 동의를 확인한 아이 프로필이 필요해요. <Link to="/recipients/new" className="font-semibold text-brand-800 underline">돌봄 대상 추가</Link></p>
        ) : (
          <>
            <label className="block"><span className="mb-1 block font-semibold">돌봄 대상</span>
              <select name="recipient" required className={input}>{ready.map((r) => <option key={r.id} value={r.id}>{r.display_name} ({r.type === 'senior' ? '부모님' : '아이'})</option>)}</select></label>
            <label className="block"><span className="mb-1 block font-semibold">카메라 이름</span><input name="name" required maxLength={30} placeholder="거실 카메라" className={input} /></label>
            <label className="block"><span className="mb-1 block font-semibold">설치 위치 (선택)</span><input name="location" maxLength={30} className={input} /></label>
            <ErrorText>{error}</ErrorText>
            <button className={btn + ' w-full'}>카메라 등록</button>
          </>
        )}
      </form>
    </div>
  )
}
