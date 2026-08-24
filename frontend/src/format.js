export const formatPrice = (price) => (price == null ? '—' : price > 0 ? `+${price}` : `${price}`)

export const formatPoint = (point) => (point == null ? '' : point > 0 ? `+${point}` : `${point}`)

export const formatPct = (value) => (value == null ? '—' : `${(value * 100).toFixed(1)}%`)

export const formatDate = (iso) =>
  new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })

export function bestLine(oddsForMarketSide) {
  if (!oddsForMarketSide.length) return null
  return oddsForMarketSide.reduce((best, cur) => (cur.price > best.price ? cur : best))
}
