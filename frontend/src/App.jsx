import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import GameDetail from './pages/GameDetail'
import Picks from './pages/Picks'
import Dashboard from './pages/Dashboard'
import EloValue from './pages/EloValue'

export default function App() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/game/:id" element={<GameDetail />} />
        <Route path="/picks" element={<Picks />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/elo" element={<EloValue />} />
      </Routes>
    </div>
  )
}
