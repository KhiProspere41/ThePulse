import { Route, Routes } from 'react-router-dom'
import NavBar from './components/NavBar'
import SlipPanel from './components/SlipPanel'
import { SlipProvider } from './slipContext'
import Home from './pages/Home'
import GameDetail from './pages/GameDetail'
import Picks from './pages/Picks'
import Dashboard from './pages/Dashboard'
import EloValue from './pages/EloValue'
import Futures from './pages/Futures'
import PlayerStats from './pages/PlayerStats'

export default function App() {
  return (
    <SlipProvider>
      <div className="min-h-screen">
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/game/:id" element={<GameDetail />} />
          <Route path="/picks" element={<Picks />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/futures" element={<Futures />} />
          <Route path="/player-stats" element={<PlayerStats />} />
          <Route path="/elo" element={<EloValue />} />
        </Routes>
        <SlipPanel />
      </div>
    </SlipProvider>
  )
}
