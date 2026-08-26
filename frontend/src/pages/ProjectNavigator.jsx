import React from 'react';
import { ArrowRight, Building2, MapPin, Plus } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api/axios';
import AuthContext from '../contexts/auth-context';
import { Empty, Field, Modal, Notice, PageHeader, SubmitBar } from '../components/TargetUI';
import { apiMessage } from '../utils/target';

export default function ProjectNavigator() {
  const { user } = React.useContext(AuthContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = React.useState([]);
  const [states, setStates] = React.useState([]);
  const [municipalities, setMunicipalities] = React.useState([]);
  const [nuclei, setNuclei] = React.useState([]);
  const [availableNuclei, setAvailableNuclei] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');
  const [showCreate, setShowCreate] = React.useState(false);
  const [projectModal, setProjectModal] = React.useState(null);
  const [saving, setSaving] = React.useState(false);
  const [form, setForm] = React.useState({ id_nucleo: '', residencia: '', responsable_nombre: '', contacto: '', referencia: '' });
  const projectId = Number(searchParams.get('id_proyecto')) || 0;
  const stateId = Number(searchParams.get('id_entidad')) || 0;
  const municipalityId = Number(searchParams.get('id_municipio')) || 0;
  const projectNucleusId = Number(searchParams.get('id_proyecto_nucleo')) || 0;
  const canCapture = ['admin', 'operador'].includes(user?.rol);

  React.useEffect(() => {
    Promise.all([api.get('/proyectos'), api.get('/catalogos/entidades')]).then(([projectResponse, stateResponse]) => {
      setProjects(projectResponse.data); setStates(stateResponse.data);
      if (!Number(new URLSearchParams(window.location.search).get('id_proyecto')) && projectResponse.data.length) setSearchParams({ id_proyecto: String(projectResponse.data[0].id_proyecto) }, { replace: true });
    }).catch((requestError) => setError(apiMessage(requestError))).finally(() => setLoading(false));
  }, [setSearchParams]);

  React.useEffect(() => {
    if (!stateId) { setMunicipalities([]); return; }
    api.get('/catalogos/municipios', { params: { id_entidad: stateId } }).then(({ data }) => setMunicipalities(data)).catch((requestError) => setError(apiMessage(requestError)));
  }, [stateId]);

  const loadNuclei = React.useCallback(async () => {
    if (!projectId) { setNuclei([]); return; }
    try {
      const params = {}; if (stateId) params.id_entidad = stateId; if (municipalityId) params.id_municipio = municipalityId;
      setNuclei((await api.get(`/proyectos/${projectId}/nucleos`, { params })).data); setError('');
    } catch (requestError) { setError(apiMessage(requestError)); }
  }, [municipalityId, projectId, stateId]);
  React.useEffect(() => { loadNuclei(); }, [loadNuclei]);

  const updateFilter = (key, value) => {
    const next = new URLSearchParams(searchParams); if (value) next.set(key, value); else next.delete(key);
    if (key === 'id_proyecto') { next.delete('id_entidad'); next.delete('id_municipio'); next.delete('id_proyecto_nucleo'); }
    if (key === 'id_entidad') { next.delete('id_municipio'); next.delete('id_proyecto_nucleo'); }
    if (key === 'id_municipio') next.delete('id_proyecto_nucleo');
    setSearchParams(next);
  };

  const openCreate = async () => {
    try {
      setAvailableNuclei((await api.get('/nucleos', { params: municipalityId ? { id_municipio: municipalityId, limit: 200 } : { limit: 200 } })).data);
      setShowCreate(true);
    } catch (requestError) { setError(apiMessage(requestError)); }
  };
  const create = async (event) => {
    event.preventDefault(); setSaving(true);
    const payload = { id_nucleo: Number(form.id_nucleo), residencia: form.residencia || null, responsable_nombre: form.responsable_nombre || null, contacto: form.contacto || null, referencias: form.referencia ? [{ tipo_referencia: 'consecutivo', valor: form.referencia, es_principal: true }] : [] };
    try { await api.post(`/proyectos/${projectId}/nucleos`, payload); setShowCreate(false); setForm({ id_nucleo: '', residencia: '', responsable_nombre: '', contacto: '', referencia: '' }); await loadNuclei(); }
    catch (requestError) { setError(apiMessage(requestError)); }
    finally { setSaving(false); }
  };

  return <section>
    <PageHeader eyebrow="Navegación territorial" title="Proyecto → Entidad → Municipio → Núcleo" description="El expediente canónico se forma por un proyecto y un núcleo agrario; las referencias históricas no lo duplican." action={<div className="record-actions">{user?.rol === 'admin' && <button className="button secondary" type="button" onClick={() => setProjectModal({})}><Plus />Nuevo proyecto</button>}{user?.rol === 'admin' && projectId > 0 && <button className="button secondary" type="button" onClick={() => setProjectModal(projects.find((item) => item.id_proyecto === projectId))}>Editar proyecto</button>}{canCapture && projectId ? <button className="button" type="button" onClick={openCreate}><Plus />Vincular núcleo</button> : null}</div>} />
    <Notice error={error} />
    <div className="hierarchy-filters">
      <Field label="Proyecto"><select aria-label="Proyecto" value={projectId || ''} onChange={(e) => updateFilter('id_proyecto', e.target.value)}><option value="">Selecciona</option>{projects.map((project) => <option key={project.id_proyecto} value={project.id_proyecto}>{project.nombre_proyecto}</option>)}</select></Field>
      <Field label="Entidad federativa"><select aria-label="Entidad federativa" value={stateId || ''} onChange={(e) => updateFilter('id_entidad', e.target.value)}><option value="">Todas</option>{states.map((state) => <option key={state.id_entidad} value={state.id_entidad}>{state.nombre}</option>)}</select></Field>
      <Field label="Municipio"><select aria-label="Municipio" disabled={!stateId} value={municipalityId || ''} onChange={(e) => updateFilter('id_municipio', e.target.value)}><option value="">Todos</option>{municipalities.map((municipality) => <option key={municipality.id_municipio} value={municipality.id_municipio}>{municipality.nombre}</option>)}</select></Field>
      <Field label="Núcleo agrario"><select aria-label="Núcleo agrario" disabled={!projectId} value={projectNucleusId || ''} onChange={(e) => updateFilter('id_proyecto_nucleo', e.target.value)}><option value="">Selecciona</option>{nuclei.map((record) => <option key={record.id_proyecto_nucleo} value={record.id_proyecto_nucleo}>{record.nombre_nucleo} · {record.tipo_nucleo}</option>)}</select></Field>
      <Field label="Expediente Proyecto · Núcleo"><Link className={`button ${projectNucleusId ? '' : 'disabled'}`} aria-disabled={!projectNucleusId} to={projectNucleusId ? `/proyecto-nucleo/${projectNucleusId}` : '#'}>Abrir expediente</Link></Field>
    </div>
    <div className="breadcrumb"><Building2 />{projects.find((item) => item.id_proyecto === projectId)?.nombre_proyecto || 'Proyecto'}<ArrowRight /><MapPin />{states.find((item) => item.id_entidad === stateId)?.nombre || 'Todas las entidades'}{municipalityId > 0 && <><ArrowRight />{municipalities.find((item) => item.id_municipio === municipalityId)?.nombre}</>}</div>
    {loading ? <div className="card">Cargando núcleos…</div> : nuclei.length === 0 ? <Empty title="Sin núcleos en el alcance seleccionado">Ajusta los filtros o vincula un núcleo existente al proyecto.</Empty> : <div className="nucleus-grid">{nuclei.filter((record) => !projectNucleusId || record.id_proyecto_nucleo === projectNucleusId).map((record) => <Link className="nucleus-card" to={`/proyecto-nucleo/${record.id_proyecto_nucleo}`} key={record.id_proyecto_nucleo}><div><span className="pill">{record.tipo_nucleo}</span><small>{record.entidad} · {record.municipio}</small></div><h3>{record.nombre_nucleo}</h3><p>Consecutivo / referencia principal: {record.consecutivo_principal || 'sin referencia'}</p><dl><div><dt>Afectaciones</dt><dd>{record.afectaciones_colectivas + record.afectaciones_individuales}</dd></div><div><dt>Convenios</dt><dd>{record.convenios}</dd></div><div><dt>Parcelas</dt><dd>{record.parcelas}</dd></div></dl><strong className="open-link">Abrir expediente <ArrowRight /></strong></Link>)}</div>}
    {showCreate && <Modal title="Vincular núcleo al proyecto" onClose={() => setShowCreate(false)}><form className="form-grid" onSubmit={create}><Field label="Núcleo agrario"><select required value={form.id_nucleo} onChange={(e) => setForm({ ...form, id_nucleo: e.target.value })}><option value="">Selecciona</option>{availableNuclei.map((item) => <option key={item.id_nucleo} value={item.id_nucleo}>{item.nombre_nucleo} · {item.tipo_nucleo}</option>)}</select></Field><Field label="Consecutivo de fuente"><input value={form.referencia} onChange={(e) => setForm({ ...form, referencia: e.target.value })} /></Field><Field label="Residencia"><input value={form.residencia} onChange={(e) => setForm({ ...form, residencia: e.target.value })} /></Field><Field label="Responsable"><input value={form.responsable_nombre} onChange={(e) => setForm({ ...form, responsable_nombre: e.target.value })} /></Field><Field label="Contacto"><input value={form.contacto} onChange={(e) => setForm({ ...form, contacto: e.target.value })} /></Field><SubmitBar saving={saving} onCancel={() => setShowCreate(false)} label="Crear expediente" /></form></Modal>}
    {projectModal && <ProjectForm current={projectModal.id_proyecto ? projectModal : null} onClose={() => setProjectModal(null)} onDone={async (record) => { setProjectModal(null); const response = await api.get('/proyectos'); setProjects(response.data); if (record?.id_proyecto) updateFilter('id_proyecto', String(record.id_proyecto)); }} />}
  </section>;
}

function ProjectForm({ current, onClose, onDone }) {
  const [form, setForm] = React.useState({ clave_proyecto: current?.clave_proyecto || '', nombre_proyecto: current?.nombre_proyecto || '', descripcion: current?.descripcion || '', fecha_inicio: current?.fecha_inicio || '', fecha_fin: current?.fecha_fin || '', observaciones: current?.observaciones || '' });
  const [saving, setSaving] = React.useState(false); const [error, setError] = React.useState('');
  const submit = async (event) => { event.preventDefault(); setSaving(true); setError(''); const payload = { ...form, descripcion: form.descripcion || null, fecha_inicio: form.fecha_inicio || null, fecha_fin: form.fecha_fin || null, observaciones: form.observaciones || null }; try { const response = current ? await api.patch(`/proyectos/${current.id_proyecto}`, { nombre_proyecto: payload.nombre_proyecto, descripcion: payload.descripcion, fecha_inicio: payload.fecha_inicio, fecha_fin: payload.fecha_fin, observaciones: payload.observaciones }) : await api.post('/proyectos', payload); await onDone(response.data); } catch (requestError) { setError(apiMessage(requestError)); } finally { setSaving(false); } };
  return <Modal title={current ? 'Editar proyecto' : 'Nuevo proyecto'} onClose={onClose}><form className="form-grid" onSubmit={submit}><Notice error={error} /><Field label="Clave"><input required disabled={Boolean(current)} value={form.clave_proyecto} onChange={(e) => setForm({ ...form, clave_proyecto: e.target.value })} /></Field><Field label="Nombre"><input required value={form.nombre_proyecto} onChange={(e) => setForm({ ...form, nombre_proyecto: e.target.value })} /></Field><Field label="Descripción"><textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></Field><Field label="Fecha de inicio"><input type="date" value={form.fecha_inicio} onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })} /></Field><Field label="Fecha de fin"><input type="date" value={form.fecha_fin} onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })} /></Field><Field label="Observaciones"><textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} /></Field><SubmitBar saving={saving} onCancel={onClose} /></form></Modal>;
}
