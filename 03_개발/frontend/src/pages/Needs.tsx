import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { fmtDay, type Need } from '../lib/types'
import { useFetch } from '../lib/useFetch'
import { useTarget } from '../lib/useTarget'
import { btn, card, Empty, ErrorText, input } from '../components/ui'

export default function Needs() {
  const needs = useFetch<Need[]>('/needs')
  const { rid, picker, ready } = useTarget()
  const [error, setError] = useState('')

  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const f = new FormData(form)
    try {
      await api('/needs', { method: 'POST', json: { recipient_id: rid, title: f.get('title'), note: f.get('note') || null, url: f.get('url') || null } })
      form.reset()
      setError('')
      needs.reload()
    } catch (err) { setError((err as Error).message) }
  }
  const toggle = (n: Need) => api(`/needs/${n.id}`, { method: 'PATCH', json: { status: n.status === 'delivered' ? 'requested' : 'delivered' } }).then(needs.reload, (e) => setError(e.message))
  const left = needs.data?.filter((n) => n.status !== 'delivered').length

  return (
    <div className="space-y-6">
      <h1 className="text-3xl">부탁해<span className="m-dot" /></h1>
      <form onSubmit={add} className="space-y-2">
        {picker}
        <div className="flex items-end gap-2">
          <label className="flex-1"><span className="sr-only">무엇을 부탁할까요?</span><input name="title" required maxLength={50} placeholder="대신 해 줬으면 하는 일 (치약 사다 주기)" className={input} /></label>
          <button disabled={!ready} className={btn}>부탁하기</button>
        </div>
        <details>
          <summary className="flex min-h-11 cursor-pointer items-center text-sm font-semibold text-brand-800 underline">메모·상품 주소 넣기</summary>
          <div className="space-y-3">
            <label className="block"><span className="mb-1 block font-semibold">메모</span><input name="note" maxLength={200} className={input} /></label>
            <label className="block"><span className="mb-1 block font-semibold">상품 주소</span><input name="url" type="url" maxLength={500} placeholder="https://" className={input} /></label>
          </div>
        </details>
        <ErrorText>{error}</ErrorText>
      </form>

      <section className="space-y-3" aria-label="부탁 목록">
        {needs.data && <p className="font-semibold">{left ? `남은 부탁 ${left}개` : '남은 부탁이 없어요'}</p>}
        {needs.data && !needs.data.length && <Empty>아직 부탁한 일이 없어요.</Empty>}
        {needs.data?.map((n) => (
          <label key={n.id} className={card + ' flex min-h-16 cursor-pointer items-start gap-4 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-300'}>
            <input type="checkbox" checked={n.status === 'delivered'} onChange={() => toggle(n)} className="mt-1 h-7 w-7 shrink-0 accent-brand-700" />
            <span className={n.status === 'delivered' ? 'text-slate-500 line-through' : ''}>
              <span className="block text-lg font-bold">{n.title}</span>
              <span className="block text-sm text-slate-600">{n.author_name} · {fmtDay(n.created_at)}</span>
              {n.note && <span className="block">{n.note}</span>}
            </span>
            {n.url && <a href={n.url} onClick={(e) => e.stopPropagation()} target="_blank" rel="noreferrer" className="ml-auto flex min-h-12 shrink-0 items-center font-semibold text-brand-800 underline">상품 보기</a>}
          </label>
        ))}
      </section>
    </div>
  )
}
