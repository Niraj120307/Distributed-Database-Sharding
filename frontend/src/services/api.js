import axios from 'axios'

export const api = axios.create({
  baseURL: localStorage.getItem('shardx-api-url') || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 5000,
})

// This checks whether an HTTP server responds at the configured base URL. It
// does not imply that the Python project has API routes or database access.
export async function testApiBase(value) {
  let url
  try {
    url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid protocol')
  } catch {
    return { reachable: false, message: 'Enter a valid http:// or https:// URL in Settings.' }
  }
  try {
    const response = await api.get(url.toString(), { timeout: 5000, validateStatus: () => true })
    return {
      reachable: true,
      message: `HTTP server responded with status ${response.status}. This only confirms URL reachability; no backend API routes are defined in this project.`,
    }
  } catch {
    return { reachable: false, message: 'No HTTP response received. Check the URL and whether a server is running there.' }
  }
}

// Add route implementations here only after the backend defines them.
export const clusterService = {
  async getNodes() { throw new Error('Unavailable: the backend has no HTTP node endpoint.') },
  async getShards() { throw new Error('Unavailable: the backend has no HTTP shard endpoint.') },
}

export const queryService = {
  async execute() { throw new Error('Unavailable: the backend has no HTTP query endpoint.') },
}
