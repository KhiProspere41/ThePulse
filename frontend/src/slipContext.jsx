import { createContext, useContext, useEffect, useState } from 'react'

const SlipContext = createContext(null)
const STORAGE_KEY = 'thepulse_slip'

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

/**
 * The bet slip: selections queued from anywhere in the app (game odds,
 * player props, futures) before being placed together as straight bets or a
 * parlay. Persisted to localStorage so it survives navigating between pages
 * — a slip is naturally built by visiting several games, not on one screen.
 */
export function SlipProvider({ children }) {
  const [legs, setLegs] = useState(loadInitial)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(legs))
  }, [legs])

  function addLeg(leg) {
    setLegs((current) => {
      if (current.some((l) => l.key === leg.key)) return current // already queued
      return [...current, leg]
    })
  }

  function removeLeg(key) {
    setLegs((current) => current.filter((l) => l.key !== key))
  }

  function clearSlip() {
    setLegs([])
  }

  return (
    <SlipContext.Provider value={{ legs, addLeg, removeLeg, clearSlip }}>{children}</SlipContext.Provider>
  )
}

export function useSlip() {
  const ctx = useContext(SlipContext)
  if (!ctx) throw new Error('useSlip must be used within a SlipProvider')
  return ctx
}
