// Independent reference page for oracle calibration, not a candidate implementation template.
// The runner prepends CASE; only the named defect varies in each mutant.
import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const newKey = () => (CASE === 'no-key' ? '' : crypto.randomUUID());
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function NewIncident({ onCreated }) {
  const [title, setTitle] = useState('');
  const [service, setService] = useState('');
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState('');
  const key = useRef(newKey());
  const failed = useRef(false);
  const edit = (set) => (event) => {
    // A payload the user edits after a failed send is a new intent with a new key.
    if (failed.current) {
      key.current = newKey();
      failed.current = false;
    }
    set(event.target.value);
  };

  async function submit(event) {
    event.preventDefault();
    setErrors({});
    setMessage('');
    for (let attempt = 1; attempt <= 5; attempt += 1) {
      if (CASE === 'fresh-key') key.current = newKey();
      const headers = { 'Content-Type': 'application/json' };
      if (key.current) headers['Idempotency-Key'] = key.current;
      const response = await fetch('/v1/incidents', {
        method: 'POST', headers, body: JSON.stringify({ title, service }),
      });
      if (response.status === 409 && response.headers.has('retry-after') && CASE !== 'stop-on-409') {
        await sleep(Number(response.headers.get('retry-after')) * 1000);
        continue;
      }
      if (response.ok) {
        onCreated(await response.json());
        return;
      }
      failed.current = true;
      const problem = await response.json().catch(() => ({}));
      if (response.status === 409) {
        setMessage('The create is still running; check the list before trying again.');
        return;
      }
      const byField = {};
      for (const error of problem.errors ?? []) byField[String(error.loc?.at(-1))] = error.msg;
      setErrors(byField);
      setMessage(problem.title ?? `HTTP ${response.status}`);
      if (CASE === 'cleared-input') {
        setTitle('');
        setService('');
      }
      return;
    }
  }

  const summary = CASE === 'summary-errors' || CASE === 'reference-describedby';
  const beside = (field) => !summary && errors[field] &&
    <span id={`${field}-error`}>{errors[field]}</span>;
  const described = (field) =>
    CASE === 'reference-describedby' && errors[field] ? `summary-${field}` : beside(field) ? `${field}-error` : undefined;

  return (
    <form aria-label="New incident" onSubmit={submit}>
      {message && <p role="alert">{message}</p>}
      {summary && Object.keys(errors).length > 0 && <ul>
        {Object.entries(errors).map(([field, text]) => <li key={field} id={`summary-${field}`}>{text}</li>)}
      </ul>}
      <div>
        <label htmlFor="new-title">Title</label>
        <input id="new-title" value={title} onChange={edit(setTitle)} aria-describedby={described('title')} />
        {beside('title')}
      </div>
      <div>
        <label htmlFor="new-service">Service</label>
        {CASE === 'reference-service-select' ? (
          <select id="new-service" value={service} onChange={edit(setService)} aria-describedby={described('service')}>
            <option value="">Choose a service</option><option value="checkout">checkout</option>
            <option value="search">search</option>
          </select>
        ) : (
          <input id="new-service" value={service} onChange={edit(setService)} aria-describedby={described('service')} />
        )}
        {beside('service')}
      </div>
      <button type="submit">Create incident</button>
    </form>
  );
}

export default function App() {
  const [params, setParams] = useSearchParams();
  const wanted = params.get('status') ?? '';
  const [rows, setRows] = useState([]);
  const [state, setState] = useState('loading');
  const [creating, setCreating] = useState(CASE === 'reference-open-form');
  const serverStatus = CASE === 'client-filter' ? '' : wanted;
  useEffect(() => {
    let active = true;
    setState('loading');
    fetch(`/v1/incidents${serverStatus ? `?status=${serverStatus}` : ''}`)
      .then((response) => {
        if (!response.ok) throw new Error('request failed');
        return response.json();
      })
      .then((page) => {
        if (active) {
          setRows(page.data);
          setState(page.data.length ? 'loaded' : 'empty');
        }
      })
      .catch(() => { if (active) setState('error'); });
    return () => { active = false; };
  }, [serverStatus]);
  const displayed = rows.filter((row) => !wanted || row.status === wanted);

  return (
    <main>
      <h1>Incidents</h1>
      <label>
        Status
        <select value={wanted} onChange={(event) =>
          setParams(event.target.value ? { status: event.target.value } : {})}>
          <option value="">All</option><option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </label>
      {CASE !== 'reference-open-form' &&
        <button type="button" onClick={() => setCreating(true)}>New incident</button>}
      {creating && <NewIncident onCreated={(incident) => {
        setRows((previous) => [incident, ...previous]);
        setCreating(CASE === 'reference-open-form');
      }} />}
      {state === 'loading' && <p role="status">Loading incidents</p>}
      {state === 'error' && <p role="alert">Incidents could not be loaded</p>}
      {state === 'empty' && <p>No incidents</p>}
      {state === 'loaded' && <table>
        <caption>Incidents</caption>
        <thead><tr><th>ID</th><th>Status</th><th>Title</th><th>Service</th><th>Created</th></tr></thead>
        <tbody>{displayed.map((row) => <tr key={row.id}>
          <td>{row.id}</td><td>{row.status}</td>
          {CASE === 'html-title' ? <td dangerouslySetInnerHTML={{ __html: row.title }} /> : <td>{row.title}</td>}
          <td>{row.service}</td><td>{row.created_at}</td>
        </tr>)}</tbody>
      </table>}
    </main>
  );
}
