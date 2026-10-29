import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, clipUrl } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { fmtTime, TYPE_LABEL, type AppEvent } from '../lib/types'
import { btn, btn2, ErrorText, StatusBadge, TypeBadge } from '../components/ui'

export default function EventDetail() {
  const { id } = useParams()
  const { data: e, error, reload } = useFetch<AppEvent>(`/events/${id}`)
  const [clip, setClip] = useState<string | null | undefined>()
  const [asking, setAsking] = useState<'acknowledged' | 'false_alarm' | null>(null)
  const [fail, setFail] = useState('')

  useEffect(() => { clipUrl(Number(id)).then(setClip) }, [id])

  async function change(status: 'acknowledged' | 'false_alarm') {
    try { await api(`/events/${id}`, { method: 'PATCH', json: { status } }); setAsking(null); reload() } catch (err) { setFail((err as Error).message) }
  }
  if (error) return <p role="alert" className="py-8">{error}</p>
  if (!e) return <p className="py-8 text-slate-600">불러오는 중…</p>

  const fall = e.type === 'fall'
  return (
    <div className="space-y-4">
      <Link to="/timeline" className="inline-flex min-h-12 items-center font-semibold text-brand-800 underline">타임라인으로</Link>
      <section className={`rounded-2xl border p-5 ${fall ? 'border-red-200 bg-red-50 text-red-800' : 'border-amber-200 bg-amber-100 text-amber-900'}`}>
        <h1 className="text-2xl font-bold">{TYPE_LABEL[e.type]}</h1>
        <p className="mt-1">{fmtTime(e.occurred_at)} · {e.camera_name}</p>
      </section>
      <div className="flex flex-wrap items-center gap-2"><span className="font-bold">{e.recipient_name}</span><TypeBadge type={e.recipient_type} beta={e.beta} /><StatusBadge status={e.status} />{e.score != null && <span className="text-slate-600">신뢰도 {e.score.toFixed(2)}</span>}</div>
      {e.beta && <p className="rounded-2xl bg-amber-100 p-4 text-amber-900">아이 대상 감지는 베타예요. 놀이 동작을 잘못 알릴 수 있으니 직접 확인해 주세요.</p>}
      {clip ? <video src={clip} controls className="w-full rounded-2xl bg-black" /> : clip === null && <p className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-slate-600">클립을 불러올 수 없어요.</p>}

      {e.status === 'new' ? (
        asking ? (
          <div role="alertdialog" aria-live="assertive" className="space-y-3 rounded-2xl border border-slate-300 bg-white p-4">
            <p className="font-semibold">{asking === 'acknowledged' ? '확인 완료로 바꿀까요?' : '오탐으로 신고할까요?'} 한 번 바꾸면 되돌릴 수 없어요.</p>
            <div className="flex gap-2"><button onClick={() => change(asking)} className={btn + ' flex-1'}>바꾸기</button><button onClick={() => setAsking(null)} className={btn2 + ' flex-1'}>취소</button></div>
          </div>
        ) : (
          <div className="space-y-3">
            <button onClick={() => setAsking('acknowledged')} className={btn + ' w-full'}>확인 완료</button>
            <button onClick={() => setAsking('false_alarm')} className={btn2 + ' w-full'}>오탐 신고</button>
            <p className="text-sm text-slate-600">오탐 신고는 모델 개선에 쓰이고, 관절 좌표만 저장돼요.</p>
          </div>
        )
      ) : <p className="text-slate-600">이미 처리한 이벤트예요.</p>}
      <ErrorText>{fail}</ErrorText>
    </div>
  )
}
