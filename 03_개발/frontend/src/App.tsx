import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { useFetch } from './lib/useFetch'
import { SessionProvider, useSession } from './lib/auth'
import AddRecipient, { ConnectRecipient } from './pages/AddRecipient'
import Auth from './pages/Auth'
import Cameras from './pages/Cameras'
import Connect from './pages/Connect'
import Chat from './pages/Chat'
import Where from './pages/Where'
import ParentHome from './pages/ParentHome'
import Feed from './pages/Feed'
import Needs from './pages/Needs'
import Plans from './pages/Plans'
import EventDetail from './pages/EventDetail'
import OAuthDone from './pages/OAuthDone'
import Landing from './pages/Landing'
import Home from './pages/Home'
import Stream from './pages/Stream'
import Report from './pages/Report'
import Timeline from './pages/Timeline'

const familyRoutes = (
  <>
    <Route path="feed" element={<Feed />} />
    <Route path="chat" element={<Chat />} />
    <Route path="where" element={<Where />} />
    <Route path="needs" element={<Needs />} />
    <Route path="plans" element={<Plans />} />
  </>
)

function ParentApp() {
  const links = useFetch<{ id: number }[]>('/links')
  if (!links.data) return <p className="p-6 text-xl">불러오는 중…</p>
  if (!links.data.length) return <Connect onLinked={links.reload} />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<ParentHome />} />
        {familyRoutes}
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  )
}

function Routing() {
  const { me, ready } = useSession()
  if (!ready) return null
  if (!me) return (
    <Routes>
      <Route index element={<Landing />} />
      <Route path="login" element={<Auth />} />
      <Route path="oauth" element={<OAuthDone />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
  if (me.role === 'parent') return <ParentApp />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        {familyRoutes}
        <Route path="timeline" element={<Timeline />} />
        <Route path="events/:id" element={<EventDetail />} />
        <Route path="cameras" element={<Cameras />} />
        <Route path="cameras/:id/stream" element={<Stream />} />
        <Route path="recipients/new" element={<AddRecipient />} />
        <Route path="recipients/:id/connect" element={<ConnectRecipient />} />
        <Route path="report" element={<Report />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  )
}

export default () => (
  <BrowserRouter>
    <SessionProvider>
      <Routing />
    </SessionProvider>
  </BrowserRouter>
)
