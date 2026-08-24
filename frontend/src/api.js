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

export const getEloValue = (league = 'nfl') => api.get('/elo/value', { params: { league } }).then((r) => r.data)

export default api
