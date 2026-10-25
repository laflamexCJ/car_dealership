import { useEffect, useMemo, useRef, useState } from 'react';
import { createApi } from './api.js';

const SESSION_KEY = 'motorhouse-session';
const emptyFilters = { q: '', category: '', min_price: '', max_price: '' };
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value));

function readSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    return typeof session?.access_token === 'string' && session?.user?.email ? session : null;
  } catch { return null; }
}

function Icon({ name, ...props }) {
  const paths = {
    car: <><path d="m5 10 2-5h10l2 5M3 10h18v8H3zM6 18v2m12-2v2M6 14h2m8 0h2" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    search: <><circle cx="10" cy="10" r="6" /><path d="m15 15 6 6" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    logout: <path d="M10 4H4v16h6m4-4 4-4-4-4m-6 4h10" />,
  };
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.car}</svg>;
}

function Brand() {
  return <div className="brand"><span className="brand-mark"><Icon name="car" /></span><span>motorhouse<span className="brand-dot">.</span></span></div>;
}

function CarArtwork() {
  return <svg className="car-art" viewBox="0 0 360 130" fill="none" aria-hidden="true"><ellipse cx="182" cy="111" rx="139" ry="8" fill="currentColor" opacity=".08" /><path d="M38 90 49 65l45-8 40-35h90l46 37 47 10 8 29H38z" fill="currentColor" opacity=".12" /><path d="m98 57 40-30h37v30zm88-30h35l36 30h-71z" fill="currentColor" opacity=".32" /><path d="M38 90 49 65l45-8 40-35h90l46 37 47 10 8 29H38z" stroke="currentColor" strokeWidth="2" /><path d="M178 63v32m13-26h13M47 75h27m218 0h22" stroke="currentColor" strokeWidth="3" /><circle cx="89" cy="97" r="20" fill="var(--car-bg, #edf1ed)" stroke="currentColor" strokeWidth="4" /><circle cx="89" cy="97" r="9" stroke="currentColor" strokeWidth="3" /><circle cx="274" cy="97" r="20" fill="var(--car-bg, #edf1ed)" stroke="currentColor" strokeWidth="4" /><circle cx="274" cy="97" r="9" stroke="currentColor" strokeWidth="3" /></svg>;
}

