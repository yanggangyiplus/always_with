import { ZONE_LABEL, type Zone } from '../lib/types'

type Box = Pick<Zone, 'x' | 'y' | 'w' | 'h'>
const pct = (b: Box) => ({ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` })

/** 4:3 화면 위에 구역 사각형을 겹쳐 그린다. 부모는 relative여야 한다. */
export function ZoneBoxes({ zones, draft }: { zones: Zone[]; draft?: Box | null }) {
  return (
    <>
      {zones.map((z) => (
        <div key={z.id} style={pct(z)} className={`pointer-events-none absolute border-2 ${z.purpose === 'danger' ? 'border-red-500 bg-red-500/20' : 'border-sky-400 bg-sky-400/20'}`}>
          <span className="absolute left-0 top-0 bg-black/60 px-1 text-xs font-semibold text-white">{z.name} · {ZONE_LABEL[z.purpose]}</span>
        </div>
      ))}
      {draft && <div style={pct(draft)} className="pointer-events-none absolute border-2 border-dashed border-white bg-white/25" />}
    </>
  )
}
