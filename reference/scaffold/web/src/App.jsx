import { useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const NAV_ITEMS = [
  { key: 'dashboard', label: 'Overview' },
  { key: 'capture', label: 'Capture' },
  { key: 'review', label: 'Review' },
  { key: 'system', label: 'System' },
];

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'x-actor-role': 'owner', ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.reason || body.error || `Request failed (${response.status})`);
  return body;
}

function getPage() {
  const requested = window.location.hash.replace('#/', '') || 'dashboard';
  return NAV_ITEMS.some((item) => item.key === requested) ? requested : 'dashboard';
}

function formatDate(timestamp) {
  if (!timestamp) return 'No timestamp';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(timestamp));
}

function EntryCard({ entry, onConfirm }) {
  return (
    <article className="entry-card" data-testid={`entry-${entry.id}`}>
      <div className="entry-card__topline">
        <span className="eyebrow">{entry.domain}</span>
        <span className={`status status--${entry.status}`}>{entry.status}</span>
      </div>
      <h3>{entry.content || entry.notes || 'Untitled capture'}</h3>
      <p className="entry-card__meta">{formatDate(entry.timestamp)} · {entry.source || 'manual'}</p>
      <div className="entry-card__facts">
        {entry.value !== null && entry.value !== undefined && <span><strong>Value</strong> {String(entry.value)}{entry.unit ? ` ${entry.unit}` : ''}</span>}
        {entry.energy !== null && entry.energy !== undefined && <span><strong>Energy</strong> {entry.energy}/10</span>}
        {entry.sentiment !== null && entry.sentiment !== undefined && <span><strong>Sentiment</strong> {entry.sentiment}</span>}
      </div>
      {entry.status === 'staged' && (
        <button className="button button--small" onClick={() => onConfirm(entry.id)} data-testid={`confirm-${entry.id}`}>
          Confirm entry
        </button>
      )}
    </article>
  );
}

