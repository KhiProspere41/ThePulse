import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

export const getOdds = (league = 'nfl', week) =>
  api.get('/odds', { params: { league, ...(week ? { week } : {}) } }).then((r) => r.data)

export const getLines = (gameId) => api.get('/lines', { params: { game: gameId } }).then((r) => r.data)

export const createPick = (pick) => api.post('/picks', pick).then((r) => r.data)

export const getPicks = () => api.get('/picks').then((r) => r.data)

export const setPickResult = (id, result) =>
  api.patch(`/picks/${id}/result`, null, { params: { result } }).then((r) => r.data)

export const getDashboard = () => api.get('/stats/dashboard').then((r) => r.data)

export const getEloRatings = (league = 'nfl') => api.get('/elo/ratings', { params: { league } }).then((r) => r.data)

export const getEloValue = (league, week) => api.get('/elo/value', { params: { league, week } }).then((r) => r.data)

export const getPropMarkets = () => api.get('/props/markets').then((r) => r.data)

// `refresh` spends Odds API credits — only pass it from an explicit user action.
export const getProps = (gameId, refresh = false) =>
  api.get(`/props/${gameId}`, { params: { refresh } }).then((r) => r.data)

export const getSuperBowlFutures = (refresh = false) =>
  api.get('/futures/super-bowl', { params: { refresh } }).then((r) => r.data)

export const getFuturesBoard = (iterations) =>
  api.get('/futures/board', { params: { ...(iterations ? { iterations } : {}) } }).then((r) => r.data)

export const getDivisionRaces = () => api.get('/futures/divisions').then((r) => r.data)

export const getApiUsage = () => api.get('/stats/api-usage').then((r) => r.data)

export const getPlayerStatsSeasons = () => api.get('/player-stats/seasons').then((r) => r.data)

export const getPlayerStatsLeaders = (category = 'overall', season) =>
  api.get('/player-stats/leaders', { params: { category, ...(season ? { season } : {}) } }).then((r) => r.data)

export const getPlayerStatsAwards = (season) =>
  api.get('/player-stats/awards', { params: { ...(season ? { season } : {}) } }).then((r) => r.data)

export default api
