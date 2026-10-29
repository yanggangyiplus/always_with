import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useSession } from '../lib/auth'
import type { Me } from '../lib/types'

/** 소셜 로그인이 끝나고 서버가 돌려보내는 곳. 토큰은 주소의 # 뒤로 오고, 읽자마자 주소에서 지운다. */
export default function OAuthDone() {
  const { signIn } = useSession()
  const nav = useNavigate()
  const ran = useRef(false) // 개발 모드에서 효과가 두 번 돌아도, 이미 지운 주소를 다시 읽지 않게 한다

  useEffect(() => {
    if (ran.current) return
    ran.current = true
    const h = new URLSearchParams(location.hash.slice(1))
    const token = h.get('token')
    history.replaceState(null, '', '/oauth')
    const fail = (msg: string) => nav(`/login?error=${encodeURIComponent(msg)}`, { replace: true })
    if (!token) { fail(h.get('error') ?? '로그인에 실패했어요'); return }
    localStorage.setItem('token', token)
    api<Me>('/me').then((me) => { signIn(token, me); nav('/', { replace: true }) }, () => { localStorage.removeItem('token'); fail('로그인에 실패했어요') })
  }, [nav, signIn])

  return <p aria-live="polite" className="p-6 text-slate-600">로그인하는 중…</p>
}
