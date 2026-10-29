import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import '../landing.css'

const START = '/login?mode=register'

const FEATURES = [
  ['가족 피드', '사용 가능', '사진과 글을 올리면 연결된 가족 화면에 몇 초 안에 올라와요. 글마다 보여 줄 가족을 고를 수 있어요.'],
  ['가족 채팅', '사용 가능', '서로 메시지를 주고받아요. 피드 글에 채팅으로 답장할 수도 있어요.'],
  ['부탁해, 일정, 위치', '사용 가능', '대신 해 달라고 부탁하고, 일정을 같이 보고, 위치는 본인이 켰을 때만 나눠요.'],
  ['낙상 의심 알림', '개발 중', '자세가 급격히 바뀌고 한동안 움직이지 않으면 가족에게 알려요. 알림은 타임라인에서 보고 잘못된 알림은 신고해요.'],
  ['위험 구역과 취침 이탈', '개발 중 · 아이', '아이가 주방 같은 곳에 머물거나 잠자리를 벗어나면 알려요. 베타로 제공돼요.'],
  ['외출 기록', '예정', '외출과 귀가를 기록하는 기능은 동의 방식을 정한 뒤 추가할 예정이에요.'],
] as const

const STEPS = [
  ['가족 연결', '보호자가 부모님이나 아이를 추가해요. 부모님께는 6자리 초대 코드를 알려 드려요.'],
  ['동의', '부모님이 코드를 입력하고 직접 동의해요. 아이는 보호자가 법정대리인으로서 동의해요.'],
  ['안부 나누기', '피드에 사진과 글을 올리고, 채팅으로 이야기하고, 필요한 일은 부탁해요.'],
  ['위험 알림 켜기', '카메라를 켜 두면 이상이 감지될 때만 알림이 가요. 평소 화면은 보호자에게 보이지 않아요.'],
] as const

const FAQ = [
  ['피드와 채팅은 누구에게 보이나요?', '연결된 가족에게만 보여요. 피드는 글마다 보여 줄 가족을 고를 수 있어요.'],
  ['영상이 계속 저장되나요?', '아니요. 평소 프레임은 서버 메모리에서만 처리하고 저장하지 않아요. 이상이 감지됐을 때의 짧은 클립 저장은 준비 중이에요.'],
  ['부모님 동의 없이 연결할 수 있나요?', '없어요. 부모님이 초대 코드를 입력하고 직접 동의해야 연결되고, 그 전에는 카메라를 등록할 수 없어요.'],
  ['아이에게도 쓸 수 있나요?', '베타로 지원해요. 성인과 고령자 데이터로 학습한 모델을 쓰기 때문에 놀이 동작을 낙상으로 잘못 알릴 수 있어요.'],
  ['외출도 기록되나요?', '아직 아니에요. 지금 위험 알림은 낙상 의심만 있고, 외출 기록은 동의 방식을 정한 뒤 추가할 예정이에요.'],
  ['의료기기인가요?', '아니요. 보조 알림 도구이고, 모든 낙상을 감지한다고 보장하지 않아요. 가림, 어두운 조명, 여러 사람이 있는 환경에서는 정확도가 떨어질 수 있어요.'],
] as const

const H2 = 'text-[clamp(40px,8.7vw,140px)] leading-[.92]'

