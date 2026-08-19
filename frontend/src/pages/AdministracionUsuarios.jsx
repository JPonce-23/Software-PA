import React from 'react';
import { ArchiveRestore, Edit3, KeyRound, Plus, Save, Search, ShieldOff, Trash2, X } from 'lucide-react';
import api from '../api/axios';
import PaginatedTable from '../components/PaginatedTable';

const emptyForm = {
  nombre: '', apellido_paterno: '', apellido_materno: '', correo: '',
  rol: 'operador', contrasena: '',
};
const roleLabels = {
  admin: 'Administrador', operador: 'Operador', geografo: 'Geógrafo', visualizador: 'Visualizador',
};
const apiError = (error) => error.response?.data?.detail || 'No fue posible completar la operación.';

function IconButton({ title, onClick, danger = false, children }) {
  return <button type="button" className={`admin-icon-button${danger ? ' danger' : ''}`} title={title} aria-label={title} onClick={onClick}>{children}</button>;
}

function ReasonDialog({ title, onCancel, onConfirm }) {
  const [reason, setReason] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  return <div className="admin-dialog-backdrop"><form className="admin-dialog" onSubmit={async (event) => { event.preventDefault(); setSaving(true); try { await onConfirm(reason.trim()); } finally { setSaving(false); } }}>
    <header><h2>{title}</h2><IconButton title="Cerrar" onClick={onCancel}><X size={18} /></IconButton></header>
    <label className="admin-field"><span>Motivo</span><textarea required minLength={3} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
    <footer><button type="button" className="admin-button secondary" onClick={onCancel}>Cancelar</button><button className="admin-button" disabled={saving || reason.trim().length < 3}>Confirmar</button></footer>
  </form></div>;
}

