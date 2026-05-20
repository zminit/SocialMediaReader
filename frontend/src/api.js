import axios from 'axios'

const api = axios.create({ baseURL: '/', timeout: 120000 })

export default {
  // Health
  health: () => api.get('/health'),

  // Stats
  getStats: () => api.get('/api/stats'),

  // Topics
  listTopics: () => api.get('/api/topics'),
  getTopic: (id) => api.get(`/api/topics/${id}`),
  createTopic: (data) => api.post('/api/topics', data),
  updateTopic: (id, data) => api.put(`/api/topics/${id}`, data),

  // Sources
  listSources: (params = {}) => api.get('/api/sources', { params }),
  getSource: (id) => api.get(`/api/sources/${id}`),

  // Analysis
  listAnalysis: (params) => api.get('/api/analysis', { params }),
  getAnalysisBySource: (sourceId) => api.get(`/api/analysis/source/${sourceId}`),

  // Jobs
  listJobs: () => api.get('/api/jobs'),
  getSchedulerStatus: () => api.get('/api/jobs/status'),
  triggerJob: (data) => api.post('/api/jobs/trigger', data),

  // Logs
  queryLogs: (params = {}) => api.get('/api/logs', { params }),
  getLogStats: () => api.get('/api/logs/stats'),
  clearLogs: (before) => api.delete('/api/logs', { params: before ? { before } : {} }),
}