export default function Landing() {
  const root = useRef<HTMLDivElement>(null)
  const cta = useRef<HTMLElement>(null)

  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && e.target.classList.add('in')), { threshold: 0.3 })
    root.current?.querySelectorAll('[data-reveal]').forEach((el) => io.observe(el))
    // 마지막 문구는 스크롤에 따라 굵어진다
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches
    const onScroll = () => {
      const r = cta.current?.getBoundingClientRect()
      if (!r || still) return
      const p = Math.min(1, Math.max(0, (innerHeight - r.top) / (innerHeight * 0.9)))
      cta.current!.style.setProperty('--w', String(Math.round(400 + p * 500)))
    }
    onScroll()
    addEventListener('scroll', onScroll, { passive: true })
    return () => { io.disconnect(); removeEventListener('scroll', onScroll) }
  }, [])

  return (
    <div ref={root} className="lp font-sans">
      <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex items-center gap-3 px-[var(--space)] py-3.5">
        <a href="#top" className="pointer-events-auto inline-flex min-h-12 items-center rounded-full bg-ink px-5 font-display text-xl font-extrabold tracking-tight text-white">Always with</a>
        <nav aria-label="주 메뉴" className="pointer-events-auto mx-auto hidden rounded-full bg-ink px-2 text-white md:block">
          <ul className="flex">{[['#about', '소개'], ['#how', '사용 방법'], ['#faq', '질문']].map(([h, l]) => <li key={h}><a href={h} className="lp-link mx-3.5 block py-3.5 text-[15px]">{l}</a></li>)}</ul>
        </nav>
        <Link to={START} className="lp-btn pointer-events-auto ml-auto shadow-[0_0_0_2px_#0d0c11] md:ml-0">시작하기</Link>
      </header>

      <main id="top">
        <section className="lp-hero">
          <div className="grid max-w-lg content-start justify-items-start gap-5 pt-[clamp(92px,14svh,150px)]">
            <p className="text-lg leading-relaxed">언제 어디서나 가족이 서로를 돌봐요. 피드와 채팅으로 안부를 나누고, 위험할 때만 알림이 울려요.</p>
            <div className="flex flex-wrap items-center gap-5"><Link to={START} className="lp-btn">시작하기</Link><Link to="/login" className="lp-link">로그인</Link></div>
          </div>
          <h1 className="lp-hero__title" style={{ ['--len' as string]: 11 }}>
            <span className="lp-hero__mask"><span className="lp-rise">Always with</span></span><span className="m-dot" />
          </h1>
          <div className="lp-hero__stage" aria-hidden><span className="lp-hero__disc" /><span className="lp-hero__orbit"><span className="lp-hero__moon" /></span></div>
        </section>

        <section id="about" className="bg-white px-[var(--space)] py-[clamp(96px,15vh,200px)]">
          <h2 data-reveal className="text-[clamp(40px,8.7vw,140px)] leading-[.92]"><span className="block">언제 어디서나</span><span className="block">서로 돌보는 가족<span className="m-dot" /></span></h2>
          <div className="mt-[clamp(56px,11vh,120px)] grid gap-12 md:grid-cols-[7fr_4fr]">
            <p className="max-w-xl text-[clamp(22px,2.35vw,34px)] leading-[1.25] tracking-tight">사진 한 장, 메시지 하나로 안부를 나누고, 대신 해 달라고 부탁해요. 혼자 사는 부모님이 넘어졌을 때는 영상을 계속 지켜보지 않아도 알림 하나로 알 수 있어요.</p>
            <ul className="grid content-start gap-3 text-lg">{[['#how', '어떻게 쓰나요'], ['#faq', '궁금한 점']].map(([h, l]) => <li key={h}><a href={h} className="lp-link">{l}</a></li>)}</ul>
          </div>
          <ul className="mt-24 grid gap-4 md:grid-cols-3">
            {FEATURES.map(([t, badge, d]) => (
              <li key={t} className="flex min-h-72 flex-col justify-between rounded-[28px] bg-pale p-7">
                <span className="self-start rounded-full border border-ink/30 px-3 py-1 text-sm font-medium">{badge}</span>
                <div><h3 className="font-display text-3xl font-bold tracking-tight">{t}</h3><p className="mt-3 text-slate-600">{d}</p></div>
              </li>
            ))}
          </ul>
        </section>

        <section id="how" className="bg-ink px-[var(--space)] py-[clamp(96px,15vh,200px)] text-white">
          <h2 data-reveal className={H2}>사용 방법<span className="m-dot" /></h2>
          <ol className="mt-24 grid gap-x-12 gap-y-14 md:grid-cols-2">
            {STEPS.map(([t, d], i) => (
              <li key={t} className="border-t border-white/20 pt-6">
                <p className="text-brand-300" aria-hidden>{i + 1}</p>
                <h3 className="mt-2 font-display text-3xl font-bold tracking-tight">{t}</h3>
                <p className="mt-3 max-w-md text-white/70">{d}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="faq" className="bg-white px-[var(--space)] py-[clamp(96px,15vh,200px)]">
          <h2 data-reveal className={H2}>궁금한 점<span className="m-dot" /></h2>
          <div className="mt-20 max-w-3xl divide-y divide-ink/15 border-y border-ink/15">
            {FAQ.map(([q, a]) => (
              <details key={q} className="group py-2">
                <summary className="flex min-h-14 items-center justify-between gap-4 text-xl font-semibold tracking-tight">{q}<span aria-hidden className="lp-plus text-3xl transition-transform">+</span></summary>
                <p className="pb-5 pr-10 text-slate-600">{a}</p>
              </details>
            ))}
          </div>
        </section>

        <section ref={cta} className="bg-brand-600 px-[var(--space)] py-[clamp(96px,15vh,200px)] text-white">
          <p className="lp-cta__title">시작해 볼까요<span className="inline-block h-[.19em] w-[.19em] rounded-full bg-white align-baseline" /></p>
          <div className="mt-12 flex flex-wrap items-center gap-6"><Link to={START} className="lp-btn lp-btn--light">시작하기</Link><Link to="/login" className="lp-link">이미 계정이 있어요</Link></div>
        </section>
      </main>

      <footer className="bg-ink px-[var(--space)] py-12 text-sm text-white/60">
        <p className="max-w-2xl">이 서비스는 의료기기가 아닌 가족 돌봄 도구이며, 낙상 알림은 보조 수단으로 모든 낙상을 감지한다고 보장하지 않습니다. 촬영 대상자의 동의가 필요하고, 평소 영상은 저장하지 않습니다.</p>
        <p className="mt-6">© 2026 Always with · 디자인은 8B design studio 템플릿(MIT)을 참고했어요.</p>
      </footer>
    </div>
  )
}
