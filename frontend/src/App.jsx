import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { api, testApiBase } from './services/api.js'

const pages = [
  ['Overview', '/'], ['Nodes', '/nodes'], ['Shards', '/shards'],
  ['Query Console', '/query'], ['Data Explorer', '/data'],
  ['Replication', '/replication'], ['Migrations', '/migrations'],
  ['Settings', '/settings'],
]
const titles = Object.fromEntries(pages)
const initialUrl = localStorage.getItem('shardx-api-url') || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const initialInterval = localStorage.getItem('shardx-refresh-interval') || '0'

function PageHeading({ title, children }) {
  return <div className="page-heading"><h1>{title}</h1>{children && <p>{children}</p>}</div>
}

function EmptyRow({ columns, children = 'No data available. The backend has no HTTP API.' }) {
  return <tr><td className="empty-cell" colSpan={columns}>{children}</td></tr>
}

function DataTable({ headers, children }) {
  return <div className="table-wrap"><table><thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div>
}

function Overview({ status, check, checking }) {
  const stats = [
    ['Total shards', '—'], ['Active nodes', '—'],
    ['Total records', '—'], ['Database connection', 'Unavailable (no API)'],
  ]
  return <>
    <PageHeading title="Overview">Values appear when a compatible backend API is available.</PageHeading>
    <div className="stats-table"><table><tbody>{stats.map(([label, value]) => <tr key={label}><th>{label}</th><td>{value}</td></tr>)}</tbody></table></div>
    <div className="section-title"><h2>Nodes</h2></div>
    <DataTable headers={['Node ID', 'Host', 'Status', 'Assigned shards']}><EmptyRow columns={4} /></DataTable>
    <div className="section-title"><h2>Shard distribution</h2></div>
    <DataTable headers={['Shard ID', 'Assigned node', 'Records', 'Status']}><EmptyRow columns={4} /></DataTable>
    <div className="section-title"><h2>Recent operations</h2></div>
    <DataTable headers={['Time', 'Operation', 'Status']}><EmptyRow columns={3} /></DataTable>
    <p className="page-note">The Python backend currently has command-line operations and direct MySQL connections only. It does not provide data to this browser app.</p>
    <button className="button" type="button" onClick={check} disabled={checking}>{checking ? 'Checking…' : 'Check API URL'}</button>
  </>
}

function Nodes() {
  return <>
    <PageHeading title="Nodes">Node inventory requires an HTTP API. Add, remove, and status operations are not available from the current backend.</PageHeading>
    <DataTable headers={['Node ID', 'Host', 'Status', 'Assigned shards']}><EmptyRow columns={4} /></DataTable>
  </>
}

function Shards() {
  return <>
    <PageHeading title="Shards">Shard metadata and record counts are not exposed through HTTP.</PageHeading>
    <DataTable headers={['Shard ID', 'Assigned node', 'Records', 'Status']}><EmptyRow columns={4} /></DataTable>
    <div className="section-title"><h2>Consistent hashing</h2></div>
    <p className="page-note">The backend includes a consistent hashing implementation, but does not expose ring positions or shard mappings to the frontend.</p>
  </>
}

function QueryConsole() {
  const [sql, setSql] = useState('')
  return <>
    <PageHeading title="Query Console">SQL execution is unavailable because the backend has no HTTP query endpoint.</PageHeading>
    <label className="field-label" htmlFor="sql">SQL query</label>
    <textarea id="sql" className="sql-editor" spellCheck="false" value={sql} onChange={event => setSql(event.target.value)} placeholder="Enter SQL query" />
    <div className="form-actions">
      <button className="button button-primary" type="button" disabled title="Requires a backend HTTP query endpoint">Execute unavailable</button>
      <button className="button" type="button" onClick={() => setSql('')}>Clear</button>
    </div>
    <p className="page-note">No query was sent. The backend currently exposes database operations through Python functions and a CLI.</p>
    <div className="section-title"><h2>Results</h2></div>
    <DataTable headers={['Results']}><EmptyRow columns={1}>No query results.</EmptyRow></DataTable>
  </>
}

function DataExplorer() {
  return <>
    <PageHeading title="Data Explorer">Database, table, schema, and record browsing requires HTTP endpoints.</PageHeading>
    <p className="page-note">The current Python backend implements student CRUD functions for direct use by its CLI. It does not expose database or table listings to this frontend.</p>
    <DataTable headers={['Database', 'Tables']}><EmptyRow columns={2} /></DataTable>
  </>
}

function Replication() {
  return <>
    <PageHeading title="Replication">The backend can copy student records to a replica, but does not expose replication state or event history over HTTP.</PageHeading>
    <DataTable headers={['Primary node', 'Replica node', 'Status', 'Last synchronized']}><EmptyRow columns={4} /></DataTable>
  </>
}

function Migrations() {
  return <>
    <PageHeading title="Migrations">Migration history exists in the Python modules but is not available through HTTP. No migration controls are exposed here.</PageHeading>
    <DataTable headers={['Migration ID', 'Source node', 'Destination node', 'Status', 'Records transferred']}><EmptyRow columns={5} /></DataTable>
  </>
}

