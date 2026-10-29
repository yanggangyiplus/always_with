import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useFetch } from '../lib/useFetch'
import { useSession } from '../lib/auth'
import type { Me } from '../lib/types'
import { btn, ErrorText, input } from '../components/ui'

const SOCIAL = [
  ['google', 'Google', 'border-[1.5px] border-ink bg-white text-ink'],
  ['kakao', '카카오', 'bg-[#FEE500] text-[#191919]'],
  ['naver', '네이버', 'bg-[#03C75A] text-white'],
] as const
const ROLES = [['guardian', '보호자', '부모님과 아이를 돌봐요'], ['parent', '부모님·아이', '보호자 코드로 연결해요']] as const

export default function Auth() {
  const { signIn } = useSession()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<'login' | 'register'>(params.get('mode') === 'register' ? 'register' : 'login')
  const [role, setRole] = useState<'guardian' | 'parent'>()
  const [show, setShow] = useState(false)
  const [error, setError] = useState(params.get('error') ?? '')
  const enabled = useFetch<Record<string, boolean>>('/auth/oauth/providers').data

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    if (mode === 'register' && !role) return setError('보호자인지 부모님인지 먼저 선택해 주세요')
    try {
      const r = await api<{ access_token: string; user: Me }>(`/auth/${mode}`, { method: 'POST', json: { email: f.get('email'), password: f.get('password'), ...(mode === 'register' && { role }) } })
      signIn(r.access_token, r.user)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <h1 className="mb-1 text-5xl">Always with<span className="m-dot" /></h1>
      <p className="mb-8 text-slate-600">평소에는 조용히, 이상할 때만 알려드려요.</p>
      <form onSubmit={submit} className="space-y-4">
        {mode === 'register' && (
          <fieldset className="grid grid-cols-2 gap-3">
            <legend className="mb-2 font-semibold">어떤 분이세요?</legend>
            {ROLES.map(([v, title, desc]) => (
              <label key={v} className={`min-h-12 cursor-pointer rounded-[28px] border-[1.5px] p-4 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-300 ${role === v ? 'border-brand-600 bg-brand-50' : 'border-transparent bg-pale'}`}>
                <input type="radio" name="role" className="sr-only" checked={role === v} onChange={() => { setRole(v); setError('') }} />
                <span className="block text-lg font-bold">{title}</span>
                <span className="text-sm text-slate-600">{desc}</span>
              </label>
            ))}
          </fieldset>
        )}
        <label className="block"><span className="mb-1 block font-semibold">이메일</span><input name="email" type="email" required autoComplete="email" className={input} /></label>
        <label className="block">
          <span className="mb-1 block font-semibold">비밀번호</span>
          <div className="flex gap-2">
            <input name="password" type={show ? 'text' : 'password'} required minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} className={input} />
            <button type="button" onClick={() => setShow(!show)} aria-pressed={show} className="min-h-12 shrink-0 px-2 text-sm underline">{show ? '숨기기' : '보기'}</button>
          </div>
          {mode === 'register' && <span className="text-sm text-slate-600">8자 이상</span>}
        </label>
        <ErrorText>{error}</ErrorText>
        <button className={btn + ' w-full'}>{mode === 'login' ? '로그인' : '가입하기'}</button>
      </form>
      <div className="my-6 flex items-center gap-3 text-sm text-slate-600"><span className="h-px flex-1 bg-ink/20" />또는<span className="h-px flex-1 bg-ink/20" /></div>
      <div className="space-y-2">
        {SOCIAL.map(([p, name, style]) => enabled?.[p] ? (
          <a key={p} href={`/api/auth/oauth/${p}/start${mode === 'register' && role ? `?role=${role}` : ''}`}
            onClick={(e) => { if (mode === 'register' && !role) { e.preventDefault(); setError('보호자인지 부모님인지 먼저 선택해 주세요') } }}
            className={`flex min-h-12 items-center justify-center rounded-full px-5 font-semibold focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none ${style}`}>
            {name}로 {mode === 'login' ? '로그인' : '가입하기'}
          </a>
        ) : (
          <button key={p} disabled className="flex min-h-12 w-full items-center justify-center rounded-full bg-slate-200 px-5 font-semibold text-slate-600">{name}로 {mode === 'login' ? '로그인' : '가입하기'} (준비 중)</button>
        ))}
      </div>
      <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }} className="mt-4 min-h-12 w-full text-slate-700 underline">
        {mode === 'login' ? '처음이세요? 가입하기' : '이미 계정이 있어요'}
      </button>
    </div>
  )
}
