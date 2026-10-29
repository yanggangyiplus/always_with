import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { analyzeFrame, api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import type { Camera } from '../lib/types'
import { btn, btn2, CameraBadge, ErrorText } from '../components/ui'

const HEARTBEAT_MS = 10_000 // 서버는 30초 무신호면 오프라인으로 본다

export default function Stream() {
  const { id } = useParams()
  const cams = useFetch<Camera[]>('/cameras')
  const video = useRef<HTMLVideoElement>(null)
  const media = useRef<MediaStream>(null)
  const timer = useRef<number>(0)
  const [on, setOn] = useState(false)
  const [asking, setAsking] = useState(false) // 브라우저의 카메라 권한 창 응답을 기다리는 중
  const [error, setError] = useState('')
  const [pose, setPose] = useState<string | null>(null)
  const cam = cams.data?.find((c) => c.id === Number(id))

  const stop = () => {
    clearInterval(timer.current)
    media.current?.getTracks().forEach((t) => t.stop())
    media.current = null
    setOn(false)
    setPose(null)
  }
  useEffect(() => stop, [])

  // 프레임을 서버로 보내 관절이 그려진 화면을 받는다. 응답이 오면 다음 프레임을 보낸다.
  async function analyzeLoop() {
    const canvas = document.createElement('canvas')
    canvas.width = 640
    canvas.height = 480
    const ctx = canvas.getContext('2d')!
    ctx.setTransform(-1, 0, 0, 1, 640, 0) // 거울처럼 먼저 뒤집어 보내면, 서버가 그리는 글자는 뒤집히지 않는다
    while (media.current) {
      ctx.drawImage(video.current!, 0, 0, 640, 480)
      const jpeg = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/jpeg', 0.7))
      const url = jpeg && (await analyzeFrame(Number(id), jpeg).catch(() => null))
      setPose((old) => { if (old) URL.revokeObjectURL(old); return url })
      setError(url ? '' : '관절 분석 화면을 받지 못하고 있어요. 서버가 켜져 있는지 확인해 주세요.')
      await new Promise((ok) => setTimeout(ok, url ? 50 : 1000))
    }
  }

  async function start() {
    setError('')
    setAsking(true)
    try {
      media.current = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
    } catch {
      return setError('카메라를 켤 수 없어요. 주소창 옆 자물쇠 아이콘에서 카메라 권한을 허용해 주세요.')
    } finally {
      setAsking(false)
    }
    video.current!.srcObject = media.current
    const beat = () => api(`/cameras/${id}/heartbeat`, { method: 'POST' }).then(cams.reload, (e) => setError(e.message))
    beat()
    timer.current = window.setInterval(beat, HEARTBEAT_MS)
    setOn(true)
    analyzeLoop()
  }

  return (
    <div className="space-y-4">
      <Link to="/cameras" className="inline-flex min-h-12 items-center font-semibold text-brand-800 underline">카메라 목록으로</Link>
      <h1 className="text-2xl font-bold">{cam?.name ?? '카메라'} 켜기</h1>
      {/* 분석 화면이 오면 영상은 숨기되, 프레임을 뜨는 원본으로 계속 켜 둔다 */}
      <video ref={video} autoPlay muted playsInline className={pose ? 'sr-only' : '-scale-x-100 aspect-[4/3] w-full rounded-2xl bg-slate-900'} />
      {pose && <img src={pose} alt="관절이 표시된 카메라 화면" className="aspect-[4/3] w-full rounded-2xl bg-slate-900 object-cover" />}
      <p aria-live="polite" className={`rounded-2xl p-4 font-semibold ${on ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
        {on ? '● 카메라가 켜져 있어요' : asking ? '카메라 권한을 기다리는 중이에요. 브라우저가 물으면 "허용"을 눌러 주세요.' : '카메라가 꺼져 있어요'} {cam && on && <CameraBadge status={cam.status} />}
      </p>
      <ErrorText>{error}</ErrorText>
      {on ? <button onClick={stop} className={btn2 + ' w-full'}>카메라 끄기</button> : <button onClick={start} disabled={asking} className={btn + ' w-full'}>{asking ? '켜는 중…' : '카메라 켜기'}</button>}
      <p className="text-sm text-slate-600">화면에는 사람의 관절이 점과 선으로 표시돼요. 영상은 분석하는 동안에만 서버로 보내고 저장하지 않아요. 이 창을 닫거나 다른 화면으로 가면 카메라가 꺼져요.</p>
    </div>
  )
}
