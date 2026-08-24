// Mirrors app/probability.py's parlay math, for showing a live combined-odds
// preview client-side before the slip is placed. The backend recomputes this
// itself on submit — this is display-only, never trusted for the real bet.

const americanToDecimal = (price) => (price > 0 ? 1 + price / 100 : 1 + 100 / -price)

const decimalToAmerican = (decimal) => (decimal >= 2 ? Math.round((decimal - 1) * 100) : Math.round(-100 / (decimal - 1)))

export function parlayCombinedPrice(prices) {
  if (!prices.length) return null
  const combinedDecimal = prices.reduce((acc, price) => acc * americanToDecimal(price), 1)
  return decimalToAmerican(combinedDecimal)
}
