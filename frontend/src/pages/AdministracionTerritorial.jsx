import React from 'react';
import {
  ArchiveRestore, Edit3, FolderKanban, Layers, Link2, Map, Plus, Save,
  Search, Trash2, UserRoundCog, X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

const tabs = [
  ['proyectos', 'Proyectos', FolderKanban],
  ['tramos', 'Tramos', Map],
  ['nucleos', 'Núcleos', Map],
  ['relaciones', 'Tramo - núcleo', Link2],
];

const emptyForms = {
  proyectos: { clave_proyecto: '', nombre_proyecto: '', descripcion: '' },
  tramos: {
    id_proyecto: '', clave_tramo: '', nombre_tramo: '', descripcion: '',
    ancho_total_derecho_via_m: '40.00', geometria_wkt: '',
  },
  nucleos: {
    id_municipio: '', nombre_nucleo: '', tipo_nucleo: 'ejido',
    comunidad_indigena: false, residencia: '', geometria_wkt: '',
  },
  relaciones: {
    id_tramo: '', id_nucleo: '', consecutivo: '', numero_tramo: '',
    geometria_wkt: '', es_expropiacion: false,
  },
};

const apiError = (error) => error.response?.data?.detail || 'No fue posible completar la operación.';

function Field({ label, children }) {
  return <label className="admin-field"><span>{label}</span>{children}</label>;
}

function ActionButton({ title, onClick, danger = false, children }) {
  return (
    <button
      type="button"
      className={`admin-icon-button${danger ? ' danger' : ''}`}
      title={title}
      aria-label={title}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function ReasonDialog({ title, onCancel, onConfirm }) {
  const [reason, setReason] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  return (
    <div className="admin-dialog-backdrop" role="presentation">
      <form
        className="admin-dialog"
        onSubmit={async (event) => {
          event.preventDefault();
          setSaving(true);
          try { await onConfirm(reason.trim()); } finally { setSaving(false); }
        }}
      >
        <header><h2>{title}</h2><ActionButton title="Cerrar" onClick={onCancel}><X size={18} /></ActionButton></header>
        <Field label="Motivo"><textarea required minLength={3} value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
        <footer>
          <button type="button" className="admin-button secondary" onClick={onCancel}>Cancelar</button>
          <button type="submit" className="admin-button" disabled={saving || reason.trim().length < 3}>Confirmar</button>
        </footer>
      </form>
    </div>
  );
}

function AssignmentDialog({ tramo, users, onCancel, onSaved, setPageError }) {
  const [selected, setSelected] = React.useState([]);
  const [reason, setReason] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    api.get(`/administracion/tramos/${tramo.id_tramo}/asignaciones`)
      .then(({ data }) => setSelected(data.map((item) => item.id_usuario)))
      .catch((error) => setPageError(apiError(error)))
      .finally(() => setLoading(false));
  }, [tramo.id_tramo, setPageError]);

  return (
    <div className="admin-dialog-backdrop" role="presentation">
      <form
        className="admin-dialog admin-dialog-wide"
        onSubmit={async (event) => {
          event.preventDefault();
          setSaving(true);
          try {
            await api.put(`/administracion/tramos/${tramo.id_tramo}/asignaciones`, {
              ids_usuario: selected,
              motivo: reason,
            });
            onSaved();
          } catch (error) {
            setPageError(apiError(error));
          } finally { setSaving(false); }
        }}
      >
        <header><div><h2>Acceso territorial</h2><p>{tramo.clave_tramo} · {tramo.nombre_tramo}</p></div><ActionButton title="Cerrar" onClick={onCancel}><X size={18} /></ActionButton></header>
        {loading ? <p className="admin-empty">Cargando asignaciones...</p> : (
          <div className="admin-check-list">
            {users.filter((user) => user.activo).map((user) => (
              <label key={user.id_usuario}>
                <input
                  type="checkbox"
                  checked={selected.includes(user.id_usuario)}
                  onChange={() => setSelected((current) => current.includes(user.id_usuario)
                    ? current.filter((id) => id !== user.id_usuario)
                    : [...current, user.id_usuario])}
                />
                <span><strong>{user.nombre} {user.apellido_paterno}</strong><small>{user.correo} · {user.rol}</small></span>
              </label>
            ))}
          </div>
        )}
        <Field label="Motivo del cambio"><textarea required minLength={3} value={reason} onChange={(event) => setReason(event.target.value)} /></Field>
        <footer>
          <button type="button" className="admin-button secondary" onClick={onCancel}>Cancelar</button>
          <button type="submit" className="admin-button" disabled={saving || loading || reason.trim().length < 3}><Save size={16} /> Guardar asignaciones</button>
        </footer>
      </form>
    </div>
  );
}

export default function AdministracionTerritorial() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState('proyectos');
  const [data, setData] = React.useState({ proyectos: [], tramos: [], nucleos: [], relaciones: [], usuarios: [], municipios: [] });
  const [form, setForm] = React.useState(emptyForms.proyectos);
  const [editingId, setEditingId] = React.useState(null);
  const [showForm, setShowForm] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const [reasonAction, setReasonAction] = React.useState(null);
  const [assignmentTramo, setAssignmentTramo] = React.useState(null);
  const [showInactive, setShowInactive] = React.useState(false);
  const [search, setSearch] = React.useState('');

  const load = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [proyectos, tramos, nucleos, relaciones, usuarios, municipios] = await Promise.all([
        api.get('/administracion/proyectos?incluir_inactivos=true'),
        api.get('/administracion/tramos?incluir_inactivos=true'),
        api.get('/administracion/nucleos?incluir_inactivos=true'),
        api.get('/administracion/tramos-nucleos?incluir_inactivos=true'),
        api.get('/administracion/usuarios?incluir_inactivos=true'),
        api.get('/catalogos/municipios'),
      ]);
      setData({
        proyectos: proyectos.data, tramos: tramos.data, nucleos: nucleos.data,
        relaciones: relaciones.data, usuarios: usuarios.data, municipios: municipios.data,
      });
    } catch (requestError) { setError(apiError(requestError)); } finally { setLoading(false); }
  }, []);

  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    setForm({ ...emptyForms[activeTab] });
    setEditingId(null);
    setShowForm(false);
    setSearch('');
  }, [activeTab]);

  const updateField = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const openCreate = () => { setForm({ ...emptyForms[activeTab] }); setEditingId(null); setShowForm(true); };
  const openEdit = (item) => {
    const next = { ...emptyForms[activeTab], ...item };
    if (next.geometria_wkt == null) next.geometria_wkt = '';
    setForm(next); setEditingId(item[`id_${activeTab === 'relaciones' ? 'tramo_nucleo' : activeTab.slice(0, -1)}`]); setShowForm(true);
  };

  const submit = async (event) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const payload = { ...form };
      Object.keys(payload).forEach((key) => { if (payload[key] === '') payload[key] = null; });
      let path;
      if (activeTab === 'proyectos') path = editingId ? `/proyectos/${editingId}` : '/proyectos';
      if (activeTab === 'tramos') path = editingId ? `/tramos/${editingId}` : '/tramos';
      if (activeTab === 'nucleos') path = editingId ? `/nucleos/${editingId}` : '/nucleos';
      if (activeTab === 'relaciones') path = editingId ? `/tramos-nucleos/${editingId}` : '/tramos-nucleos';
      if (editingId) {
        const immutable = activeTab === 'proyectos' ? ['clave_proyecto']
          : activeTab === 'tramos' ? ['id_proyecto', 'clave_tramo']
            : activeTab === 'nucleos' ? ['id_municipio', 'tipo_nucleo']
              : ['id_tramo', 'id_nucleo', 'consecutivo'];
        immutable.forEach((key) => delete payload[key]);
      }
      await api[editingId ? 'put' : 'post'](path, payload);
      setShowForm(false); await load();
    } catch (requestError) { setError(apiError(requestError)); } finally { setSaving(false); }
  };

  const confirmLifecycle = async (reason) => {
    const { item, type } = reasonAction;
    const singular = type === 'relaciones' ? 'tramos-nucleos' : type;
    const idKey = type === 'proyectos' ? 'id_proyecto' : type === 'tramos' ? 'id_tramo' : type === 'nucleos' ? 'id_nucleo' : 'id_tramo_nucleo';
    try {
      if (item.activo) await api.delete(`/${singular}/${item[idKey]}?motivo=${encodeURIComponent(reason)}`);
      else await api.post(`/administracion/${singular}/${item[idKey]}/reactivar`, { motivo: reason });
      setReasonAction(null); await load();
    } catch (requestError) { setError(apiError(requestError)); setReasonAction(null); }
  };

  const renderForm = () => (
    <form className="admin-form-band" onSubmit={submit}>
      <div className="admin-form-heading"><h2>{editingId ? 'Editar registro' : 'Nuevo registro'}</h2><ActionButton title="Cerrar formulario" onClick={() => setShowForm(false)}><X size={18} /></ActionButton></div>
      <div className="admin-form-grid">
        {activeTab === 'proyectos' && <>
          <Field label="Clave"><input required disabled={Boolean(editingId)} value={form.clave_proyecto ?? ''} onChange={(e) => updateField('clave_proyecto', e.target.value)} /></Field>
          <Field label="Nombre"><input required value={form.nombre_proyecto ?? ''} onChange={(e) => updateField('nombre_proyecto', e.target.value)} /></Field>
          <Field label="Descripción"><input value={form.descripcion ?? ''} onChange={(e) => updateField('descripcion', e.target.value)} /></Field>
        </>}
        {activeTab === 'tramos' && <>
          <Field label="Proyecto"><select required disabled={Boolean(editingId)} value={form.id_proyecto ?? ''} onChange={(e) => updateField('id_proyecto', Number(e.target.value))}><option value="">Selecciona</option>{data.proyectos.filter((p) => p.activo).map((p) => <option key={p.id_proyecto} value={p.id_proyecto}>{p.clave_proyecto} · {p.nombre_proyecto}</option>)}</select></Field>
          <Field label="Clave"><input required disabled={Boolean(editingId)} value={form.clave_tramo ?? ''} onChange={(e) => updateField('clave_tramo', e.target.value)} /></Field>
          <Field label="Nombre"><input required value={form.nombre_tramo ?? ''} onChange={(e) => updateField('nombre_tramo', e.target.value)} /></Field>
          <Field label="Ancho total (m)"><input type="number" min="0.01" step="0.01" value={form.ancho_total_derecho_via_m ?? ''} onChange={(e) => updateField('ancho_total_derecho_via_m', e.target.value)} /></Field>
          <Field label="Descripción"><input value={form.descripcion ?? ''} onChange={(e) => updateField('descripcion', e.target.value)} /></Field>
          <Field label="Geometría MULTILINESTRING"><textarea value={form.geometria_wkt ?? ''} onChange={(e) => updateField('geometria_wkt', e.target.value)} /></Field>
        </>}
        {activeTab === 'nucleos' && <>
          <Field label="Municipio"><select required disabled={Boolean(editingId)} value={form.id_municipio ?? ''} onChange={(e) => updateField('id_municipio', Number(e.target.value))}><option value="">Selecciona</option>{data.municipios.map((m) => <option key={m.id_municipio} value={m.id_municipio}>{m.nombre}</option>)}</select></Field>
          <Field label="Nombre"><input required value={form.nombre_nucleo ?? ''} onChange={(e) => updateField('nombre_nucleo', e.target.value)} /></Field>
          <Field label="Tipo"><select disabled={Boolean(editingId)} value={form.tipo_nucleo ?? 'ejido'} onChange={(e) => updateField('tipo_nucleo', e.target.value)}><option value="ejido">Ejido</option><option value="comunidad">Comunidad</option></select></Field>
          <Field label="Residencia"><input value={form.residencia ?? ''} onChange={(e) => updateField('residencia', e.target.value)} /></Field>
          <label className="admin-toggle"><input type="checkbox" checked={Boolean(form.comunidad_indigena)} onChange={(e) => updateField('comunidad_indigena', e.target.checked)} /><span>Comunidad indígena</span></label>
          <Field label="Geometría MULTIPOLYGON"><textarea value={form.geometria_wkt ?? ''} onChange={(e) => updateField('geometria_wkt', e.target.value)} /></Field>
        </>}
        {activeTab === 'relaciones' && <>
          <Field label="Tramo"><select required disabled={Boolean(editingId)} value={form.id_tramo ?? ''} onChange={(e) => updateField('id_tramo', Number(e.target.value))}><option value="">Selecciona</option>{data.tramos.filter((t) => t.activo).map((t) => <option key={t.id_tramo} value={t.id_tramo}>{t.clave_tramo} · {t.nombre_tramo}</option>)}</select></Field>
          <Field label="Núcleo"><select required disabled={Boolean(editingId)} value={form.id_nucleo ?? ''} onChange={(e) => updateField('id_nucleo', Number(e.target.value))}><option value="">Selecciona</option>{data.nucleos.filter((n) => n.activo).map((n) => <option key={n.id_nucleo} value={n.id_nucleo}>{n.nombre_nucleo}</option>)}</select></Field>
          <Field label="Consecutivo"><input required type="number" min="1" disabled={Boolean(editingId)} value={form.consecutivo ?? ''} onChange={(e) => updateField('consecutivo', Number(e.target.value))} /></Field>
          <Field label="Número de tramo"><input value={form.numero_tramo ?? ''} onChange={(e) => updateField('numero_tramo', e.target.value)} /></Field>
          <label className="admin-toggle"><input type="checkbox" checked={Boolean(form.es_expropiacion)} onChange={(e) => updateField('es_expropiacion', e.target.checked)} /><span>Es expropiación</span></label>
          <Field label="Geometría MULTILINESTRING"><textarea value={form.geometria_wkt ?? ''} onChange={(e) => updateField('geometria_wkt', e.target.value)} /></Field>
        </>}
      </div>
      <div className="admin-form-actions"><button className="admin-button" disabled={saving} type="submit"><Save size={16} />{saving ? 'Guardando...' : 'Guardar'}</button></div>
    </form>
  );

  const normalizedSearch = search.trim().toLowerCase();
  const sourceItems = showInactive ? data[activeTab] : data[activeTab].filter((item) => item.activo);
  const items = normalizedSearch
    ? sourceItems.filter((item) => Object.values(item).some((value) => String(value ?? '').toLowerCase().includes(normalizedSearch)))
    : sourceItems;
  const projectName = (id) => data.proyectos.find((item) => item.id_proyecto === id)?.clave_proyecto || '—';
  const tramoName = (id) => data.tramos.find((item) => item.id_tramo === id)?.clave_tramo || '—';
  const nucleoName = (id) => data.nucleos.find((item) => item.id_nucleo === id)?.nombre_nucleo || '—';

  return (
    <section className="admin-page">
      <div className="admin-toolbar">
        <div className="admin-tabs" role="tablist">{tabs.map(([key, label, Icon]) => <button key={key} type="button" role="tab" aria-selected={activeTab === key} className={activeTab === key ? 'active' : ''} onClick={() => setActiveTab(key)}><Icon size={16} />{label}</button>)}</div>
        <div className="admin-toolbar-actions"><label className="admin-history-toggle"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inactivos</label><button className="admin-button" type="button" onClick={openCreate}><Plus size={16} />Nuevo</button></div>
      </div>
      <label className="admin-search"><Search size={16} /><input type="search" placeholder="Buscar en esta vista" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      {error && <div className="admin-error" role="alert">{error}</div>}
      {showForm && renderForm()}
      <div className="admin-table-wrap">
        {loading ? <p className="admin-empty">Cargando registros...</p> : items.length === 0 ? <p className="admin-empty">No hay registros.</p> : (
          <table className="admin-table">
            <thead><tr>
              {activeTab === 'proyectos' && <><th>Clave</th><th>Proyecto</th></>}
              {activeTab === 'tramos' && <><th>Clave</th><th>Tramo</th><th>Proyecto</th><th>Ancho</th></>}
              {activeTab === 'nucleos' && <><th>Núcleo</th><th>Tipo</th><th>Residencia</th></>}
              {activeTab === 'relaciones' && <><th>Tramo</th><th>Núcleo</th><th>Consecutivo</th><th>Número</th></>}
              <th>Estado</th><th className="admin-actions-cell">Acciones</th>
            </tr></thead>
            <tbody>{items.map((item) => {
              const id = item.id_proyecto || item.id_tramo_nucleo || item.id_tramo || item.id_nucleo;
              return <tr key={id} className={!item.activo ? 'inactive' : ''}>
                {activeTab === 'proyectos' && <><td data-label="Clave"><strong>{item.clave_proyecto}</strong></td><td data-label="Proyecto">{item.nombre_proyecto}</td></>}
                {activeTab === 'tramos' && <><td data-label="Clave"><strong>{item.clave_tramo}</strong></td><td data-label="Tramo">{item.nombre_tramo}</td><td data-label="Proyecto">{projectName(item.id_proyecto)}</td><td data-label="Ancho">{item.ancho_total_derecho_via_m ?? '—'} m</td></>}
                {activeTab === 'nucleos' && <><td data-label="Núcleo"><strong>{item.nombre_nucleo}</strong></td><td data-label="Tipo">{item.tipo_nucleo}</td><td data-label="Residencia">{item.residencia || '—'}</td></>}
                {activeTab === 'relaciones' && <><td data-label="Tramo"><strong>{tramoName(item.id_tramo)}</strong></td><td data-label="Núcleo">{nucleoName(item.id_nucleo)}</td><td data-label="Consecutivo">{item.consecutivo}</td><td data-label="Número">{item.numero_tramo || '—'}</td></>}
                <td data-label="Estado"><span className={`admin-status ${item.activo ? 'active' : 'inactive'}`}>{item.activo ? 'Activo' : 'Inactivo'}</span></td>
                <td data-label="Acciones" className="admin-actions-cell">
                  {item.activo && <ActionButton title="Editar" onClick={() => openEdit(item)}><Edit3 size={16} /></ActionButton>}
                  {activeTab === 'tramos' && item.activo && <ActionButton title="Abrir mapa y derecho de vía" onClick={() => navigate(`/mapa?id_tramo=${item.id_tramo}`)}><Layers size={16} /></ActionButton>}
                  {activeTab === 'tramos' && item.activo && <ActionButton title="Asignar usuarios" onClick={() => setAssignmentTramo(item)}><UserRoundCog size={16} /></ActionButton>}
                  {activeTab === 'relaciones' && item.activo && <ActionButton title="Abrir expediente" onClick={() => navigate(`/expedientes/${item.id_tramo_nucleo}`)}><FolderKanban size={16} /></ActionButton>}
                  <ActionButton title={item.activo ? 'Dar de baja' : 'Reactivar'} danger={item.activo} onClick={() => setReasonAction({ item, type: activeTab })}>{item.activo ? <Trash2 size={16} /> : <ArchiveRestore size={16} />}</ActionButton>
                </td>
              </tr>;
            })}</tbody>
          </table>
        )}
      </div>
      {reasonAction && <ReasonDialog title={reasonAction.item.activo ? 'Confirmar baja lógica' : 'Confirmar reactivación'} onCancel={() => setReasonAction(null)} onConfirm={confirmLifecycle} />}
      {assignmentTramo && <AssignmentDialog tramo={assignmentTramo} users={data.usuarios} onCancel={() => setAssignmentTramo(null)} onSaved={async () => { setAssignmentTramo(null); await load(); }} setPageError={setError} />}
    </section>
  );
}
