import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Spot } from '../lib/types'

/** 위치를 공유 중인 가족의 마지막 위치를 한 지도에 핀으로 보여 준다. 지도 이미지는 OpenStreetMap에서 받아온다. */
export default function FamilyMap({ spots }: { spots: Spot[] }) {
  const box = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const pins = useRef<L.LayerGroup | null>(null)
  const shown = useRef(-1)

  useEffect(() => {
    map.current = L.map(box.current!, { zoomControl: true }).setView([37.5665, 126.978], 11)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map.current)
    pins.current = L.layerGroup().addTo(map.current)
    shown.current = -1 // 지도를 새로 만들면 핀 맞춤도 다시 한다
    return () => { map.current?.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (!map.current || !pins.current) return
    pins.current.clearLayers()
    const pts = spots.filter((s) => s.sharing && s.lat != null && s.lng != null).map((s) => ({ s, at: [s.lat!, s.lng!] as [number, number] }))
    pts.forEach(({ s, at }) => L.circleMarker(at, { radius: 10, color: '#fff', weight: 3, fillColor: '#6c3cff', fillOpacity: 1 })
      .bindTooltip(s.name, { permanent: true, direction: 'top', offset: [0, -10] }).addTo(pins.current!))
    if (pts.length && pts.length !== shown.current) map.current.fitBounds(L.latLngBounds(pts.map((p) => p.at)), { padding: [40, 40], maxZoom: 16 }) // 30초마다 새로 불러와도 보던 위치가 튀지 않게, 핀 수가 바뀔 때만 맞춘다
    shown.current = pts.length
  }, [spots])

  return <div ref={box} role="region" aria-label="가족 위치 지도" className="isolate h-72 w-full overflow-hidden rounded-2xl border border-ink/10" />
}