function EmptyState({ title, text, action }) {
  return (
    <div className="empty-state">
      <span className="empty-state__mark" aria-hidden="true">○</span>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState(getPage);
  const [health, setHealth] = useState(null);
  const [entries, setEntries] = useState([]);
  const [domains, setDomains] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ content: '', domain: 'health', value: '', unit: '', energy: '', sentiment: '' });

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const [healthData, journalData, domainData, auditData] = await Promise.all([
        api('/health'),
        api('/journal'),
        api('/domains'),
        api('/audit'),
      ]);
      setHealth(healthData);
      setEntries(journalData.entries || []);
      setDomains(domainData.domains || []);
      setAudit(auditData.entries || []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const handleHashChange = () => setPage(getPage());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (nextPage) => {
    window.location.hash = `/${nextPage}`;
    setPage(nextPage);
  };

  const stats = useMemo(() => ({
    total: entries.length,
    staged: entries.filter((entry) => entry.status === 'staged').length,
    committed: entries.filter((entry) => entry.status === 'committed').length,
    activeDomains: domains.filter((domain) => domain.active).length,
  }), [entries, domains]);

  const submitCapture = async (event) => {
    event.preventDefault();
    if (!form.content.trim()) return;
    setSaving(true);
    setError('');
    const payload = {
      content: form.content.trim(),
      domain: form.domain,
      value: form.value === '' ? undefined : Number.isNaN(Number(form.value)) ? form.value : Number(form.value),
      unit: form.unit || undefined,
      energy: form.energy === '' ? undefined : Number(form.energy),
      sentiment: form.sentiment === '' ? undefined : Number(form.sentiment),
      source: 'manual',
      timestamp: new Date().toISOString(),
    };
    try {
      await api('/journal', { method: 'POST', body: JSON.stringify(payload) });
      setForm({ content: '', domain: form.domain, value: '', unit: '', energy: '', sentiment: '' });
      await refresh();
      navigate('review');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const confirmEntry = async (id) => {
    setError('');
    try {
      await api(`/journal/${id}/confirm`, { method: 'POST', body: '{}' });
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const pageContent = {
    dashboard: (
      <>
        <section className="hero-panel">
          <div>
            <span className="eyebrow">Personal operating system</span>
            <h1>Make your life<br /><em>legible.</em></h1>
            <p className="hero-panel__copy">A quiet command center for the signals you capture, the patterns you notice, and the decisions you want to remember.</p>
            <button className="button" onClick={() => navigate('capture')} data-testid="hero-capture">Capture a moment <span aria-hidden="true">→</span></button>
          </div>
          <div className="hero-panel__orbit" aria-hidden="true"><span>capture</span><span>extract</span><span>store</span><span>review</span><div className="orbit-core">COS</div></div>
        </section>
        <section className="metric-grid" aria-label="Life system metrics">
          <div className="metric-card"><span className="metric-card__label">All entries</span><strong>{stats.total}</strong><span className="metric-card__detail">across your system</span></div>
          <div className="metric-card metric-card--accent"><span className="metric-card__label">Awaiting review</span><strong>{stats.staged}</strong><span className="metric-card__detail">staged observations</span></div>
          <div className="metric-card"><span className="metric-card__label">Committed</span><strong>{stats.committed}</strong><span className="metric-card__detail">durable memories</span></div>
          <div className="metric-card"><span className="metric-card__label">Active domains</span><strong>{stats.activeDomains}</strong><span className="metric-card__detail">ways of seeing</span></div>
        </section>
        <section className="split-section">
          <div className="section-block"><div className="section-heading"><div><span className="eyebrow">Latest signals</span><h2>Recent entries</h2></div><button className="text-button" onClick={() => navigate('review')}>View all <span aria-hidden="true">↗</span></button></div>{entries.length ? entries.slice(-3).reverse().map((entry) => <EntryCard key={entry.id} entry={entry} onConfirm={confirmEntry} />) : <EmptyState title="Your system is quiet" text="Capture one small observation to give the week a starting point." action={<button className="button button--small" onClick={() => navigate('capture')}>Start capturing</button>} />}</div>
          <div className="section-block section-block--domains"><div className="section-heading"><div><span className="eyebrow">Your lens</span><h2>Domains</h2></div><button className="text-button" onClick={() => navigate('system')}>Manage <span aria-hidden="true">↗</span></button></div><div className="domain-list">{domains.map((domain) => <div className="domain-row" key={domain.name}><span className="domain-dot" style={{ background: domain.color }}></span><span>{domain.name}</span><span className="domain-count">{entries.filter((entry) => entry.domain === domain.name).length}</span></div>)}</div></div>
        </section>
      </>
    ),
    capture: (
      <section className="form-panel"><div className="section-heading"><div><span className="eyebrow">Capture layer</span><h1>What is present?</h1><p>Record an observation before it disappears. You can refine it during review.</p></div><div className="form-step">01 <span>/ 01</span></div></div><form onSubmit={submitCapture}><label htmlFor="content">Observation <span>required</span></label><textarea id="content" placeholder="I noticed..." value={form.content} onChange={(event) => setForm({ ...form, content: event.target.value })} rows="5" required /><div className="form-grid"><label htmlFor="domain">Domain<select id="domain" value={form.domain} onChange={(event) => setForm({ ...form, domain: event.target.value })}>{domains.filter((domain) => domain.active).map((domain) => <option key={domain.name} value={domain.name}>{domain.name}</option>)}<option value="uncategorized">uncategorized</option></select></label><label htmlFor="value">Value<input id="value" inputMode="decimal" placeholder="30" value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} /></label><label htmlFor="unit">Unit<input id="unit" placeholder="minutes" value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} /></label><label htmlFor="energy">Energy / 10<input id="energy" type="number" min="1" max="10" placeholder="7" value={form.energy} onChange={(event) => setForm({ ...form, energy: event.target.value })} /></label><label htmlFor="sentiment">Sentiment<input id="sentiment" type="number" min="-1" max="1" step="0.1" placeholder="0.5" value={form.sentiment} onChange={(event) => setForm({ ...form, sentiment: event.target.value })} /></label></div><div className="form-footer"><p>Saved to SQLite with a JSONL backup after submission.</p><button className="button" type="submit" disabled={saving} data-testid="capture-submit">{saving ? 'Saving...' : 'Stage observation →'}</button></div></form></section>
    ),
    review: (
      <section><div className="section-heading page-heading"><div><span className="eyebrow">Review layer</span><h1>See the pattern.</h1><p>Review is where raw observations become useful. Confirm what belongs in your durable record.</p></div><button className="button button--small" onClick={refresh}>Refresh</button></div>{entries.length ? <div className="review-list">{[...entries].reverse().map((entry) => <EntryCard key={entry.id} entry={entry} onConfirm={confirmEntry} />)}</div> : <EmptyState title="Nothing to review yet" text="Your first capture will appear here." action={<button className="button button--small" onClick={() => navigate('capture')}>Capture a moment</button>} />}</section>
    ),
    system: (
      <section><div className="section-heading page-heading"><div><span className="eyebrow">System layer</span><h1>How it holds.</h1><p>The operating contract is visible here: simple layers, explicit provenance, and durable history.</p></div></div><div className="architecture-grid">{['Capture', 'Extract', 'Store', 'Review'].map((layer, index) => <div className="architecture-card" key={layer}><span>0{index + 1}</span><h2>{layer}</h2><p>{['VoxLog · Telegram · Logseq', 'Gemini Flash categorization', 'SQLite · JSONL · GitHub', 'Streamlit · weekly markdown'][index]}</p>{index < 3 && <b aria-hidden="true">→</b>}</div>)}</div><div className="audit-panel"><div className="section-heading"><div><span className="eyebrow">Trace</span><h2>Recent audit events</h2></div><span className="status status--committed">{health?.status || 'offline'}</span></div>{audit.slice(-8).reverse().map((event, index) => <div className="audit-row" key={`${event.request_id}-${index}`}><span>{formatDate(event.timestamp)}</span><strong>{event.action}</strong><span className={`audit-result audit-result--${event.result}`}>{event.result}</span><span>{event.actor}</span></div>)}</div></section>
    ),
  }[page];

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">◒</span><span>Cognitive<br /><b>OS</b></span></div><div className="sidebar-intro"><span className="eyebrow">A system for noticing</span><p>Your data, your context, your cadence.</p></div><nav aria-label="Primary navigation">{NAV_ITEMS.map((item) => <button key={item.key} className={`nav-item ${page === item.key ? 'nav-item--active' : ''}`} onClick={() => navigate(item.key)} data-testid={`nav-${item.key}`}><span className="nav-index">0{NAV_ITEMS.indexOf(item) + 1}</span>{item.label}</button>)}</nav><div className="sidebar-footer"><div className="connection-indicator"><span className={`pulse ${health?.status === 'ok' ? 'pulse--on' : ''}`}></span><span>{health?.status === 'ok' ? 'Local system online' : 'Connecting...'}</span></div><small>v0.1 · local first</small></div></aside><main className="main-content"><header className="topbar"><div className="mobile-brand"><span className="brand-mark">◒</span> Cognitive <b>OS</b></div><div className="topbar-status"><span className="eyebrow">Wednesday · Week 35</span><span className="topbar-divider">/</span><span className="topbar-state">{loading ? 'Syncing' : 'In sync'}</span></div><button className="refresh-button" onClick={refresh} aria-label="Refresh data">↻</button></header>{error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}<div className="content-wrap">{pageContent}</div><footer className="page-footer"><span>Capture gently. Review honestly.</span><span>SQLite · JSONL · Git</span></footer></main></div>;
}