function Notice({ children, error = false }) {
  return children ? <div className={`notice ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>{children}</div> : null;
}

function Auth({ onLogin, message }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const api = useMemo(() => createApi(), []);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(true); setError(''); setSuccess('');
    try {
      if (register) {
        await api('/auth/register', { method: 'POST', body: data });
        setRegister(false);
        setSuccess('Account created. Sign in to explore the inventory.');
        form.elements.password.value = '';
      } else {
        onLogin(await api('/auth/login', { method: 'POST', body: data }));
      }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="auth-layout">
    <section className="auth-story"><Brand /><div><span className="eyebrow light">THE NEXT CHAPTER IN YOUR GARAGE</span><h1>Great inventory.<br />Even better journeys.</h1><p>A clear view of every vehicle. One place to keep your dealership moving.</p><CarArtwork /></div><span className="auth-footer">Thoughtfully built for the road ahead.</span></section>
    <main className="auth-main"><div className="auth-box"><span className="eyebrow">WELCOME TO MOTORHOUSE</span><h2>{register ? 'Start your journey.' : 'Welcome back.'}</h2><p className="muted">{register ? 'Create your account to browse and manage vehicles.' : 'Sign in to your dealership workspace.'}</p>
      <Notice error>{error || message}</Notice><Notice>{success}</Notice>
      <form onSubmit={submit} className="form-stack"><fieldset disabled={busy}>
        <label>Email address<input name="email" type="email" autoComplete="email" placeholder="you@example.com" maxLength="254" required /></label>
        <label>Password<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} placeholder={register ? 'At least 8 characters' : 'Your password'} minLength={register ? 8 : 1} maxLength="128" required /></label>
        <button className="button primary full" type="submit">{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}<Icon name="arrow" /></button>
      </fieldset></form>
      <p className="auth-switch">{register ? 'Already have an account?' : 'New to Motorhouse?'} <button disabled={busy} onClick={() => { setRegister(!register); setError(''); setSuccess(''); }}>{register ? 'Sign in' : 'Create an account'}</button></p>
    </div></main>
  </div>;
}

function VehicleDialog({ modal, close, api, onSaved }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { type, vehicle } = modal;
  useEffect(() => { ref.current.showModal(); }, []);
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true);
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (type === 'delete') {
        await api(`/vehicles/${vehicle.id}`, { method: 'DELETE' });
      } else if (type === 'restock') {
        await api(`/vehicles/${vehicle.id}/restock`, { method: 'POST', body: { quantity: Number(fields.quantity) } });
      } else {
        const body = { make: fields.make.trim(), model: fields.model.trim(), category: fields.category.trim(), price: fields.price };
        if (type === 'add') body.quantity = Number(fields.quantity);
        await api(type === 'add' ? '/vehicles' : `/vehicles/${vehicle.id}`, { method: type === 'add' ? 'POST' : 'PUT', body });
      }
      onSaved({ add: 'Vehicle added to inventory.', edit: 'Vehicle details updated.', restock: 'Stock replenished.', delete: 'Vehicle deleted.' }[type]);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  const title = { add: 'Add a vehicle', edit: 'Edit vehicle', restock: 'Restock vehicle', delete: 'Delete vehicle?' }[type];
  return <dialog ref={ref} className="modal" onCancel={event => { event.preventDefault(); if (!busy) close(); }} aria-labelledby="dialog-title">
    <div className="modal-heading"><div><span className="eyebrow">INVENTORY MANAGEMENT</span><h2 id="dialog-title">{title}</h2></div><button className="close" aria-label="Close dialog" disabled={busy} onClick={close}>×</button></div>
    <Notice error>{error}</Notice>
    <form onSubmit={submit}><fieldset disabled={busy}>
      {(type === 'add' || type === 'edit') ? <><div className="form-grid">
        <label>Make<input name="make" defaultValue={vehicle?.make || ''} maxLength="100" required autoFocus /></label>
        <label>Model<input name="model" defaultValue={vehicle?.model || ''} maxLength="100" required /></label>
        <label>Category<input name="category" defaultValue={vehicle?.category || ''} placeholder="e.g. Sedan, SUV, Electric" maxLength="100" required /></label>
        <label>Price (USD)<input name="price" type="number" min="0" max="9999999999.99" step="0.01" defaultValue={vehicle?.price ?? ''} required /></label>
        {type === 'add' && <label>Initial quantity<input name="quantity" type="number" min="0" max="2147483647" step="1" defaultValue="1" required /></label>}
      </div>{type === 'edit' && <p className="muted small">Stock is managed separately through purchases and admin restocking.</p>}</> : <><p className="muted">{vehicle.make} {vehicle.model} · {vehicle.quantity} available</p>
        {type === 'restock' ? <label>Quantity to add<input name="quantity" type="number" min="1" max="2147483647" step="1" defaultValue="1" required autoFocus /></label> : <p>This removes the vehicle from inventory. This action cannot be undone.</p>}
      </>}
      <div className="modal-actions"><button type="button" className="button secondary" onClick={close}>Cancel</button><button className={`button ${type === 'delete' ? 'danger' : 'primary'}`} type="submit">{busy ? 'Saving…' : { add: 'Add vehicle', edit: 'Save changes', restock: 'Add stock', delete: 'Delete vehicle' }[type]}</button></div>
    </fieldset></form>
  </dialog>;
}

function Dashboard({ session, onLogout }) {
  const [vehicles, setVehicles] = useState([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [applied, setApplied] = useState(emptyFilters);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [buying, setBuying] = useState(null);
  const [modal, setModal] = useState(null);
  const admin = session.user.role === 'admin';
  const api = useMemo(() => createApi(undefined, () => session.access_token, () => onLogout('Your session has expired. Please sign in again.')), [session, onLogout]);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setLoading(true); setError('');
    const query = new URLSearchParams(Object.entries(applied).filter(([, value]) => value !== ''));
    api(query.size ? `/vehicles/search?${query}` : '/vehicles', { signal: controller.signal })
      .then(data => { if (active) setVehicles(data); })
      .catch(err => { if (active && err.name !== 'AbortError') setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [api, applied, revision]);

  async function purchase(vehicle) {
    setBuying(vehicle.id); setError(''); setSuccess('');
    try {
      await api(`/vehicles/${vehicle.id}/purchase`, { method: 'POST', body: { quantity: 1 } });
      setSuccess(`Purchased one ${vehicle.make} ${vehicle.model}. Inventory is being refreshed.`);
      setRevision(value => value + 1);
    } catch (err) { setError(err.message); }
    finally { setBuying(null); }
  }
  const activeSearch = Object.values(applied).some(Boolean);
  const stock = vehicles.reduce((sum, vehicle) => sum + vehicle.quantity, 0);
  const value = vehicles.reduce((sum, vehicle) => sum + Number(vehicle.price) * vehicle.quantity, 0);
  const outOfStock = vehicles.filter(vehicle => vehicle.quantity === 0).length;
  const unavailable = loading || Boolean(error);
  function search(event) {
    event.preventDefault();
    if (filters.min_price !== '' && filters.max_price !== '' && Number(filters.min_price) > Number(filters.max_price)) {
      setError('Minimum price must not exceed maximum price.'); return;
    }
    setApplied({ ...filters, q: filters.q.trim(), category: filters.category.trim() }); setSuccess('');
  }
  return <div className="app-shell">
    <aside className="sidebar"><Brand /><span className="nav-label">WORKSPACE</span><a className="nav-item" href="#inventory"><Icon name="grid" /> Vehicle inventory <span>01</span></a><div className="sidebar-note"><span className="status-dot" /> Your next move starts here.<p>Every vehicle.<br />Every opportunity.</p><Icon name="car" width="42" height="42" /></div><div className="sidebar-bottom">MOTORHOUSE / INVENTORY SYSTEM</div></aside>
    <div className="workspace"><header className="topbar"><span className="breadcrumb">Workspace <span>/</span> <strong>Inventory</strong></span><div className="account"><span className="avatar">{session.user.email[0].toUpperCase()}</span><div><span className="account-email">{session.user.email}</span><span className="account-role">{admin ? 'Administrator' : 'Member'}</span></div><button className="logout" onClick={() => onLogout('')} title="Log out"><Icon name="logout" /><span>Log out</span></button></div></header>
      <main id="inventory" className="main-content"><div className="page-heading"><div><span className="eyebrow">YOUR SHOWROOM, AT A GLANCE</span><h1>Vehicle inventory<span className="accent">.</span></h1><p className="muted">Find the right vehicle. Keep your inventory moving.</p></div><button className="button primary" disabled={buying !== null} onClick={() => { setModal({ type: 'add' }); setSuccess(''); }}><Icon name="plus" /> Add vehicle</button></div>
        <section className="stats" aria-label={activeSearch ? 'Search result totals' : 'Inventory totals'}>
          <div className="stat"><span>{activeSearch ? 'Matching vehicles' : 'Vehicle listings'}</span><strong>{unavailable ? '—' : vehicles.length.toLocaleString()}</strong><small>Distinct makes & models</small></div>
          <div className="stat"><span>Available units</span><strong>{unavailable ? '—' : stock.toLocaleString()}</strong><small>{activeSearch ? 'Across matching vehicles' : 'Ready for their next journey'}</small></div>
          <div className="stat"><span>Inventory value</span><strong className="value">{unavailable ? '—' : money(value)}</strong><small>{activeSearch ? 'Value of matching stock · USD' : 'Current stock value · USD'}</small></div>
          <div className="stat"><span>Out of stock</span><strong>{unavailable ? '—' : outOfStock}</strong><small>Listings awaiting restock</small></div>
        </section>
        <section className="inventory-section"><div className="section-title"><h2>The collection <span>{unavailable ? '…' : vehicles.length}</span></h2><button className="text-button" disabled={loading || buying !== null} onClick={() => setRevision(v => v + 1)}>Refresh inventory ↻</button></div>
          <form className="search-bar" onSubmit={search}><label className="search-field"><span className="sr-only">Search make, model or category</span><Icon name="search" /><input placeholder="Search make, model or category…" value={filters.q} onChange={e => setFilters({ ...filters, q: e.target.value })} /></label>
            <label><span className="sr-only">Category</span><input placeholder="Category" value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })} /></label>
            <label><span className="sr-only">Minimum price</span><input type="number" min="0" step="0.01" placeholder="Min price" value={filters.min_price} onChange={e => setFilters({ ...filters, min_price: e.target.value })} /></label>
            <label><span className="sr-only">Maximum price</span><input type="number" min="0" step="0.01" placeholder="Max price" value={filters.max_price} onChange={e => setFilters({ ...filters, max_price: e.target.value })} /></label>
            <button className="button primary" disabled={loading || buying !== null}>Search</button>
            {(activeSearch || Object.values(filters).some(Boolean)) && <button type="button" className="text-button" onClick={() => { setFilters(emptyFilters); setApplied(emptyFilters); setSuccess(''); }}>Clear</button>}
          </form>
          <Notice error>{error}</Notice><Notice>{success}</Notice>
          {loading ? <div className="empty-state" role="status"><span className="spinner" /><h3>Loading your inventory…</h3><p>Getting the latest vehicles and stock levels.</p></div>
            : error ? <div className="empty-state"><Icon name="car" width="40" height="40" /><h3>Let’s get you back on the road.</h3><p>Resolve the message above or refresh to load the latest inventory.</p><button className="button secondary" onClick={() => setRevision(v => v + 1)}>Retry inventory</button></div>
            : vehicles.length === 0 ? <div className="empty-state"><Icon name="car" width="44" height="44" /><h3>{activeSearch ? 'No vehicles match your search.' : 'Your showroom starts here.'}</h3><p>{activeSearch ? 'Try a different keyword, category or price range.' : 'Add your first vehicle to bring this inventory to life.'}</p><button className="button secondary" onClick={() => activeSearch ? (setApplied(emptyFilters), setFilters(emptyFilters)) : setModal({ type: 'add' })}>{activeSearch ? 'Clear filters' : 'Add your first vehicle'}</button></div>
            : <div className="vehicle-grid">{vehicles.map(vehicle => <article className="vehicle-card" key={vehicle.id}>
              <div className="vehicle-visual"><span className="category">{vehicle.category}</span><span className="vehicle-id">#{String(vehicle.id).padStart(3, '0')}</span><CarArtwork /><span className="illustration-label">VEHICLE ILLUSTRATION</span></div>
              <div className="vehicle-body"><div className="vehicle-title"><div><span className="make">{vehicle.make}</span><h3>{vehicle.model}</h3></div><span className={`stock-badge ${vehicle.quantity === 0 ? 'sold' : ''}`}><span />{vehicle.quantity === 0 ? 'Out of stock' : `${vehicle.quantity} available`}</span></div>
                <div className="price-row"><strong>{money(vehicle.price)}</strong><span>per vehicle</span></div>
                <div className="card-actions"><button className="button primary" disabled={vehicle.quantity === 0 || buying !== null} onClick={() => purchase(vehicle)}>{buying === vehicle.id ? 'Purchasing…' : vehicle.quantity === 0 ? 'Unavailable' : 'Purchase 1'}{vehicle.quantity > 0 && <Icon name="arrow" />}</button><button className="button secondary" disabled={buying !== null} onClick={() => setModal({ type: 'edit', vehicle })} aria-label={`Edit ${vehicle.make} ${vehicle.model}`}>Edit</button></div>
                {admin && <div className="admin-actions"><button disabled={buying !== null} onClick={() => setModal({ type: 'restock', vehicle })}>＋ Restock</button><button className="delete-link" disabled={buying !== null} onClick={() => setModal({ type: 'delete', vehicle })}>Delete vehicle</button></div>}
              </div>
            </article>)}</div>}
        </section><footer className="page-footer"><span>Motorhouse — made for the journey.</span><span>All prices in USD</span></footer>
      </main>
    </div>
    {modal && <VehicleDialog modal={modal} api={api} close={() => setModal(null)} onSaved={message => { setModal(null); setSuccess(message); setRevision(v => v + 1); }} />}
  </div>;
}

export default function App() {
  const [session, setSession] = useState(readSession);
  const [message, setMessage] = useState('');
  // Stable callback keeps inventory requests from restarting on unrelated renders.
  const logout = useMemo(() => (reason = '') => {
    try { sessionStorage.removeItem(SESSION_KEY); } catch { /* In-memory logout still works. */ }
    setSession(null); setMessage(reason);
  }, []);
  function login(data) {
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)); } catch { /* Session remains usable in memory. */ }
    setSession(data); setMessage('');
  }
  return session ? <Dashboard session={session} onLogout={logout} /> : <Auth onLogin={login} message={message} />;
}
