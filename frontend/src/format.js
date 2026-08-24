export const formatPrice = (price) => (price == null ? '—' : price > 0 ? `+${price}` : `${price}`)

export const formatPoint = (point) => (point == null ? '' : point > 0 ? `+${point}` : `${point}`)

export const formatPct = (value) => (value == null ? '—' : `${(value * 100).toFixed(1)}%`)

// The backend stores every timestamp as a naive UTC datetime and serializes
// it without a timezone marker (e.g. "2026-09-10T00:15:00", no "Z"). A
// date-time string with no offset is parsed by `Date` as *local* time, not
// UTC — that silently shifted every kickoff by the viewer's UTC offset, and
// for late-evening ET games (which land after midnight UTC) showed the wrong
// calendar day entirely. Appending "Z" tells `Date` what the string already
// means: UTC.
const asUtc = (iso) => (/[Zz]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`)

export const formatDate = (iso) =>
  new Date(asUtc(iso)).toLocaleString('en-US', {
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

export const formatLine = (point) => (point == null ? '' : `${point}`)

// Probabilities from the simulator are 0-1; show them to one decimal so a 0.4%
// Super Bowl chance doesn't render as a flat 0%.
export const formatProb = (value) =>
  value == null ? '—' : value < 0.001 ? '<0.1%' : `${(value * 100).toFixed(1)}%`

export const formatSigned = (value, digits = 1) =>
  value == null ? '—' : `${value > 0 ? '+' : ''}${(value * 100).toFixed(digits)}%`

export const formatUnits = (value) =>
  value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}u`

export const MARKET_LABELS = {
  player_pass_yds: 'Passing Yards',
  player_pass_tds: 'Passing TDs',
  player_rush_yds: 'Rushing Yards',
  player_reception_yds: 'Receiving Yards',
  player_receptions: 'Receptions',
  player_anytime_td: 'Anytime TD',
  h2h: 'Moneyline',
  spreads: 'Spread',
  totals: 'Total',
  outrights: 'Futures',
}

export const marketLabel = (key) => MARKET_LABELS[key] ?? key
