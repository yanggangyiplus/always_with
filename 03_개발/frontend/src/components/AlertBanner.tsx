import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

type Note = { id: number; event_id: number | null; title: string; camera_name: string | null; sent_at: string; read_at: string | null }
const FRESH_MS = 10 * 60_000 // 오래전에 쌓인 안 읽은 알림이 로그인할 때마다 뜨지 않게, 최근 10분 것만 띄운다

/** 어느 화면에 있든 새 알림(낙상 등)이 오면 맨 위에 크게 보여 준다. 3초마다 확인한다. */
export default function AlertBanner() {
  const [notes, setNotes] = useState<Note[]>([])

  useEffect(() => {
    const load = () => api<Note[]>('/notifications').then((all) => setNotes(
      all.filter((n) => !n.read_at && Date.now() - new Date(n.sent_at + 'Z').getTime() < FRESH_MS)), () => {})
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [])

  if (!notes.length) return null
  const top = notes[0]
  const clear = () => {
    setNotes([])
    notes.forEach((n) => api(`/notifications/${n.id}/read`, { method: 'POST' }).catch(() => {}))
  }
  return (
    <div role="alert" className="fixed inset-x-3 top-3 z-30 mx-auto flex max-w-3xl flex-wrap items-center gap-3 rounded-2xl bg-red-600 p-4 text-white shadow-xl">
      <p className="mr-auto text-lg font-bold">
        {top.title.replace('낙상 의심', '낙상이 감지되었습니다')}
        {top.camera_name && <span className="ml-2 text-base font-semibold text-red-100">{top.camera_name}</span>}
        {notes.length > 1 && <span className="ml-2 text-base font-semibold text-red-100">외 {notes.length - 1}건</span>}
      </p>
      {top.event_id && <Link to={`/events/${top.event_id}`} onClick={clear} className="inline-flex min-h-11 items-center rounded-full bg-white px-4 font-semibold text-red-700">확인하기</Link>}
      <button onClick={clear} className="min-h-11 rounded-full border border-white px-4 font-semibold">닫기</button>
    </div>
  )
}
