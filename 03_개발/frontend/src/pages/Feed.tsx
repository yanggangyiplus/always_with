import { useNavigate } from 'react-router-dom'
import { useEffect, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { api, photoUrl, shrink, uploadPhoto } from '../lib/api'
import { useSession } from '../lib/auth'
import { fmtTime, type Post } from '../lib/types'
import { useSeen } from '../lib/seen'
import { useFetch } from '../lib/useFetch'
import { useLocation } from '../lib/location'
import { btn, btn2, Empty, ErrorText } from '../components/ui'

const QUICK = ['잘 지내요', '식사했어요', '산책 다녀왔어요', '보고 싶어요']
const MAX_PHOTOS = 5
const here = () => new Promise<GeolocationPosition>((ok, no) => navigator.geolocation.getCurrentPosition(ok, no, { timeout: 10_000 }))
const ago = (iso: string) => {
  const m = Math.round((Date.now() - new Date(iso + 'Z').getTime()) / 60_000)
  return m < 1 ? '방금 전' : m < 60 ? `${m}분 전` : m < 1440 ? `${Math.floor(m / 60)}시간 전` : fmtTime(iso)
}
const textarea = 'min-h-24 w-full resize-none rounded-2xl border-[1.5px] border-ink/30 bg-white p-3 text-base focus-visible:border-brand-600 focus-visible:ring-4 focus-visible:ring-brand-300 focus-visible:outline-none'

function Avatar({ name }: { name: string }) {
  return <span aria-hidden className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-600 font-bold text-white">{name.slice(0, 1)}</span>
}

function Photo({ postId, photoId, small }: { postId: number; photoId: number; small?: boolean }) {
  const [src, setSrc] = useState<string | null>()
  useEffect(() => {
    let url: string | null = null
    photoUrl(postId, photoId).then((u) => setSrc((url = u)), () => setSrc(null))
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [postId, photoId])
  const size = small ? 'h-20 w-20 rounded-2xl' : 'aspect-square w-full snap-center'
  return src === null ? <div className={`grid ${size} shrink-0 place-items-center bg-white text-center text-xs text-slate-600`}>불러오지 못했어요</div>
    : <img src={src} alt="" className={`${size} shrink-0 bg-white object-cover`} />
}

function Carousel({ post }: { post: Post }) {
  const [i, setI] = useState(0)
  const n = post.photo_ids.length
  return (
    <div className="relative">
      <div onScroll={(e) => setI(Math.round(e.currentTarget.scrollLeft / e.currentTarget.clientWidth))} aria-label={`사진 ${n}장`} className="flex snap-x snap-mandatory overflow-x-auto [scrollbar-width:none]">
        {post.photo_ids.map((id) => <Photo key={id} postId={post.id} photoId={id} />)}
      </div>
      {n > 1 && <span className="absolute top-3 right-3 rounded-full bg-ink/70 px-3 py-1 text-xs font-semibold text-white">{i + 1}/{n}</span>}
      {n > 1 && <div aria-hidden className="absolute inset-x-0 bottom-3 flex justify-center gap-1.5">{post.photo_ids.map((id, k) => <span key={id} className={`h-1.5 w-1.5 rounded-full ${k === i ? 'bg-white' : 'bg-white/50'}`} />)}</div>}
    </div>
  )
}

function Card({ post, mine, onChange }: { post: Post; mine: boolean; onChange: () => void }) {
  const nav = useNavigate()
  const [menu, setMenu] = useState(false)
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(post.text)
  const [error, setError] = useState('')
  const run = (p: Promise<unknown>) => p.then(onChange, (e) => setError(e.message))

  return (
    <article className="overflow-hidden rounded-[28px] bg-pale">
      <header className="relative flex items-center gap-3 px-4 py-3">
        <Avatar name={post.author_name} />
        <p className="min-w-0 flex-1"><span className="block font-bold">{mine ? '나' : post.author_name}</span><span className="block text-xs text-slate-600">{ago(post.created_at)}{mine && post.audience_names.length > 0 && ` · ${post.audience_names.join(', ')}에게만`}</span></p>
        {mine && <button onClick={() => setMenu(!menu)} aria-expanded={menu} aria-label="더 보기" className="min-h-12 min-w-12 rounded-full text-2xl hover:bg-white">⋯</button>}
        {menu && (
          <div className="absolute top-14 right-4 z-10 flex flex-col overflow-hidden rounded-2xl bg-white shadow-lg ring-1 ring-ink/10">
            <button onClick={() => { setText(post.text); setEditing(true); setMenu(false) }} className="min-h-12 px-6 text-left font-semibold hover:bg-pale">수정</button>
            <button onClick={() => { setMenu(false); if (confirm('이 글을 지울까요?')) run(api(`/posts/${post.id}`, { method: 'DELETE' })) }} className="min-h-12 px-6 text-left font-semibold text-red-700 hover:bg-pale">삭제</button>
          </div>
        )}
      </header>

      {post.photo_ids.length > 0 && <Carousel post={post} />}

      <div className="space-y-1 px-4 pt-1 pb-4">
        <div className="flex items-center gap-1">
          <button onClick={() => run(api(`/posts/${post.id}/like`, { method: 'POST' }))} aria-pressed={post.liked} aria-label="좋아요" className={`min-h-12 min-w-12 rounded-full text-2xl hover:bg-white ${post.liked ? 'text-red-600' : ''}`}>{post.liked ? '♥' : '♡'}</button>
          <button onClick={() => nav('/chat', { state: { reply: { id: post.id, author_name: mine ? '나' : post.author_name, text: post.text.slice(0, 80) } } })} className="flex min-h-12 items-center rounded-full px-3 text-sm font-semibold text-brand-800 underline hover:bg-white">채팅으로 답장</button>
          {post.lat != null && <a href={`https://www.openstreetmap.org/?mlat=${post.lat}&mlon=${post.lng}#map=16/${post.lat}/${post.lng}`} target="_blank" rel="noreferrer" className="flex min-h-12 items-center rounded-full px-3 text-sm font-semibold text-brand-800 underline">올린 곳 보기</a>}
        </div>
        {post.likes > 0 && <p className="text-sm font-bold">좋아요 {post.likes}개</p>}
        {editing ? (
          <form onSubmit={(e) => { e.preventDefault(); run(api(`/posts/${post.id}`, { method: 'PATCH', json: { text } }).then(() => setEditing(false))) }} className="space-y-2">
            <label><span className="sr-only">글 수정</span><textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={500} required className={textarea} /></label>
            {post.photo_ids.length > 0 && (
              <div>
                <div className="flex flex-wrap gap-2">
                  {post.photo_ids.map((id, k) => (
                    <div key={id} className="relative">
                      <Photo postId={post.id} photoId={id} small />
                      <button type="button" onClick={() => confirm('이 사진을 지울까요?') && run(api(`/posts/${post.id}/photos/${id}`, { method: 'DELETE' }))} aria-label={`사진 ${k + 1} 지우기`} className="absolute -top-2 -right-2 h-8 w-8 rounded-full bg-ink text-white">×</button>
                    </div>
                  ))}
                </div>
                <p className="mt-1 text-sm text-slate-600">사진은 지우기만 할 수 있어요. 더 올리려면 새 글로 올려 주세요.</p>
              </div>
            )}
            <div className="flex gap-2"><button className={btn}>저장</button><button type="button" onClick={() => { setEditing(false); setText(post.text) }} className={btn2}>취소</button></div>
          </form>
        ) : <p className="text-base break-words"><span className="font-bold">{mine ? '나' : post.author_name}</span> {post.text}</p>}
        <ErrorText>{error}</ErrorText>
      </div>
    </article>
  )
}

function Composer({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const { data: loc } = useLocation()
  const members = loc?.members ?? []
  const [text, setText] = useState('')
  const [files, setFiles] = useState<Blob[]>([]) // 고르는 즉시 줄여 둔 JPEG
  const [previews, setPreviews] = useState<string[]>([])
  const [audience, setAudience] = useState<number[]>([]) // 비어 있으면 전체
  const [withPlace, setWithPlace] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f))
    setPreviews(urls)
    return () => urls.forEach(URL.revokeObjectURL)
  }, [files])

  // 사진을 고르거나 끌어다 놓는 즉시 읽는다. 읽을 수 없는 파일(HEIC 등)은 올리기 전에 알려 준다.
  async function add(picked: File[]) {
    setError('')
    const ok: Blob[] = []
    let skipped = 0
    for (const f of picked.slice(0, MAX_PHOTOS - files.length)) {
      if (!f.type.startsWith('image/')) { skipped++; continue }
      try { ok.push(await shrink(f)) } catch { skipped++ }
    }
    if (skipped) setError(`읽을 수 없는 파일 ${skipped}개는 뺐어요. JPG나 PNG 사진을 골라 주세요.`)
    setFiles((old) => [...old, ...ok].slice(0, MAX_PHOTOS))
  }
  const pickFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []) // 입력을 비우기 전에 먼저 꺼내 둔다
    e.target.value = ''
    add(picked)
  }
  const drop = (e: DragEvent) => { e.preventDefault(); add(Array.from(e.dataTransfer.files)) }
  const toggle = (id: number) => {
    const next = audience.includes(id) ? audience.filter((x) => x !== id) : [...audience, id]
    setAudience(next.length === members.length ? [] : next) // 가족을 모두 골랐으면 전체와 같다
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const pos = withPlace ? (await here().catch(() => { throw new Error('위치를 가져올 수 없어요. 브라우저의 위치 권한을 확인해 주세요.') })).coords : null
      const post = await api<Post>('/posts', { method: 'POST', json: { text, audience: audience.length ? audience : undefined, lat: pos?.latitude, lng: pos?.longitude } })
      for (const j of files) await uploadPhoto(post.id, j)
      onDone()
    } catch (err) { setError((err as Error).message); setBusy(false) }
  }

  const chip = (on: boolean) => `min-h-11 rounded-full px-4 text-sm font-semibold ${on ? 'bg-ink text-white' : 'bg-white hover:brightness-95'}`
  return (
    <form onSubmit={submit} onDragOver={(e) => e.preventDefault()} onDrop={drop} className="space-y-3 rounded-[28px] bg-pale p-4">
      <h2 className="font-sans text-lg font-bold tracking-normal">새 글</h2>
      <div className="flex flex-wrap gap-2">
        {previews.map((u, i) => (
          <div key={u} className="relative">
            <img src={u} alt={`선택한 사진 ${i + 1}`} className="h-20 w-20 rounded-2xl object-cover" />
            <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))} aria-label={`사진 ${i + 1} 빼기`} className="absolute -top-2 -right-2 h-8 w-8 rounded-full bg-ink text-white">×</button>
          </div>
        ))}
        {files.length < MAX_PHOTOS && (
          <label className="grid h-20 w-20 cursor-pointer place-items-center rounded-2xl border-[1.5px] border-dashed border-ink/50 bg-white text-center text-sm font-semibold hover:brightness-95 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-brand-300">
            <span>사진 선택<br />{files.length}/{MAX_PHOTOS}</span>
            <input type="file" accept="image/*" multiple onChange={pickFiles} className="sr-only" />
          </label>
        )}
      </div>
      <p className="text-xs text-slate-600">사진은 {MAX_PHOTOS}장까지, 파일을 여기로 끌어다 놓아도 돼요.</p>
      <label className="block"><span className="sr-only">글</span><textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={500} required placeholder="사진에 대한 이야기나 오늘 안부를 적어 보세요" className={textarea} /></label>
      <div className="flex flex-wrap gap-2">
        {QUICK.map((q) => <button type="button" key={q} onClick={() => setText(q)} className="min-h-11 rounded-full bg-white px-4 text-sm font-semibold hover:brightness-95">{q}</button>)}
      </div>
      <fieldset>
        <legend className="mb-1 font-semibold">누구에게 보여 줄까요?</legend>
        <div className="flex flex-wrap gap-2">
          <button type="button" aria-pressed={audience.length === 0} onClick={() => setAudience([])} className={chip(audience.length === 0)}>전체</button>
          {members.map((m) => <button type="button" key={m.user_id} aria-pressed={audience.includes(m.user_id)} onClick={() => toggle(m.user_id)} className={chip(audience.includes(m.user_id))}>{m.name}</button>)}
        </div>
        <p className="mt-1 text-xs text-slate-600">{audience.length ? `고른 사람에게만 보여요. 나는 항상 볼 수 있어요.` : '가족 모두에게 보여요.'}</p>
      </fieldset>
      <label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={withPlace} onChange={(e) => setWithPlace(e.target.checked)} className="h-5 w-5" />지금 있는 곳도 알리기 (이번 글에만 붙어요)</label>
      <ErrorText>{error}</ErrorText>
      <div className="flex gap-2">
        <button disabled={busy || !text.trim()} className={btn + ' flex-1'}>{busy ? '올리는 중…' : '공유하기'}</button>
        <button type="button" onClick={onCancel} disabled={busy} className={btn2}>취소</button>
      </div>
    </form>
  )
}

