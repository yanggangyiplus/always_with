import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useSession } from '../lib/auth'
import { LocationProvider } from '../lib/location'
import InstallButton from './InstallButton'
import { canEnablePush, enablePush } from '../lib/push'

const family = [['/feed', '피드'], ['/chat', '채팅'], ['/plans', '일정'], ['/needs', '부탁해'], ['/where', '위치']] as const
const tabs = { guardian: [['/', '홈'], ...family, ['/cameras', '카메라']], parent: [['/', '홈'], ...family] } as const
const tab = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-full px-4 font-semibold ${isActive ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-pale hover:text-ink'}`

export default function Layout() {
  const { me, signOut } = useSession()
  const [push, setPush] = useState(false)
  useEffect(() => { canEnablePush().then(setPush) }, [])
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-ink/10 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-3 px-4 py-2 md:flex-nowrap">
          <Link to="/" aria-label="Always with 홈으로" className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full bg-ink px-4 font-display text-lg font-extrabold tracking-tight text-white focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none">
            Always with
            <span aria-hidden className="presence h-2 w-2 rounded-full bg-brand-600" />
          </Link>
          <button onClick={signOut} className="ml-auto min-h-11 shrink-0 px-2 text-sm text-slate-600 underline md:order-last">로그아웃</button>
          <nav aria-label="주 메뉴" className="-mx-4 flex w-full gap-1 overflow-x-auto px-4 pt-1 md:mx-0 md:w-auto md:flex-1 md:pt-0">
            {tabs[me!.role].map(([to, label]) => <NavLink key={to} to={to} end={to === '/'} className={tab}>{label}</NavLink>)}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6"><LocationProvider><Outlet /></LocationProvider></main>
      <footer className="mx-auto mt-8 flex max-w-3xl flex-wrap items-center gap-2 border-t border-ink/10 px-4 py-6">
        <p className="mr-auto text-sm text-slate-600">Always with · 언제 어디서나 서로를 돌봐요</p>
        <InstallButton />
        {push && <button onClick={() => enablePush().then(() => setPush(false), (e) => alert(e.message))} className="min-h-11 shrink-0 rounded-full border border-brand-600 px-3 text-sm font-semibold text-brand-800">알림 받기</button>}
      </footer>
    </>
  )
}
