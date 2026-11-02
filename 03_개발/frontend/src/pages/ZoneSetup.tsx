import { useRef, useState, type FormEvent, type PointerEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { ZONE_LABEL, type Camera, type Zone } from '../lib/types'
import { ZoneBoxes } from '../components/ZoneBoxes'
import { btn, btn2, card, Empty, ErrorText, input } from '../components/ui'

const MAX_ZONES = 3 // 서버와 같은 값
const MIN_SIZE = 0.05
const PRESETS = [['왼쪽', { x: 0, y: 0, w: 0.4, h: 1 }], ['오른쪽', { x: 0.6, y: 0, w: 0.4, h: 1 }], ['아래쪽', { x: 0, y: 0.6, w: 1, h: 0.4 }]] as const
type Rect = { x: number; y: number; w: number; h: number }

export default function ZoneSetup() {
  const { id } = useParams()
  const cams = useFetch<Camera[]>('/cameras')
  const zones = useFetch<Zone[]>(`/cameras/${id}/zones`)
  const board = useRef<HTMLDivElement>(null)
  const start = useRef<{ x: number; y: number } | null>(null)
  const [rect, setRect] = useState<Rect | null>(null)
  const [purpose, setPurpose] = useState<'danger' | 'bed'>('danger')
  const [error, setError] = useState('')
  const cam = cams.data?.find((c) => c.id === Number(id))
  const full = (zones.data?.length ?? 0) >= MAX_ZONES

  const at = (e: PointerEvent) => {
    const b = board.current!.getBoundingClientRect()
    return { x: Math.min(1, Math.max(0, (e.clientX - b.left) / b.width)), y: Math.min(1, Math.max(0, (e.clientY - b.top) / b.height)) }
  }
  const down = (e: PointerEvent) => { e.currentTarget.setPointerCapture(e.pointerId); start.current = at(e); setRect(null) }
  const move = (e: PointerEvent) => {
    const s = start.current
    if (!s) return
    const p = at(e)
    setRect({ x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) })
  }
  const up = () => { start.current = null; setRect((r) => (r && r.w >= MIN_SIZE && r.h >= MIN_SIZE ? r : null)) }

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!rect) return setError('화면에서 구역을 드래그해 그리거나 아래 위치 버튼을 눌러 주세요.')
    const form = e.currentTarget // await 이후에는 currentTarget이 null이 된다
    const f = new FormData(form)
    const dwell = Number(f.get('dwell'))
    try {
      await api(`/cameras/${id}/zones`, { method: 'POST', json: { name: f.get('name'), purpose, ...rect, active_from: purpose === 'bed' ? f.get('from') : null, active_to: purpose === 'bed' ? f.get('to') : null, dwell_sec: dwell || null } })
      setRect(null); setError(''); form.reset(); zones.reload()
    } catch (err) { setError((err as Error).message) }
  }
  const remove = (z: Zone) => confirm(`"${z.name}" 구역을 지울까요?`) && api(`/zones/${z.id}`, { method: 'DELETE' }).then(zones.reload, (err) => setError(err.message))

  if (cams.data && cam?.recipient_type !== 'child') return <p className="py-8">아이 카메라에서만 구역을 설정할 수 있어요. <Link to="/cameras" className="font-semibold text-brand-800 underline">카메라 목록으로</Link></p>
  return (
    <div className="space-y-5">
      <Link to="/cameras" className="inline-flex min-h-12 items-center font-semibold text-brand-800 underline">카메라 목록으로</Link>
      <h1 className="text-2xl font-bold">{cam?.name} 구역 설정</h1>
      <p className="text-slate-600">카메라 화면 위에 위험 구역(주방 같은 곳)이나 취침 구역(침대)을 그려요. 카메라가 켜져 있어야 저장돼요. 카메라당 최대 {MAX_ZONES}개예요.</p>
      <p className="rounded-2xl bg-amber-100 p-4 text-amber-900">구역에 들어가거나 벗어나면 알려 주는 기능은 아직 개발 중이에요. 지금은 구역을 저장하고 화면에 겹쳐 보여 주는 것까지 돼요.</p>

      <div ref={board} onPointerDown={down} onPointerMove={move} onPointerUp={up} style={{ touchAction: 'none' }} role="img" aria-label="구역을 그리는 카메라 화면. 아래 위치 버튼으로도 정할 수 있어요"
        className="relative aspect-[4/3] w-full cursor-crosshair select-none overflow-hidden rounded-2xl bg-slate-800 bg-[linear-gradient(rgba(255,255,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.12)_1px,transparent_1px)] bg-[size:25%_25%]">
        <ZoneBoxes zones={zones.data ?? []} draft={rect} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">위치로 정하기</span>
        {PRESETS.map(([label, r]) => <button key={label} type="button" onClick={() => setRect({ ...r })} className={btn2}>{label}</button>)}
      </div>

      <form onSubmit={save} className={card + ' space-y-4'}>
        <h2 className="text-lg font-bold">구역 저장</h2>
        <label className="block"><span className="mb-1 block font-semibold">이름</span><input name="name" required maxLength={30} placeholder="주방" className={input} /></label>
        <label className="block"><span className="mb-1 block font-semibold">용도</span>
          <select value={purpose} onChange={(e) => setPurpose(e.target.value as 'danger' | 'bed')} className={input}>{Object.entries(ZONE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        {purpose === 'bed' && (
          <div className="flex gap-4">
            <label className="block flex-1"><span className="mb-1 block font-semibold">취침 시작</span><input name="from" type="time" required defaultValue="21:00" className={input} /></label>
            <label className="block flex-1"><span className="mb-1 block font-semibold">취침 끝</span><input name="to" type="time" required defaultValue="07:00" className={input} /></label>
          </div>
        )}
        <label className="block"><span className="mb-1 block font-semibold">알릴 기준 시간(초, 선택)</span><input name="dwell" type="number" min={1} max={3600} placeholder={purpose === 'danger' ? '기본 3초' : '기본 30초'} className={input} /></label>
        <ErrorText>{error}</ErrorText>
        <button disabled={full} className={btn + ' w-full'}>{full ? `구역은 ${MAX_ZONES}개까지예요` : '구역 저장'}</button>
      </form>

      <section className="space-y-2" aria-live="polite">
        <h2 className="text-lg font-bold">저장된 구역</h2>
        {zones.data && !zones.data.length && <Empty>아직 구역이 없어요.</Empty>}
        {zones.data?.map((z) => (
          <div key={z.id} className="flex items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white p-3">
            <span><b>{z.name}</b> · {ZONE_LABEL[z.purpose]}{z.purpose === 'bed' && ` ${z.active_from}~${z.active_to}`} · {z.dwell_sec}초</span>
            <button onClick={() => remove(z)} className={btn2}>삭제</button>
          </div>
        ))}
      </section>
    </div>
  )
}
