import { useState, type FormEvent } from 'react'
import { api } from '../lib/api'
import { useSession } from '../lib/auth'
import { ErrorText } from '../components/ui'

const big = 'min-h-14 w-full rounded-xl text-xl font-semibold focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none'

export default function Connect({ onLinked }: { onLinked: () => void }) {
  const { signOut } = useSession()
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    try { await api('/invites/accept', { method: 'POST', json: { code: new FormData(e.currentTarget).get('code'), consent } }); onLinked() } catch (err) { setError((err as Error).message) }
  }

  return (
    <div className="mx-auto max-w-md space-y-6 px-4 py-10 text-xl">
        <form onSubmit={submit} className="space-y-5">
          <h1 className="text-3xl font-bold">보호자 코드를 입력해 주세요</h1>
          <input name="code" required inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="one-time-code" aria-label="6자리 코드" className={big + ' border border-slate-300 bg-white text-center font-mono tracking-[0.4em]'} />
          <div className="rounded-2xl bg-slate-100 p-4 text-lg">
            <p className="font-semibold">이렇게 사용돼요</p>
            <p>평소에는 관절 선만 분석하고 영상은 저장하지 않아요. 영상은 연결된 보호자만 볼 수 있어요.</p>
          </div>
          <label className="flex min-h-14 items-start gap-3"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-7 w-7 shrink-0" />위 내용을 읽었고 동의해요</label>
          <ErrorText>{error}</ErrorText>
          <button disabled={!consent} className={big + ' bg-brand-700 text-white hover:bg-brand-800 disabled:bg-slate-300 disabled:text-slate-600'}>연결하기</button>
        </form>
      <button onClick={signOut} className="min-h-14 text-lg underline">로그아웃</button>
    </div>
  )
}