function Settings({ apiUrl, setApiUrl, interval, setInterval, onSaved, status, check, checking, checkMessage }) {
  const [error, setError] = useState('')
  function submit(event) {
    event.preventDefault()
    setError('')
    let parsed
    try { parsed = new URL(apiUrl) } catch { setError('Enter a valid URL, including http:// or https://.'); return }
    if (!['http:', 'https:'].includes(parsed.protocol)) { setError('Use an http:// or https:// URL.'); return }
    const normalized = parsed.toString().replace(/\/$/, '')
    localStorage.setItem('shardx-api-url', normalized)
    localStorage.setItem('shardx-refresh-interval', interval)
    api.defaults.baseURL = normalized
    setApiUrl(normalized)
    onSaved()
  }
  return <>
    <PageHeading title="Settings">Configure the API base URL and connection check interval.</PageHeading>
    <form className="settings-form" onSubmit={submit}>
      <label className="field-label" htmlFor="api-url">Backend API URL</label>
      <input id="api-url" className="text-input" type="url" required value={apiUrl} onChange={event => setApiUrl(event.target.value)} placeholder="http://localhost:8000" />
      <p className="field-help">The connection check requests this URL only. A response does not confirm that API routes exist.</p>
      <label className="field-label" htmlFor="refresh-interval">Connection check interval</label>
      <select id="refresh-interval" className="text-input select-input" value={interval} onChange={event => setInterval(event.target.value)}>
        <option value="0">Off</option><option value="10">10 seconds</option><option value="30">30 seconds</option><option value="60">1 minute</option>
      </select>
      <div className="form-actions"><button className="button button-primary" type="submit">Save settings</button><button className="button" type="button" onClick={check} disabled={checking}>{checking ? 'Checking…' : 'Test connection'}</button></div>
    </form>
    <div className="section-title"><h2>Connection</h2></div>
    <p className="status-line"><span className={`status-indicator ${status === 'URL responds' ? 'status-ok' : 'status-off'}`} />{status}</p>
    {checkMessage && <p className="page-note" role="status">{checkMessage}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="section-title"><h2>Backend capabilities</h2></div>
    <p className="page-note">No HTTP server or routes were found in the inspected backend. Live node, shard, query, data, replication, and migration features need an API implementation first.</p>
  </>
}

export default function App() {
  const location = useLocation()
  const [apiUrl, setApiUrl] = useState(initialUrl)
  const [interval, setIntervalValue] = useState(initialInterval)
  const [status, setStatus] = useState('Not checked')
  const [checkMessage, setCheckMessage] = useState('')
  const [checking, setChecking] = useState(false)

  async function check() {
    setChecking(true)
    setCheckMessage('')
    const result = await testApiBase(apiUrl)
    setStatus(result.reachable ? 'URL responds' : 'No response')
    setCheckMessage(result.message)
    setChecking(false)
  }

  useEffect(() => {
    let active = true
    testApiBase(apiUrl).then(result => {
      if (active) {
        setStatus(result.reachable ? 'URL responds' : 'No response')
        setCheckMessage(result.message)
      }
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const seconds = Number(interval)
    if (!seconds) return undefined
    const timer = window.setInterval(() => {
      testApiBase(apiUrl).then(result => {
        setStatus(result.reachable ? 'URL responds' : 'No response')
        setCheckMessage(result.message)
      })
    }, seconds * 1000)
    return () => window.clearInterval(timer)
  }, [apiUrl, interval])

  function saveSettings() {
    setIntervalValue(localStorage.getItem('shardx-refresh-interval') || '0')
    setCheckMessage('Settings saved in this browser.')
  }

  const currentTitle = titles[location.pathname] || 'Overview'
  return <div className="app-layout">
    <aside className="sidebar">
      <div className="app-name">ShardX</div>
      <nav aria-label="Main navigation">{pages.map(([label, path]) => <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>{label}</NavLink>)}</nav>
    </aside>
    <main className="main-content">
      <header className="topbar"><span className="topbar-app">ShardX</span><span className="topbar-separator">/</span><span>{currentTitle}</span><span className="topbar-status"><i className={`status-indicator ${status === 'URL responds' ? 'status-ok' : 'status-off'}`} />{status === 'URL responds' ? 'API URL responds' : status}</span></header>
      <section className="content"><Routes>
        <Route path="/" element={<Overview status={status} check={check} checking={checking} />} />
        <Route path="/nodes" element={<Nodes />} /><Route path="/shards" element={<Shards />} />
        <Route path="/query" element={<QueryConsole />} /><Route path="/data" element={<DataExplorer />} />
        <Route path="/replication" element={<Replication />} /><Route path="/migrations" element={<Migrations />} />
        <Route path="/settings" element={<Settings apiUrl={apiUrl} setApiUrl={setApiUrl} interval={interval} setInterval={setIntervalValue} onSaved={saveSettings} status={status} check={check} checking={checking} checkMessage={checkMessage} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></section>
    </main>
  </div>
}
