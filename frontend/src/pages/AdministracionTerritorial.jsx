import React from 'react';
import {
  ArchiveRestore, Edit3, FolderKanban, Layers, Link2, Map, Plus, Save,
  Search, Trash2, UserRoundCog, X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import AuthContext from '../contexts/auth-context';
import PaginatedTable from '../components/PaginatedTable';
import GeospatialUpload from '../components/GeospatialUpload';
import TramoNucleoCandidates from '../components/TramoNucleoCandidates';
import SeccionDerechoViaPanel from '../components/SeccionDerechoViaPanel';
import FranjaDerechoViaPanel from '../components/fase2/FranjaDerechoViaPanel';

const allTabs = [
  ['proyectos', 'Proyectos', FolderKanban],
  ['trazos', 'Trazo ferroviario', Layers],
  ['tramos', 'Tramos', Map],
  ['nucleos', 'Núcleos', Map],
  ['relaciones', 'Tramo - núcleo', Link2],
];

const emptyForms = {
  proyectos: { clave_proyecto: '', nombre_proyecto: '', descripcion: '' },
  tramos: {
    id_proyecto: '', clave_tramo: '', nombre_tramo: '', descripcion: '',
  },
  nucleos: {
    id_entidad: '', id_municipio: '', nombre_nucleo: '', tipo_nucleo: 'ejido',
    comunidad_indigena: false, residencia: '', geometria_wkt: '',
    id_carga_geoespacial_feature: null,
  },
  relaciones: {
    id_tramo: '', id_nucleo: '', consecutivo: '', numero_tramo: '',
    geometria_wkt: '', es_expropiacion: false, proyecto_no_afecta_uso_comun: false,
    causa_problema: '',
  },
};

const apiError = (error) => error.response?.data?.detail || 'No fue posible completar la operación.';

function Field({ label, children }) {
  return <label className="admin-field"><span>{label}</span>{children}</label>;
}

function GeometryField({ label, expected, example, value, onChange }) {
  const invalid = value && !value.trim().toUpperCase().startsWith(expected);
  return (
    <details className="admin-field admin-field-wide">
      <summary>Captura avanzada: {label}</summary>
      <textarea
        className={invalid ? 'admin-input-invalid' : ''}
        value={value ?? ''}
        placeholder={example}
        spellCheck="false"
        onChange={(event) => onChange(event.target.value)}
      />
      <small>Uso exclusivo para soporte técnico. Formato WKT esperado: {expected}. Ejemplo: {example}</small>
      {invalid && <em>La geometría debe iniciar con {expected}; PostgreSQL validará tipo, SRID, topología y vacío.</em>}
    </details>
  );
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
  const { user } = React.useContext(AuthContext);
  const isAdmin = user?.rol === 'admin';
  const tabs = React.useMemo(
    () => allTabs.filter(([key]) => isAdmin || ['proyectos', 'trazos', 'tramos', 'nucleos'].includes(key)),
    [isAdmin],
  );
  const [activeTab, setActiveTab] = React.useState('proyectos');
  const [data, setData] = React.useState({ proyectos: [], trazos: [], tramos: [], nucleos: [], relaciones: [], usuarios: [], municipios: [], entidades: [] });
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
  const [nucleoFilters, setNucleoFilters] = React.useState({ id_proyecto: '', id_entidad: '', id_municipio: '' });
  const [trazoProjectId, setTrazoProjectId] = React.useState('');
  const [sectionTramo, setSectionTramo] = React.useState(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const nucleosParams = new URLSearchParams({ incluir_inactivos: 'true' });
      Object.entries(nucleoFilters).forEach(([key, value]) => {
        if (value) nucleosParams.set(key, value);
      });
      const requests = [
        api.get('/administracion/proyectos?incluir_inactivos=true'),
        api.get('/administracion/tramos?incluir_inactivos=true'),
        api.get(`/administracion/nucleos?${nucleosParams.toString()}`),
        api.get('/catalogos/municipios'),
        api.get('/catalogos/entidades'),
      ];
      if (isAdmin) {
        requests.push(
          api.get('/administracion/tramos-nucleos?incluir_inactivos=true'),
          api.get('/administracion/usuarios?incluir_inactivos=true'),
        );
      }
      const [proyectos, tramos, nucleos, municipios, entidades, relaciones, usuarios] = await Promise.all(requests);
      setData({
        proyectos: proyectos.data, trazos: [], tramos: tramos.data, nucleos: nucleos.data,
        relaciones: relaciones?.data ?? [], usuarios: usuarios?.data ?? [], municipios: municipios.data,
        entidades: entidades.data,
      });
    } catch (requestError) { setError(apiError(requestError)); } finally { setLoading(false); }
  }, [isAdmin, nucleoFilters]);

  React.useEffect(() => { load(); }, [load]);
  React.useEffect(() => {
    if (!tabs.some(([key]) => key === activeTab)) setActiveTab('proyectos');
  }, [activeTab, tabs]);
  React.useEffect(() => {
    setForm({ ...(emptyForms[activeTab] || emptyForms.proyectos) });
    setEditingId(null);
    setShowForm(false);
    setSearch('');
  }, [activeTab]);

  const updateField = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const openCreate = () => { setForm({ ...(emptyForms[activeTab] || emptyForms.proyectos) }); setEditingId(null); setShowForm(true); };
  const openEdit = (item) => {
    const next = { ...emptyForms[activeTab], ...item };
    if (next.geometria_wkt == null) next.geometria_wkt = '';
    if (activeTab === 'nucleos' && next.id_municipio) {
      const municipio = data.municipios.find((m) => m.id_municipio === next.id_municipio);
      next.id_entidad = municipio?.id_entidad ?? next.id_entidad ?? '';
    }
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
      if (activeTab === 'nucleos') delete payload.id_entidad;
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

  const formMunicipios = data.municipios.filter((municipio) => (
    !form.id_entidad || municipio.id_entidad === Number(form.id_entidad)
  ));
  const filterMunicipios = data.municipios.filter((municipio) => (
    !nucleoFilters.id_entidad || municipio.id_entidad === Number(nucleoFilters.id_entidad)
  ));
  const updateNucleoFilter = (key, value) => {
    setNucleoFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === 'id_entidad' ? { id_municipio: '' } : {}),
    }));
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
          <Field label="Descripción"><input value={form.descripcion ?? ''} onChange={(e) => updateField('descripcion', e.target.value)} /></Field>
        </>}
        {activeTab === 'nucleos' && <>
          <Field label="Entidad federativa"><select required disabled={Boolean(editingId)} value={form.id_entidad ?? ''} onChange={(e) => { updateField('id_entidad', e.target.value); updateField('id_municipio', ''); }}><option value="">Selecciona</option>{data.entidades.map((entidad) => <option key={entidad.id_entidad} value={entidad.id_entidad}>{entidad.nombre}</option>)}</select></Field>
          <Field label="Municipio"><select required disabled={Boolean(editingId) || !form.id_entidad} value={form.id_municipio ?? ''} onChange={(e) => updateField('id_municipio', Number(e.target.value))}><option value="">{form.id_entidad ? 'Selecciona' : 'Selecciona primero entidad'}</option>{formMunicipios.map((m) => <option key={m.id_municipio} value={m.id_municipio}>{m.nombre}</option>)}</select></Field>
          <Field label="Nombre"><input required value={form.nombre_nucleo ?? ''} onChange={(e) => updateField('nombre_nucleo', e.target.value)} /></Field>
          <Field label="Tipo"><select disabled={Boolean(editingId)} value={form.tipo_nucleo ?? 'ejido'} onChange={(e) => updateField('tipo_nucleo', e.target.value)}><option value="ejido">Ejido</option><option value="comunidad">Comunidad</option></select></Field>
          <Field label="Residencia"><input value={form.residencia ?? ''} onChange={(e) => updateField('residencia', e.target.value)} /></Field>
          <label className="admin-toggle"><input type="checkbox" checked={Boolean(form.comunidad_indigena)} onChange={(e) => updateField('comunidad_indigena', e.target.checked)} /><span>Comunidad indígena</span></label>
          <div className="admin-field admin-field-wide"><GeospatialUpload target="nucleo_agrario" value={form.id_carga_geoespacial_feature} onChange={(id) => { updateField('id_carga_geoespacial_feature', id); updateField('geometria_wkt', ''); }} /></div>
          <GeometryField label="Geometría del núcleo" expected="MULTIPOLYGON" example="MULTIPOLYGON(((-99.10 19.40, -99.08 19.40, -99.08 19.42, -99.10 19.40)))" value={form.geometria_wkt} onChange={(value) => updateField('geometria_wkt', value)} />
        </>}
        {activeTab === 'relaciones' && <>
          <Field label="Tramo"><select required disabled={Boolean(editingId)} value={form.id_tramo ?? ''} onChange={(e) => updateField('id_tramo', Number(e.target.value))}><option value="">Selecciona</option>{data.tramos.filter((t) => t.activo).map((t) => <option key={t.id_tramo} value={t.id_tramo}>{t.clave_tramo} · {t.nombre_tramo}</option>)}</select></Field>
          <Field label="Núcleo"><select required disabled={Boolean(editingId)} value={form.id_nucleo ?? ''} onChange={(e) => updateField('id_nucleo', Number(e.target.value))}><option value="">Selecciona</option>{data.nucleos.filter((n) => n.activo).map((n) => <option key={n.id_nucleo} value={n.id_nucleo}>{n.nombre_nucleo}</option>)}</select></Field>
          <Field label="Consecutivo"><input required type="number" min="1" disabled={Boolean(editingId)} value={form.consecutivo ?? ''} onChange={(e) => updateField('consecutivo', Number(e.target.value))} /></Field>
          <Field label="Número de tramo"><input value={form.numero_tramo ?? ''} onChange={(e) => updateField('numero_tramo', e.target.value)} /></Field>
          <Field label="¿El proyecto afecta tierras de uso común?">
            <select
              value={form.proyecto_no_afecta_uso_comun ? 'no' : 'si'}
              onChange={(event) => {
                const noAfecta = event.target.value === 'no';
                updateField('proyecto_no_afecta_uso_comun', noAfecta);
                if (!noAfecta) updateField('es_expropiacion', false);
              }}
            >
              <option value="si">Sí</option>
              <option value="no">No</option>
            </select>
          </Field>
          <label className="admin-toggle"><input type="checkbox" checked={Boolean(form.es_expropiacion)} onChange={(e) => {
            updateField('es_expropiacion', e.target.checked);
            if (e.target.checked) updateField('proyecto_no_afecta_uso_comun', true);
          }} /><span>Motivo: Expropiación directa</span></label>
          {data.nucleos.find((n) => n.id_nucleo === Number(form.id_nucleo))?.comunidad_indigena && (
            <div className="admin-field admin-field-wide">
              <small>Motivo detectado por el núcleo: Comunidad indígena. El caso no continúa en el seguimiento ordinario PA.</small>
            </div>
          )}
          <Field label="Motivo u observación de seguimiento"><textarea value={form.causa_problema ?? ''} onChange={(e) => updateField('causa_problema', e.target.value)} /></Field>
          <GeometryField label="Geometría del segmento" expected="MULTILINESTRING" example="MULTILINESTRING((-99.10 19.40, -99.08 19.42))" value={form.geometria_wkt} onChange={(value) => updateField('geometria_wkt', value)} />
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
  const nucleoById = (id) => data.nucleos.find((item) => item.id_nucleo === Number(id));
  const relacionMotivoSinSeguimiento = (item) => {
    const nucleo = nucleoById(item.id_nucleo);
    if (item.es_expropiacion) return 'Expropiación directa';
    if (nucleo?.comunidad_indigena) return 'Comunidad indígena';
    if (item.proyecto_no_afecta_uso_comun) return 'No afecta tierras de uso común';
    return 'Seguimiento ordinario';
  };
  const nucleoProjectLabel = (item) => {
    const projects = item.proyectos_territoriales || [];
    if (projects.length === 0) return 'Sin relación';
    if (projects.length === 1) return projects[0].clave_proyecto;
    return `${projects[0].clave_proyecto} +${projects.length - 1}`;
  };

  const tableColumns = [];
  if (activeTab === 'proyectos') {
    tableColumns.push({ header: 'Clave', render: (item) => <strong>{item.clave_proyecto}</strong> });
    tableColumns.push({ header: 'Proyecto', render: (item) => item.nombre_proyecto });
  } else if (activeTab === 'tramos') {
    tableColumns.push({ header: 'Clave', render: (item) => <strong>{item.clave_tramo}</strong> });
    tableColumns.push({ header: 'Tramo', render: (item) => item.nombre_tramo });
    tableColumns.push({ header: 'Proyecto', render: (item) => projectName(item.id_proyecto) });
  } else if (activeTab === 'nucleos') {
    tableColumns.push({ header: 'Núcleo', render: (item) => <strong>{item.nombre_nucleo}</strong> });
    tableColumns.push({ header: 'Proyecto', render: (item) => nucleoProjectLabel(item) });
    tableColumns.push({ header: 'Entidad', render: (item) => item.entidad_nombre || '—' });
    tableColumns.push({ header: 'Municipio', render: (item) => item.municipio_nombre || '—' });
    tableColumns.push({ header: 'E/C', render: (item) => item.tipo_nucleo === 'ejido' ? 'E · Ejido' : 'C · Comunidad' });
    tableColumns.push({ header: 'Comunidad indígena', render: (item) => item.comunidad_indigena ? 'Sí' : 'No' });
  } else if (activeTab === 'relaciones') {
    tableColumns.push({ header: 'Tramo', render: (item) => <strong>{tramoName(item.id_tramo)}</strong> });
    tableColumns.push({ header: 'Núcleo', render: (item) => nucleoName(item.id_nucleo) });
    tableColumns.push({ header: 'Consecutivo', render: (item) => item.consecutivo });
    tableColumns.push({ header: 'Número', render: (item) => item.numero_tramo || '—' });
    tableColumns.push({ header: 'Uso común', render: (item) => item.proyecto_no_afecta_uso_comun || item.es_expropiacion || nucleoById(item.id_nucleo)?.comunidad_indigena ? 'No' : 'Sí' });
    tableColumns.push({ header: 'Seguimiento PA', render: (item) => relacionMotivoSinSeguimiento(item) });
  }

  tableColumns.push({
    header: 'Estado',
    render: (item) => <span className={`admin-status ${item.activo ? 'active' : 'inactive'}`}>{item.activo ? 'Activo' : 'Inactivo'}</span>
  });

  tableColumns.push({
    header: 'Acciones',
    className: 'admin-actions-cell',
    render: (item) => (
      <>
        {isAdmin && item.activo && <ActionButton title="Editar" onClick={() => openEdit(item)}><Edit3 size={16} /></ActionButton>}
        {activeTab === 'tramos' && item.activo && <ActionButton title="Abrir mapa" onClick={() => navigate(`/mapa?id_tramo=${item.id_tramo}`)}><Layers size={16} /></ActionButton>}
        {activeTab === 'tramos' && item.activo && <ActionButton title="Cargar sección del trazo" onClick={() => setSectionTramo(item)}><Map size={16} /></ActionButton>}
        {isAdmin && activeTab === 'tramos' && item.activo && <ActionButton title="Asignar usuarios" onClick={() => setAssignmentTramo(item)}><UserRoundCog size={16} /></ActionButton>}
        {activeTab === 'relaciones' && item.activo && <ActionButton title="Abrir expediente" onClick={() => navigate(`/expedientes/${item.id_tramo_nucleo}`)}><FolderKanban size={16} /></ActionButton>}
        {isAdmin && <ActionButton title={item.activo ? 'Dar de baja' : 'Reactivar'} danger={item.activo} onClick={() => setReasonAction({ item, type: activeTab })}>{item.activo ? <Trash2 size={16} /> : <ArchiveRestore size={16} />}</ActionButton>}
      </>
    )
  });

  const idKey = activeTab === 'proyectos' ? 'id_proyecto' :
                activeTab === 'tramos' ? 'id_tramo' :
                activeTab === 'nucleos' ? 'id_nucleo' :
                'id_tramo_nucleo';

  return (
    <section className="admin-page">
      <div className="admin-toolbar">
        <div className="admin-tabs" role="tablist">{tabs.map(([key, label, Icon]) => <button key={key} type="button" role="tab" aria-selected={activeTab === key} className={activeTab === key ? 'active' : ''} onClick={() => setActiveTab(key)}><Icon size={16} />{label}</button>)}</div>
        <div className="admin-toolbar-actions">
          {isAdmin && <label className="admin-history-toggle"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inactivos</label>}
          {activeTab !== 'trazos' && <button className="admin-button" type="button" onClick={openCreate}><Plus size={16} />Nuevo</button>}
        </div>
      </div>
      <label className="admin-search"><Search size={16} /><input type="search" placeholder="Buscar en esta vista" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      {activeTab === 'nucleos' && (
        <div className="admin-filter-row" aria-label="Filtros de núcleos agrarios">
          <Field label="Proyecto">
            <select value={nucleoFilters.id_proyecto} onChange={(event) => updateNucleoFilter('id_proyecto', event.target.value)}>
              <option value="">Todos</option>
              {data.proyectos.filter((p) => p.activo).map((p) => (
                <option key={p.id_proyecto} value={p.id_proyecto}>{p.clave_proyecto} · {p.nombre_proyecto}</option>
              ))}
            </select>
          </Field>
          <Field label="Entidad federativa">
            <select value={nucleoFilters.id_entidad} onChange={(event) => updateNucleoFilter('id_entidad', event.target.value)}>
              <option value="">Todas</option>
              {data.entidades.map((entidad) => (
                <option key={entidad.id_entidad} value={entidad.id_entidad}>{entidad.nombre}</option>
              ))}
            </select>
          </Field>
          <Field label="Municipio">
            <select value={nucleoFilters.id_municipio} disabled={!nucleoFilters.id_entidad} onChange={(event) => updateNucleoFilter('id_municipio', event.target.value)}>
              <option value="">{nucleoFilters.id_entidad ? 'Todos' : 'Selecciona entidad'}</option>
              {filterMunicipios.map((municipio) => (
                <option key={municipio.id_municipio} value={municipio.id_municipio}>{municipio.nombre}</option>
              ))}
            </select>
          </Field>
        </div>
      )}
      {error && <div className="admin-error" role="alert">{error}</div>}
      {activeTab === 'trazos' && <section className="admin-form-band"><div className="admin-form-heading"><h2>Trazo oficial de derecho de vía</h2></div><Field label="Proyecto"><select value={trazoProjectId} onChange={(event) => setTrazoProjectId(event.target.value)}><option value="">Selecciona un proyecto</option>{data.proyectos.filter((item) => item.activo).map((item) => <option key={item.id_proyecto} value={item.id_proyecto}>{item.clave_proyecto} · {item.nombre_proyecto}</option>)}</select></Field>{trazoProjectId && <FranjaDerechoViaPanel idProyecto={Number(trazoProjectId)} onImportSuccess={load} />}</section>}
      {showForm && renderForm()}
      {activeTab === 'relaciones' && <TramoNucleoCandidates tramos={data.tramos} onChanged={load} />}
      {activeTab !== 'trazos' && <PaginatedTable
          columns={tableColumns}
          data={items}
          loading={loading}
          keyField={idKey}
          rowClassName={(item) => (!item.activo ? 'inactive' : '')}
        />}
      {reasonAction && <ReasonDialog title={reasonAction.item.activo ? 'Confirmar baja lógica' : 'Confirmar reactivación'} onCancel={() => setReasonAction(null)} onConfirm={confirmLifecycle} />}
      {assignmentTramo && <AssignmentDialog tramo={assignmentTramo} users={data.usuarios} onCancel={() => setAssignmentTramo(null)} onSaved={async () => { setAssignmentTramo(null); await load(); }} setPageError={setError} />}
      {sectionTramo && <SeccionDerechoViaPanel tramo={sectionTramo} onSaved={load} onClose={() => setSectionTramo(null)} />}
    </section>
  );
}