export default function AdministracionUsuarios() {
  const [users, setUsers] = React.useState([]);
  const [form, setForm] = React.useState(emptyForm);
  const [editing, setEditing] = React.useState(null);
  const [showForm, setShowForm] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const [reasonAction, setReasonAction] = React.useState(null);
  const [showInactive, setShowInactive] = React.useState(false);
  const [search, setSearch] = React.useState('');

  const load = React.useCallback(async () => {
    setLoading(true); setError('');
    try { setUsers((await api.get('/administracion/usuarios?incluir_inactivos=true')).data); }
    catch (requestError) { setError(apiError(requestError)); }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { load(); }, [load]);

  const openCreate = () => { setForm(emptyForm); setEditing(null); setShowForm(true); };
  const openEdit = (user) => {
    setForm({
      nombre: user.nombre, apellido_paterno: user.apellido_paterno,
      apellido_materno: user.apellido_materno || '', correo: user.correo,
      rol: user.rol, contrasena: '',
    });
    setEditing(user.id_usuario); setShowForm(true);
  };
  const change = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      if (editing) {
        const { nombre, apellido_paterno, apellido_materno, rol } = form;
        await api.put(`/usuarios/${editing}`, { nombre, apellido_paterno, apellido_materno: apellido_materno || null, rol });
      } else {
        await api.post('/usuarios', { ...form, apellido_materno: form.apellido_materno || null });
      }
      setShowForm(false); await load();
    } catch (requestError) { setError(apiError(requestError)); }
    finally { setSaving(false); }
  };

  const confirmReason = async (reason) => {
    const { type, user } = reasonAction;
    try {
      if (type === 'delete') await api.delete(`/usuarios/${user.id_usuario}?motivo=${encodeURIComponent(reason)}`);
      if (type === 'restore') await api.post(`/administracion/usuarios/${user.id_usuario}/reactivar`, { motivo: reason });
      if (type === 'sessions') await api.post(`/usuarios/${user.id_usuario}/revocar-sesiones`, { motivo: reason });
      if (type === 'unlock') await api.post(`/usuarios/${user.id_usuario}/desbloquear`, { motivo: reason });
      setReasonAction(null); await load();
    } catch (requestError) { setError(apiError(requestError)); setReasonAction(null); }
  };

  const sourceUsers = showInactive ? users : users.filter((user) => user.activo);
  const normalizedSearch = search.trim().toLowerCase();
  const visibleUsers = normalizedSearch
    ? sourceUsers.filter((user) => [user.nombre, user.apellido_paterno, user.apellido_materno, user.correo, user.rol].some((value) => String(value ?? '').toLowerCase().includes(normalizedSearch)))
    : sourceUsers;

  const tableColumns = [
    { header: 'Nombre', render: (user) => <strong>{user.nombre} {user.apellido_paterno}</strong> },
    { header: 'Correo', render: (user) => user.correo },
    { header: 'Rol', render: (user) => roleLabels[user.rol] },
    { header: 'Estado', render: (user) => <span className={`admin-status ${user.activo ? 'active' : 'inactive'}`}>{user.activo ? 'Activo' : 'Inactivo'}</span> },
    {
      header: 'Acciones',
      className: 'admin-actions-cell',
      render: (user) => user.activo ? (
        <>
          <IconButton title="Editar" onClick={() => openEdit(user)}><Edit3 size={16} /></IconButton>
          <IconButton title="Desbloquear cuenta" onClick={() => setReasonAction({ type: 'unlock', user })}><KeyRound size={16} /></IconButton>
          <IconButton title="Revocar sesiones" onClick={() => setReasonAction({ type: 'sessions', user })}><ShieldOff size={16} /></IconButton>
          <IconButton title="Dar de baja" danger onClick={() => setReasonAction({ type: 'delete', user })}><Trash2 size={16} /></IconButton>
        </>
      ) : (
        <IconButton title="Reactivar" onClick={() => setReasonAction({ type: 'restore', user })}><ArchiveRestore size={16} /></IconButton>
      )
    }
  ];

  return <section className="admin-page">
    <div className="admin-toolbar"><div><h2 className="admin-section-title">Usuarios y roles</h2><p className="admin-section-copy">Cuentas, roles y acceso vigente</p></div><div className="admin-toolbar-actions"><label className="admin-history-toggle"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inactivos</label><button type="button" className="admin-button" onClick={openCreate}><Plus size={16} />Nuevo usuario</button></div></div>
    <label className="admin-search"><Search size={16} /><input type="search" placeholder="Buscar por nombre, correo o rol" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    {error && <div className="admin-error" role="alert">{error}</div>}
    {showForm && <form className="admin-form-band" onSubmit={submit}>
      <div className="admin-form-heading"><h2>{editing ? 'Editar usuario' : 'Nuevo usuario'}</h2><IconButton title="Cerrar formulario" onClick={() => setShowForm(false)}><X size={18} /></IconButton></div>
      <div className="admin-form-grid">
        <label className="admin-field"><span>Nombre</span><input required value={form.nombre} onChange={(e) => change('nombre', e.target.value)} /></label>
        <label className="admin-field"><span>Apellido paterno</span><input required value={form.apellido_paterno} onChange={(e) => change('apellido_paterno', e.target.value)} /></label>
        <label className="admin-field"><span>Apellido materno</span><input value={form.apellido_materno} onChange={(e) => change('apellido_materno', e.target.value)} /></label>
        <label className="admin-field"><span>Correo</span><input type="email" required disabled={Boolean(editing)} value={form.correo} onChange={(e) => change('correo', e.target.value)} /></label>
        <label className="admin-field"><span>Rol</span><select value={form.rol} onChange={(e) => change('rol', e.target.value)}>{Object.entries(roleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        {!editing && <label className="admin-field"><span>Contraseña temporal</span><input type="password" required minLength={12} autoComplete="new-password" value={form.contrasena} onChange={(e) => change('contrasena', e.target.value)} /></label>}
      </div>
      <div className="admin-form-actions"><button className="admin-button" disabled={saving}><Save size={16} />{saving ? 'Guardando...' : 'Guardar'}</button></div>
    </form>}
    <PaginatedTable
      columns={tableColumns}
      data={visibleUsers}
      loading={loading}
      keyField="id_usuario"
      rowClassName={(user) => (!user.activo ? 'inactive' : '')}
      emptyMessage="No hay usuarios."
    />
    {reasonAction && <ReasonDialog title={reasonAction.type === 'sessions' ? 'Revocar sesiones' : reasonAction.type === 'unlock' ? 'Desbloquear cuenta' : reasonAction.type === 'delete' ? 'Dar de baja al usuario' : 'Reactivar usuario'} onCancel={() => setReasonAction(null)} onConfirm={confirmReason} />}
  </section>;
}
