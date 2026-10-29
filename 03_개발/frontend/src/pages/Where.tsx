import { useState } from 'react'
import { useLocation } from '../lib/location'
import { btn, btn2, card, Empty, ErrorText } from '../components/ui'

const ago = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso + 'Z').getTime()) / 60_000)
  return m < 1 ? '방금 전' : m < 60 ? `${m}분 전` : `${Math.floor(m / 60)}시간 전`
}

export default function Where() {
  const { data, setSharing, geoError } = useLocation()
  const [error, setError] = useState('')
  if (!data) return <p aria-live="polite" className="py-8 text-slate-600">불러오는 중…</p>
  const toggle = () => setSharing(!data.me.sharing).catch((e) => setError(e.message))

  return (
    <div className="space-y-6">
      <h1 className="text-3xl">위치<span className="m-dot" /></h1>
      <section className={card + ' space-y-3'}>
        <p className="font-bold">내 위치 공유: {data.me.sharing ? '켜짐' : '꺼짐'}</p>
        <p className="text-slate-600">
          {data.me.sharing
            ? '이 앱이 열려 있는 동안 1분마다 내 위치를 가족에게 보여 줘요. 언제든 끄면 저장된 위치가 바로 지워져요.'
            : '켜면 가족이 내 마지막 위치를 볼 수 있어요. 켜는 것도, 끄는 것도 내가 정해요. 끄면 저장된 위치는 지워져요.'}
        </p>
        <ErrorText>{error || geoError}</ErrorText>
        <button onClick={toggle} className={(data.me.sharing ? btn2 : btn) + ' w-full'}>{data.me.sharing ? '공유 끄기' : '내 위치 공유 켜기'}</button>
      </section>

      <section className="space-y-3" aria-label="가족 위치">
        {!data.members.length && <Empty>위치를 볼 가족이 아직 없어요.</Empty>}
        {data.members.map((m) => (
          <article key={m.user_id} className={card}>
            <h2 className="font-sans text-lg font-bold tracking-normal">{m.name}</h2>
            {!m.sharing ? <p className="text-slate-600">위치를 공유하고 있지 않아요.</p>
              : m.lat == null ? <p className="text-slate-600">공유를 켰지만 아직 위치가 도착하지 않았어요.</p>
              : (
                <>
                  <p className="text-slate-600">{ago(m.updated_at!)} 마지막 위치</p>
                  <a href={`https://www.openstreetmap.org/?mlat=${m.lat}&mlon=${m.lng}#map=16/${m.lat}/${m.lng}`} target="_blank" rel="noreferrer" className="mt-1 inline-flex min-h-12 items-center font-semibold text-brand-800 underline">지도로 보기</a>
                </>
              )}
          </article>
        ))}
      </section>
    </div>
  )
}
