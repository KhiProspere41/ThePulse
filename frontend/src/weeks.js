export const WEEK_RANGE = {
  nfl: { min: 1, max: 18 },
  college: { min: 0, max: 15 },
}

export function weeksForLeague(league) {
  const { min, max } = WEEK_RANGE[league]
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
}
