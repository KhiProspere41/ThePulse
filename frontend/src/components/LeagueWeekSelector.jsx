import { WEEK_RANGE, weeksForLeague } from '../weeks'

export default function LeagueWeekSelector({ league, week, onLeagueChange, onWeekChange }) {
  const { min, max } = WEEK_RANGE[league]
  const weeks = weeksForLeague(league)

  return (
    <div className="flex items-center gap-2">
      <select
        value={league}
        onChange={(e) => onLeagueChange(e.target.value)}
        className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
      >
        <option value="nfl">NFL</option>
        <option value="college">College</option>
      </select>

      <div className="flex items-center rounded border border-slate-700 overflow-hidden">
        <button
          onClick={() => onWeekChange(Math.max(min, week - 1))}
          disabled={week <= min}
          className="px-2.5 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800"
          aria-label="Previous week"
        >
          ←
        </button>
        <select
          value={week}
          onChange={(e) => onWeekChange(Number(e.target.value))}
          className="bg-slate-800 px-3 py-1.5 text-sm border-x border-slate-700"
        >
          {weeks.map((w) => (
            <option key={w} value={w}>
              Week {w}
            </option>
          ))}
        </select>
        <button
          onClick={() => onWeekChange(Math.min(max, week + 1))}
          disabled={week >= max}
          className="px-2.5 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800"
          aria-label="Next week"
        >
          →
        </button>
      </div>
    </div>
  )
}
