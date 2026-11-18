import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { api, clusterService, testApiBase } from './services/api.js'

const pages = [
  ['Overview', '/'],
  ['Nodes', '/nodes'],
  ['Shards', '/shards'],
  ['Query Console', '/query'],
  ['Data Explorer', '/data'],
  ['Bulk Import', '/bulk-import'],
  ['Replication', '/replication'],
  ['Migrations', '/migrations'],
  ['Settings', '/settings']
]
const titles = Object.fromEntries(pages)
const initialUrl = localStorage.getItem('shardx-api-url') || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const initialInterval = localStorage.getItem('shardx-refresh-interval') || '0'

function PageHeading({ title, children }) { return <div className="page-heading"><h1>{title}</h1>{children && <p>{children}</p>}</div> }
function EmptyRow({ columns, children = 'No data available.' }) { return <tr><td className="empty-cell" colSpan={columns}>{children}</td></tr> }
function DataTable({ headers, children }) { return <div className="table-wrap"><table><thead><tr>{headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div> }
function useLoad(loader, deps = []) {
  const [data, setData] = useState(null); const [error, setError] = useState(''); const [refresh, setRefresh] = useState(0)
  useEffect(() => { let live = true; loader().then(value => { if (live) { setData(value); setError('') } }).catch(e => { if (live) setError(e.response?.data?.detail || e.message) }); return () => { live = false } }, [...deps, refresh])
  return { data, error, reload: () => setRefresh(v => v + 1) }
}
function ErrorNote({ error }) { return error ? <p className="form-error" role="alert">{error}</p> : null }
function Overview({ check, checking }) {
  const { data, error, reload } = useLoad(clusterService.getDashboard)
  return <><PageHeading title="Overview">Live cluster status and database statistics.</PageHeading><ErrorNote error={error} />
    <div className="stats-table"><table><tbody>{[['Total shards', data?.total_shards ?? 'Loading…'], ['Active nodes', data?.active_nodes ?? 'Loading…'], ['Total records', data?.total_records ?? 'Loading…'], ['Database connection', data ? (data.database_connected ? 'Connected' : 'Unavailable') : 'Checking…']].map(([label, value]) => <tr key={label}><th>{label}</th><td>{value}</td></tr>)}</tbody></table></div>
    <div className="section-title"><h2>Nodes</h2></div><DataTable headers={['Node ID', 'Host', 'Status', 'Assigned shards']}>{data?.nodes?.map(n => <tr key={n.node_id}><td>{n.node_id}</td><td>{n.host}</td><td>{n.status}</td><td>{n.assigned_shards}</td></tr>) || <EmptyRow columns={4} />}</DataTable>
    <div className="section-title"><h2>Shard distribution</h2></div><DataTable headers={['Shard ID', 'Assigned node', 'Records', 'Status']}>{data?.shards?.map(s => <tr key={s.shard_id}><td>{s.shard_id}</td><td>{s.node}</td><td>{s.records}</td><td>{s.status}</td></tr>) || <EmptyRow columns={4} />}</DataTable>
    <div className="section-title"><h2>Recent operations</h2></div><DataTable headers={['Time', 'Operation', 'Status']}>{data?.recent_operations?.length ? data.recent_operations.map((op,i)=><tr key={`${op.operation}-${i}`}><td>{new Date(op.occurred_at).toLocaleString()}</td><td>{op.operation}</td><td>{op.status}</td></tr>) : <EmptyRow columns={3}>No operations recorded yet.</EmptyRow>}</DataTable>
    <button className="button" type="button" onClick={() => { reload(); check() }} disabled={checking}>{checking ? 'Checking…' : 'Refresh status'}</button></>
}
function Nodes() {
  const { data, error, reload } = useLoad(clusterService.getNodes)
  async function toggle(n) { try { await clusterService.setNodeStatus(n.node_name, n.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'); reload() } catch (e) { window.alert(e.response?.data?.detail || e.message) } }
  return <><PageHeading title="Nodes">Shard node inventory and live MySQL reachability.</PageHeading><ErrorNote error={error} /><DataTable headers={['Node ID', 'Host', 'Status', 'Assigned shards', 'Action']}>{data?.map(n => <tr key={n.node_id}><td>{n.node_name}</td><td>{n.host}:{n.port}</td><td>{n.status}</td><td>{n.assigned_shards}</td><td><button className="button" onClick={() => toggle(n)}>{n.status === 'ACTIVE' ? 'Disable' : 'Enable'}</button></td></tr>) || <EmptyRow columns={5} />}</DataTable></>
}
function Shards() {
  const { data, error } = useLoad(clusterService.getShards)
  return <><PageHeading title="Shards">Primary student records are distributed by student ID across available MySQL shards.</PageHeading><ErrorNote error={error} /><DataTable headers={['Shard ID', 'Assigned node', 'Records', 'Status']}>{data?.map(s => <tr key={s.shard_id}><td>{s.shard_id}</td><td>{s.node}</td><td>{s.records}</td><td>{s.status}</td></tr>) || <EmptyRow columns={4} />}</DataTable><div className="section-title"><h2>Consistent hashing</h2></div><p className="page-note">The active strategy is shard-key modulo hashing. Student ID determines the primary shard; reads without a shard key scan reachable shards.</p></>
}
function QueryConsole() {
  const [sql, setSql] = useState('SELECT student_id, name, email, department FROM students ORDER BY student_id')
  const [result, setResult] = useState(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function execute() { setBusy(true); setError(''); try { setResult(await clusterService.query(sql)) } catch (e) { setError(e.response?.data?.detail || e.message) } finally { setBusy(false) } }
  return <><PageHeading title="Query Console">Run a read-only SELECT against student records across the shards.</PageHeading><label className="field-label" htmlFor="sql">SQL query</label><textarea id="sql" className="sql-editor" spellCheck="false" value={sql} onChange={e => setSql(e.target.value)} placeholder="Enter SQL query"/><div className="form-actions"><button className="button button-primary" onClick={execute} disabled={busy}>{busy ? 'Executing…' : 'Execute'}</button><button className="button" onClick={() => { setSql(''); setResult(null) }}>Clear</button></div><ErrorNote error={error}/><div className="section-title"><h2>Results {result ? `(${result.row_count})` : ''}</h2></div><DataTable headers={result?.columns?.length ? result.columns : ['Results']}>{result?.rows?.length ? result.rows.map((row, i) => <tr key={i}>{result.columns.map(c => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>) : <EmptyRow columns={result?.columns?.length || 1}>No query results.</EmptyRow>}</DataTable></>
}
function DataExplorer() {
  const { data, error, reload } = useLoad(() => clusterService.getStudents({ limit: 500 }))
  const [form, setForm] = useState({ student_id: '', name: '', email: '', department: '' }); const [notice, setNotice] = useState('')
  async function save(e) { e.preventDefault(); setNotice(''); try { const payload = { ...form, student_id: Number(form.student_id) }; await clusterService.createStudent(payload); setNotice(`Student created on the shard assigned to ID ${payload.student_id}.`); setForm({ student_id: '', name: '', email: '', department: '' }); reload() } catch (err) { setNotice(err.response?.data?.detail || err.message) } }
  async function edit(s) { const name = window.prompt('Name', s.name); if (name === null) return; const email = window.prompt('Email', s.email); if (email === null) return; const department = window.prompt('Department', s.department); if (department === null) return; try { await clusterService.updateStudent(s.student_id, { student_id: s.student_id, name, email, department }); reload(); setNotice(`Student ${s.student_id} updated.`) } catch (err) { setNotice(err.response?.data?.detail || err.message) } }
  async function remove(id) { if (!window.confirm(`Delete student ${id}?`)) return; try { await clusterService.deleteStudent(id); reload(); setNotice(`Student ${id} deleted.`) } catch (err) { setNotice(err.response?.data?.detail || err.message) } }
  return <><PageHeading title="Data Explorer">Browse and manage student records stored in the shard databases.</PageHeading><ErrorNote error={error}/><div className="section-title"><h2>Student records</h2></div><DataTable headers={['ID', 'Name', 'Email', 'Department', 'Shard', 'Action']}>{data?.items?.map(s => <tr key={s.student_id}><td>{s.student_id}</td><td>{s.name}</td><td>{s.email}</td><td>{s.department}</td><td>{s.shard}</td><td><button className="button" onClick={() => edit(s)}>Edit</button> <button className="button" onClick={() => remove(s.student_id)}>Delete</button></td></tr>) || <EmptyRow columns={6}/>}</DataTable><p className="page-note">{data ? `${data.total} record(s)` : 'Loading records…'}</p><div className="section-title"><h2>Add student</h2></div><form className="settings-form" onSubmit={save}>{[['student_id','Student ID','number'],['name','Name','text'],['email','Email','email'],['department','Department','text']].map(([key,label,type])=><label key={key} className="field-label" htmlFor={`student-${key}`}>{label}<input required min={type==='number' ? 1 : undefined} type={type} className="text-input" id={`student-${key}`} value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})}/></label>)}<button className="button button-primary" type="submit">Add student</button></form>{notice && <p className="page-note" role="status">{notice}</p>}</>
}

function BulkImport() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function selectFile(event) {
    const selected = event.target.files?.[0] || null
    setFile(selected)
    setPreview(null)
    setResult(null)
    setError('')
  }

  async function handlePreview() {
    if (!file) {
      setError('Please select a CSV file first.')
      return
    }

    setBusy(true)
    setError('')
    setResult(null)

    try {
      const data = await clusterService.bulkPreview(file)
      setPreview(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'CSV preview failed.')
    } finally {
      setBusy(false)
    }
  }

  async function handleImport() {
    if (!file || !preview) return

    setBusy(true)
    setError('')

    try {
      const data = await clusterService.bulkImport(file)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'CSV import failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeading title="Bulk Import">
        Upload a CSV file to validate student records and distribute them across the four MySQL shards.
      </PageHeading>

      <div className="settings-form">
        <label className="field-label" htmlFor="csv-file">
          Select CSV file
        </label>

        <input
          id="csv-file"
          className="text-input"
          type="file"
          accept=".csv,text/csv"
          onChange={selectFile}
        />

        <p className="field-help">
          Required columns: student_id, name, email, department. Maximum file size: 10 MB.
        </p>

        {file && (
          <p className="page-note">
            Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </p>
        )}

        <div className="form-actions">
          <button
            className="button button-primary"
            type="button"
            onClick={handlePreview}
            disabled={!file || busy}
          >
            {busy ? 'Please wait...' : 'Preview CSV'}
          </button>

          <button
            className="button"
            type="button"
            onClick={() => {
              setFile(null)
              setPreview(null)
              setResult(null)
              setError('')
              document.getElementById('csv-file').value = ''
            }}
            disabled={busy}
          >
            Clear
          </button>
        </div>
      </div>

      <ErrorNote error={error} />

      {preview && (
        <>
          <div className="section-title">
            <h2>CSV Validation Summary</h2>
          </div>

          <div className="stats-table">
            <table>
              <tbody>
                <tr>
                  <th>Valid records</th>
                  <td>{preview.total_valid}</td>
                </tr>
                <tr>
                  <th>Invalid records</th>
                  <td>{preview.total_invalid}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="section-title">
            <h2>Shard Distribution</h2>
          </div>

          <DataTable headers={['Shard', 'Records to process']}>
            {Object.entries(preview.shard_distribution || {}).map(([shard, count]) => (
              <tr key={shard}>
                <td>{shard}</td>
                <td>{count}</td>
              </tr>
            ))}
          </DataTable>

          <div className="section-title">
            <h2>Student Preview</h2>
          </div>

          <DataTable headers={['Student ID', 'Name', 'Email', 'Department']}>
            {preview.preview?.length
              ? preview.preview.map(student => (
                  <tr key={student.student_id}>
                    <td>{student.student_id}</td>
                    <td>{student.name}</td>
                    <td>{student.email}</td>
                    <td>{student.department}</td>
                  </tr>
                ))
              : <EmptyRow columns={4}>No valid records to preview.</EmptyRow>}
          </DataTable>

          {preview.errors?.length > 0 && (
            <>
              <div className="section-title">
                <h2>Validation Errors</h2>
              </div>

              <DataTable headers={['CSV Row', 'Error']}>
                {preview.errors.map((item, index) => (
                  <tr key={index}>
                    <td>{item.row}</td>
                    <td>{item.error}</td>
                  </tr>
                ))}
              </DataTable>
            </>
          )}

          <div className="form-actions">
            <button
              className="button button-primary"
              type="button"
              onClick={handleImport}
              disabled={busy || preview.total_valid === 0}
            >
              {busy ? 'Importing...' : 'Import Valid Records'}
            </button>
          </div>
        </>
      )}

      {result && (
        <>
          <div className="section-title">
            <h2>Import Results</h2>
          </div>

          <div className="stats-table">
            <table>
              <tbody>
                <tr>
                  <th>Inserted</th>
                  <td>{result.inserted}</td>
                </tr>
                <tr>
                  <th>Skipped duplicates</th>
                  <td>{result.skipped}</td>
                </tr>
                <tr>
                  <th>Invalid records</th>
                  <td>{result.invalid}</td>
                </tr>
                <tr>
                  <th>Failed shards</th>
                  <td>{result.failed_shards?.length || 0}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="section-title">
            <h2>Shard Import Details</h2>
          </div>

          <DataTable headers={['Shard', 'Inserted', 'Skipped', 'Status']}>
            {Object.entries(result.shard_results || {}).map(([shard, details]) => (
              <tr key={shard}>
                <td>{shard}</td>
                <td>{details.inserted}</td>
                <td>{details.skipped}</td>
                <td>{details.status}</td>
              </tr>
            ))}
          </DataTable>

          {result.errors?.length > 0 && (
            <>
              <div className="section-title">
                <h2>Import Errors</h2>
              </div>
              <DataTable headers={['Error']}>
                {result.errors.map((item, index) => (
                  <tr key={index}>
                    <td>{typeof item === 'string' ? item : JSON.stringify(item)}</td>
                  </tr>
                ))}
              </DataTable>
            </>
          )}

          <p className="page-note" role="status">
            {result.message}
          </p>
        </>
      )}
    </>
  )
}

function Replication() { const { data, error } = useLoad(clusterService.getReplication); return <><PageHeading title="Replication">Replication configuration read from the cluster metadata database.</PageHeading><ErrorNote error={error}/><DataTable headers={['Primary node', 'Replica node', 'Status', 'Last synchronized']}><EmptyRow columns={4}>{data?.enabled ? 'Replication is enabled; no replication event history is recorded.' : 'Replication is disabled. Horizontal shard placement stores each primary record on its assigned shard.'}</EmptyRow></DataTable></> }
function Migrations() { const { data, error } = useLoad(clusterService.getMigrations); return <><PageHeading title="Migrations">Persisted shard rebalancing history.</PageHeading><ErrorNote error={error}/><DataTable headers={['Migration ID', 'Strategy', 'Status', 'Records transferred']}>{data?.map(m=><tr key={m.job_id}><td>{m.job_id}</td><td>{m.strategy}</td><td>{m.status}</td><td>{m.records_migrated} / {m.records_to_move}</td></tr>) || <EmptyRow columns={4}/>}</DataTable></> }
function Settings({ apiUrl, setApiUrl, interval, setInterval, onSaved, status, check, checking, checkMessage }) {
  const [error, setError] = useState('')
  function submit(event) { event.preventDefault(); setError(''); let parsed; try { parsed = new URL(apiUrl) } catch { setError('Enter a valid URL, including http:// or https://.'); return } if (!['http:', 'https:'].includes(parsed.protocol)) { setError('Use an http:// or https:// URL.'); return } const normalized = parsed.toString().replace(/\/$/, ''); localStorage.setItem('shardx-api-url', normalized); localStorage.setItem('shardx-refresh-interval', interval); api.defaults.baseURL = normalized; setApiUrl(normalized); onSaved() }
  return <><PageHeading title="Settings">Configure the backend API URL and connection check interval.</PageHeading><form className="settings-form" onSubmit={submit}><label className="field-label" htmlFor="api-url">Backend API URL</label><input id="api-url" className="text-input" type="url" required value={apiUrl} onChange={e=>setApiUrl(e.target.value)} placeholder="http://localhost:8000"/><p className="field-help">The connection check verifies the API and its MySQL connections.</p><label className="field-label" htmlFor="refresh-interval">Connection check interval</label><select id="refresh-interval" className="text-input select-input" value={interval} onChange={e=>setInterval(e.target.value)}><option value="0">Off</option><option value="10">10 seconds</option><option value="30">30 seconds</option><option value="60">1 minute</option></select><div className="form-actions"><button className="button button-primary" type="submit">Save settings</button><button className="button" type="button" onClick={check} disabled={checking}>{checking ? 'Checking…' : 'Test connection'}</button></div></form><div className="section-title"><h2>Connection</h2></div><p className="status-line"><span className={`status-indicator ${status === 'Connected' ? 'status-ok' : 'status-off'}`}/>{status}</p>{checkMessage && <p className="page-note" role="status">{checkMessage}</p>}{error && <p className="form-error" role="alert">{error}</p>}<div className="section-title"><h2>Backend capabilities</h2></div><p className="page-note">Live shard inventory, student records, read-only query execution, node status, and migration history use the ShardX API.</p></>
}
export default function App() {
  const location = useLocation(); const [apiUrl,setApiUrl] = useState(initialUrl); const [interval,setIntervalValue] = useState(initialInterval); const [status,setStatus] = useState('Not checked'); const [checkMessage,setCheckMessage] = useState(''); const [checking,setChecking] = useState(false)
  async function check() { setChecking(true); const result = await testApiBase(apiUrl); setStatus(result.reachable ? 'Connected' : 'Unavailable'); setCheckMessage(result.message); setChecking(false) }
  useEffect(() => { check() }, [])
  useEffect(() => { const seconds = Number(interval); if (!seconds) return undefined; const timer = window.setInterval(check, seconds*1000); return () => window.clearInterval(timer) }, [apiUrl,interval])
  function saveSettings() { setIntervalValue(localStorage.getItem('shardx-refresh-interval') || '0'); setCheckMessage('Settings saved in this browser.') }
  const currentTitle = titles[location.pathname] || 'Overview'
  return <div className="app-layout"><aside className="sidebar"><div className="app-name">ShardX</div><nav aria-label="Main navigation">{pages.map(([label,path])=><NavLink key={path} to={path} end={path==='/'} className={({isActive})=>`nav-link${isActive?' active':''}`}>{label}</NavLink>)}</nav></aside><main className="main-content"><header className="topbar"><span className="topbar-app">ShardX</span><span className="topbar-separator">/</span><span>{currentTitle}</span><span className="topbar-status"><i className={`status-indicator ${status==='Connected'?'status-ok':'status-off'}`}/>{status}</span></header><section className="content"><Routes><Route path="/" element={<Overview check={check} checking={checking}/>}/><Route path="/nodes" element={<Nodes/>}/><Route path="/shards" element={<Shards/>}/><Route path="/query" element={<QueryConsole/>}/><Route path="/data" element={<DataExplorer/>}/><Route path="/bulk-import" element={<BulkImport/>}/><Route path="/replication" element={<Replication/>}/><Route path="/migrations" element={<Migrations/>}/><Route path="/settings" element={<Settings apiUrl={apiUrl} setApiUrl={setApiUrl} interval={interval} setInterval={setIntervalValue} onSaved={saveSettings} status={status} check={check} checking={checking} checkMessage={checkMessage}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></section></main></div>
}
