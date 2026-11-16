import axios from 'axios'

export const api = axios.create({
  baseURL: localStorage.getItem('shardx-api-url') || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 15000,
})

export async function testApiBase(value) {
  try {
    const response = await api.get(new URL('/health', value).toString(), { timeout: 5000 })
    return { reachable: response.data?.database === true, message: response.data?.database ? `API and MySQL are connected (${response.data.nodes_reachable} nodes reachable).` : 'API responded, but MySQL is unavailable.' }
  } catch (error) {
    return { reachable: false, message: error.response?.data?.detail || 'No API/MySQL response. Check the URL and running services.' }
  }
}

export const clusterService = {
  getDashboard: () => api.get('/api/dashboard').then(r => r.data),
  getNodes: () => api.get('/api/nodes').then(r => r.data),
  setNodeStatus: (name, status) => api.patch(`/api/nodes/${encodeURIComponent(name)}/status`, { status }).then(r => r.data),
  getShards: () => api.get('/api/shards').then(r => r.data),
  getStudents: params => api.get('/api/students', { params }).then(r => r.data),
  createStudent: value => api.post('/api/students', value).then(r => r.data),
  updateStudent: (id, value) => api.put(`/api/students/${id}`, value).then(r => r.data),
  deleteStudent: id => api.delete(`/api/students/${id}`).then(r => r.data),
  getExplorer: () => api.get('/api/explorer').then(r => r.data),
  getReplication: () => api.get('/api/replication').then(r => r.data),
  getMigrations: () => api.get('/api/migrations').then(r => r.data),
  query: sql => api.post('/api/query', { sql }).then(r => r.data),
}