export default function Feed() {
  const { me } = useSession()
  const posts = useFetch<Post[]>('/posts')
  useSeen('feed')
  useEffect(() => { const t = setInterval(posts.reload, 3000); return () => clearInterval(t) }, [posts.reload])
  const [view, setView] = useState<'family' | 'mine'>('family')
  const [composing, setComposing] = useState(false)

  const shown = posts.data?.filter((p) => view === 'family' || p.author_id === me?.id)
  const tab = (v: typeof view, label: string) => (
    <button onClick={() => setView(v)} aria-pressed={view === v} className={`min-h-11 flex-1 rounded-full px-4 font-semibold ${view === v ? 'bg-ink text-white' : 'text-slate-600 hover:bg-pale'}`}>{label}</button>
  )

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl">피드<span className="m-dot" /></h1>
        {!composing && <button onClick={() => setComposing(true)} className={btn}>새 글</button>}
      </div>
      {composing && <Composer onDone={() => { setComposing(false); setView('family'); posts.reload() }} onCancel={() => setComposing(false)} />}

      <div role="group" aria-label="피드 보기" className="flex gap-1 rounded-full bg-white p-1 ring-1 ring-ink/15">{tab('family', '가족 피드')}{tab('mine', '내 피드')}</div>
      {view === 'mine' && shown && <p className="text-sm font-semibold text-slate-600">내 게시물 {shown.length}개</p>}

      <section className="space-y-5" aria-label="피드 목록">
        {shown && !shown.length && <Empty>{view === 'mine' ? '아직 올린 글이 없어요. 새 글로 첫 사진을 올려 보세요.' : '아직 올라온 글이 없어요. 첫 사진이나 한마디를 남겨 보세요.'}</Empty>}
        {shown?.map((p) => <Card key={p.id} post={p} mine={p.author_id === me?.id} onChange={posts.reload} />)}
      </section>
    </div>
  )
}
