// Independent reference page for oracle calibration, not a candidate implementation template.
// The runner prepends CASE, LOADING, and FILTER; only the named defect varies in each mutant.
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export default function App() {
  const [params, setParams] = useSearchParams();
  const wanted = params.get('status') ?? 'all';
  const [selectedHere, setSelectedHere] = useState(false);
  const [rows, setRows] = useState([]);
  const [state, setState] = useState('loading');
  const serverStatus = FILTER === 'server' ? wanted : 'all';
  useEffect(() => {
    let active = true;
    setState('loading');
    fetch(`/api/incidents${serverStatus === 'all' ? '' : `?status=${serverStatus}`}`)
      .then((response) => {
        if (!response.ok) throw new Error('request failed');
        return response.json();
      })
      .then((data) => {
        if (active) {
          setRows(data);
          setState(data.length ? 'loaded' : 'empty');
        }
      })
      .catch(() => { if (active) setState('error'); });
    return () => { active = false; };
  }, [serverStatus]);

  const hidden = (name) => CASE === `hidden-${name}` ? { display: 'none' } : undefined;
  const suppress = (name) => CASE === `permanent-${name}` || CASE === 'outside-main' ||
    CASE === 'remounted-permanent' || CASE === `hidden-child-${name}`;
  const loading = state === 'loading';
  const loadingMessage = loading || CASE === 'permanent-loading' || CASE === 'remounted-permanent';
  const shouldFilter = CASE !== 'url-only' && (CASE !== 'ignore-deep-link' || selectedHere);
  const matches = (row) => !shouldFilter || wanted === 'all' || row.status === wanted;
  const displayed = FILTER === 'hidden-rows' ? rows : rows.filter(matches);

  return (
    <div>
      <nav aria-label="Primary">
        <a href="/incidents">Incidents</a>
        {CASE === 'outside-main' && <>
          <p>Loading monitoring data</p><p role="alert">Monitoring failed</p><p>No results</p>
        </>}
      </nav>
      <main key={CASE === 'remounted-permanent' ? state : 'page'}>
        <h1>Incidents</h1>
        {/* A correct incidents page may coexist with unrelated permanent status content. */}
        <aside aria-label="Connection"><p role="status">Connected to monitoring</p></aside>
        {['permanent-error', 'remounted-permanent'].includes(CASE) &&
          <p role="alert">Monitoring unavailable</p>}
        {['permanent-empty', 'remounted-permanent'].includes(CASE) &&
          <p>No results in the monitoring sidebar</p>}
        <label>
          Status
          <select value={wanted} onChange={(event) => {
            setSelectedHere(true);
            setParams(event.target.value === 'all' ? {} : { status: event.target.value });
          }}>
            <option value="all">All</option><option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <section aria-label="Incident results"
          aria-busy={LOADING === 'busy' ? loading : undefined}>
          {CASE === 'hidden-child-loading' && <p role="status">
            <span style={{ display: 'none' }}>{loading ? 'Loading incidents' : 'Incidents ready'}</span>
          </p>}
          {CASE === 'hidden-child-error' && <p role="alert">
            <span style={{ display: 'none' }}>{state === 'error' ? 'Incident request failed' : ''}</span>
          </p>}
          {CASE !== 'outside-main' && loadingMessage && LOADING === 'text' &&
            <p style={hidden('loading')}>Loading incidents</p>}
          {LOADING === 'status' &&
            <p role="status">{loading ? 'Retrieving incident records' : `${rows.length} incident records`}</p>}
          {LOADING === 'named-role' && <p role="status"
            aria-label={loading ? 'Retrieving incident records' : 'Incidents ready'}>↻</p>}
          {LOADING === 'labelledby-role' && <>
            <span id="request-label" hidden>{loading ? 'Retrieving incident records' : 'Incidents ready'}</span>
            <p role="status" aria-labelledby="request-label">↻</p>
          </>}
          {LOADING === 'progressbar' && loading &&
            <div role="progressbar" aria-label="Incident request">Working</div>}
          {LOADING === 'label' && loading && <span aria-label="Loading incidents">↻</span>}
          {LOADING === 'busy' && <p>Incident results follow</p>}
          {CASE === 'same-node' ? (
            <p role={state === 'error' ? 'alert' : 'status'}>
              {state === 'error' ? 'Incident request failed' :
                state === 'empty' ? 'No incidents' : loading ? 'Loading incidents' : 'Incidents ready'}
            </p>
          ) : <>
            {!suppress('error') && state === 'error' && <>
              {LOADING === 'named-role' ? <p role="alert" aria-label="Incident request failed">⚠</p> :
                LOADING === 'labelledby-role' ? <>
                  <span id="error-label" hidden>Incident request failed</span>
                  <p role="alert" aria-labelledby="error-label">⚠</p>
                </> : <p role="alert" style={hidden('error')}>Incident request failed</p>}
            </>}
            {!suppress('empty') && state === 'empty' &&
              <p style={hidden('empty')}>No incidents</p>}
          </>}
          {state === 'loaded' && <table>
            <caption>Incident records</caption>
            <thead><tr><th>ID</th><th>Status</th><th>Title</th><th>Service</th><th>Created</th></tr></thead>
            <tbody>{displayed.map((row) => <tr key={row.id}
              style={FILTER === 'hidden-rows' && !matches(row) ? { display: 'none' } : undefined}>
              <td>{row.id}</td><td>{row.status}</td><td>{row.title}</td>
              <td>{row.service}</td><td>{row.created_at}</td>
            </tr>)}</tbody>
          </table>}
        </section>
      </main>
    </div>
  );
}
