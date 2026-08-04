import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, GitBranch, Loader2, Plus } from 'lucide-react';
import api from '../../api/axios';
import { Campo, ErrorBanner, ModalWrapper } from '../FormUI';
import { inputStyle } from '../formStyles';

const today = () => new Date().toISOString().slice(0, 10);

function errorText(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return detail?.message || 'No fue posible completar la operación.';
}

export default function FlujoLiberacionPanel({
  idTramoNucleo, idNucleo, idAfectacion = null, afectaciones, convenios,
  canWrite, onRefresh,
}) {
  const [activities, setActivities] = useState([]);
  const [tramites, setTramites] = useState([]);
  const [states, setStates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activityForm, setActivityForm] = useState(null);
  const [cycleForm, setCycleForm] = useState(null);
  const [terminalForm, setTerminalForm] = useState(null);
  const [fifonafeForm, setFifonafeForm] = useState(null);
  const scopedAfectaciones = useMemo(
    () => idAfectacion
      ? afectaciones.filter((item) => item.id_afectacion === Number(idAfectacion))
      : afectaciones,
    [afectaciones, idAfectacion],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [activityResponse, tramiteResponse, stateResponses] = await Promise.all([
        api.get('/actividades-campo', {
          params: {
            id_tramo_nucleo: idTramoNucleo,
            ...(idAfectacion ? { solo_compartidas: true } : {}),
          },
        }),
        api.get('/fifonafe', {
          params: {
            id_tramo_nucleo: idTramoNucleo,
            ...(idAfectacion ? { id_afectacion: idAfectacion } : {}),
          },
        }),
        Promise.all(scopedAfectaciones.map((item) => api.get(`/afectaciones/${item.id_afectacion}/estado`))),
      ]);
      setActivities(activityResponse.data);
      setTramites(tramiteResponse.data);
      setStates(stateResponses.map((response) => response.data));
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setLoading(false);
    }
  }, [idAfectacion, idTramoNucleo, scopedAfectaciones]);

  useEffect(() => { load(); }, [load]);

  const convenioMap = useMemo(
    () => Object.fromEntries(convenios.map((item) => [item.id_convenio, item])),
    [convenios],
  );

  const action = async (request) => {
    setError(null);
    try {
      await request();
      await load();
      onRefresh?.();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  if (loading) return <div className="panel-loading"><Loader2 className="spin" /> Cargando flujo…</div>;

  return (
    <div className="phase-panel">
      <ErrorBanner mensaje={error} />
      <header className="phase-panel-header">
        <div>
          <h3>Secuencia de liberación</h3>
          <p>Los estados y saldos se derivan en el servidor a partir de evidencia.</p>
        </div>
      </header>

      <section style={sectionStyle}>
        <div style={titleRow}>
          <div>
            <strong>Antecedentes compartidos</strong>
            <div style={hintStyle}>Sensibilización antes de caminamiento.</div>
          </div>
          {canWrite && <button className="button" type="button" onClick={() => setActivityForm(true)}><Plus size={15} /> Actividad</button>}
        </div>
        <div className="record-list">
          {activities.map((item) => (
            <article className="record-card" key={item.id_actividad}>
              <strong>{item.tipo_actividad}</strong>
              <span>{item.contexto_proceso} · {item.fecha_realizada ? `realizada ${item.fecha_realizada}` : 'pendiente'}</span>
            </article>
          ))}
          {activities.length === 0 && <div className="empty-state">Aún no hay actividades.</div>}
        </div>
      </section>

      {states.map((state) => {
        const affect = scopedAfectaciones.find((item) => item.id_afectacion === state.id_afectacion);
        return (
          <section key={state.id_afectacion} style={sectionStyle}>
            <div style={titleRow}>
              <div>
                <strong>Afectación #{state.id_afectacion} · {state.tipo_afectacion}</strong>
                <div style={hintStyle}>Liberación: {state.estado_liberacion} · Registral: {state.estado_registral} · Financiero: {state.estado_financiero}</div>
              </div>
              {state.estado_liberacion === 'liberada'
                ? <CheckCircle2 color="#059669" />
                : state.estado_terminal ? <AlertTriangle color="#b45309" /> : <GitBranch color="#2563eb" />}
            </div>

            <div className="record-list">
              {state.ciclos.map((cycle) => {
                const base = convenioMap[cycle.id_convenio];
                const cicloTramites = tramites.filter((item) => item.id_ciclo_afectacion === cycle.id_ciclo_afectacion);
                const informe = cicloTramites.find((item) => item.tipo_tramite === 'informe_no_conflictos');
                const indemnizacion = cicloTramites.find((item) => item.tipo_tramite === 'indemnizacion');
                return (
                  <article className="record-card" key={cycle.id_ciclo_afectacion}>
                    <header>
                      <div>
                        <strong>{cycle.tipo_ciclo} #{cycle.consecutivo}</strong>
                        <span>{cycle.estado_operativo} · {cycle.estado_registral} · {cycle.estado_financiero}</span>
                      </div>
                      <span className={cycle.estado_financiero === 'concluido' ? 'status success' : 'status'}>
                        {cycle.estado_financiero}
                      </span>
                    </header>
                    <div style={hintStyle}>
                      Límite: {cycle.limite_pagable ?? '—'} · Pagado: {cycle.total_pagado} · Saldo: {cycle.saldo_disponible}
                    </div>
                    {canWrite && !state.estado_terminal && (
                      <div style={actionRow}>
                        {base?.convenio_inscrito_fecha_ran && !informe && (
                          <button type="button" className="button secondary" onClick={() => setFifonafeForm({ mode: 'informe', cycle, base })}>Registrar no conflictos</button>
                        )}
                        {informe?.estatus === 'completo' && !indemnizacion && (
                          <button type="button" className="button secondary" onClick={() => setFifonafeForm({ mode: 'indemnizacion', cycle, base, informe })}>Abrir indemnización</button>
                        )}
                        {indemnizacion && indemnizacion.estatus !== 'completo' && (
                          <button type="button" className="button" onClick={() => setFifonafeForm({ mode: 'completar', cycle, tramite: indemnizacion })}>Completar indemnización</button>
                        )}
                        {cycle.estado_financiero === 'retiro_fondos_pendiente' && (
                          <button type="button" className="button" onClick={() => action(async () => {
                            const created = await api.post('/asambleas', {
                              id_nucleo: idNucleo,
                              id_tramo_nucleo: idTramoNucleo,
                              id_afectacion: state.id_afectacion,
                              id_ciclo_afectacion: cycle.id_ciclo_afectacion,
                              contexto_proceso: cycle.tipo_ciclo,
                              tipo_asamblea: 'retiro_fondos',
                              resultado_anuencia: 'no_aplica',
                              estatus_asamblea: 'pendiente',
                              fecha_realizada: today(),
                            });
                            await api.post(`/asambleas/${created.data.id_asamblea}/completar-retiro-fondos`, { confirmar: true });
                          })}>Completar retiro de fondos</button>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>

            {canWrite && !state.estado_terminal && state.estado_liberacion !== 'liberada' && (
              <div style={actionRow}>
                <button type="button" className="button secondary" onClick={() => setCycleForm(affect)}>Abrir ciclo posterior</button>
                <button type="button" className="button danger" onClick={() => setTerminalForm(affect)}>Registrar salida terminal</button>
              </div>
            )}
          </section>
        );
      })}

      {activityForm && <ActivityForm idTramoNucleo={idTramoNucleo} onClose={() => setActivityForm(null)} onSaved={() => { setActivityForm(null); load(); }} />}
      {cycleForm && <CycleForm affect={cycleForm} onClose={() => setCycleForm(null)} onSaved={() => { setCycleForm(null); load(); }} />}
      {terminalForm && <TerminalForm affect={terminalForm} onClose={() => setTerminalForm(null)} onSaved={() => { setTerminalForm(null); load(); onRefresh?.(); }} />}
      {fifonafeForm && <FifonafeForm data={fifonafeForm} idTramoNucleo={idTramoNucleo} onClose={() => setFifonafeForm(null)} onSaved={() => { setFifonafeForm(null); load(); }} />}
    </div>
  );
}

function ActivityForm({ idTramoNucleo, onClose, onSaved }) {
  const [form, setForm] = useState({ tipo_actividad: 'sensibilizacion', fecha_realizada: today() });
  const [error, setError] = useState(null);
  const submit = async (event) => {
    event.preventDefault();
    try {
      await api.post('/actividades-campo', { id_tramo_nucleo: idTramoNucleo, contexto_proceso: 'cop_original', ...form });
      onSaved();
    } catch (requestError) { setError(errorText(requestError)); }
  };
  return <ModalWrapper titulo="Registrar actividad" onClose={onClose} color="#2563eb"><form className="form-stack" onSubmit={submit}><ErrorBanner mensaje={error} /><Campo label="Actividad"><select style={inputStyle} value={form.tipo_actividad} onChange={(e) => setForm({ ...form, tipo_actividad: e.target.value })}><option value="sensibilizacion">Sensibilización</option><option value="caminamiento">Caminamiento</option></select></Campo><Campo label="Fecha realizada"><input required type="date" style={inputStyle} value={form.fecha_realizada} onChange={(e) => setForm({ ...form, fecha_realizada: e.target.value })} /></Campo><button className="button" type="submit">Guardar</button></form></ModalWrapper>;
}

function CycleForm({ affect, onClose, onSaved }) {
  const options = affect.tipo_afectacion === 'colectivo'
    ? ['superficie_adicional', 'obras_complementarias']
    : ['ampliacion', 'ampliacion_remanente'];
  const [tipo, setTipo] = useState(options[0]);
  const [error, setError] = useState(null);
  return <ModalWrapper titulo="Abrir ciclo posterior" onClose={onClose} color="#2563eb"><form className="form-stack" onSubmit={async (event) => { event.preventDefault(); try { await api.post(`/afectaciones/${affect.id_afectacion}/ciclos`, { tipo_ciclo: tipo }); onSaved(); } catch (requestError) { setError(errorText(requestError)); } }}><ErrorBanner mensaje={error} /><Campo label="Tipo de ciclo"><select style={inputStyle} value={tipo} onChange={(e) => setTipo(e.target.value)}>{options.map((item) => <option key={item}>{item}</option>)}</select></Campo><button className="button" type="submit">Abrir ciclo</button></form></ModalWrapper>;
}

function TerminalForm({ affect, onClose, onSaved }) {
  const [form, setForm] = useState({ tipo_salida_terminal: 'fuera_seguimiento_expropiacion', motivo: '' });
  const [error, setError] = useState(null);
  return <ModalWrapper titulo="Registrar salida terminal" onClose={onClose} color="#b45309"><form className="form-stack" onSubmit={async (event) => { event.preventDefault(); try { await api.put(`/afectaciones/${affect.id_afectacion}/salida-terminal`, { ...form, confirmar: true }); onSaved(); } catch (requestError) { setError(errorText(requestError)); } }}><ErrorBanner mensaje={error} /><Campo label="Salida"><select style={inputStyle} value={form.tipo_salida_terminal} onChange={(e) => setForm({ ...form, tipo_salida_terminal: e.target.value })}><option value="fuera_seguimiento_expropiacion">Expropiación directa</option><option value="fuera_seguimiento_comunidad_indigena">Comunidad indígena</option></select></Campo><Campo label="Motivo"><textarea required style={inputStyle} value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} /></Campo><button className="button danger" type="submit">Confirmar salida</button></form></ModalWrapper>;
}

function FifonafeForm({ data, idTramoNucleo, onClose, onSaved }) {
  const [error, setError] = useState(null);
  const [fields, setFields] = useState({
    no_oficio_fifonafe_a_dgaopr: '', no_oficio_dgaopr_a_repr: '',
    no_oficio_rpta_repr_a_dgaopr: '', no_oficio_rpta_dgaopr_a_fifonafe: '',
    fecha_oficio_fifonafe_a_dgaopr: today(), fecha_oficio_dgaopr_a_repr: today(),
    fecha_oficio_rpta_repr_a_dgaopr: today(), fecha_oficio_rpta_dgaopr_a_fifonafe: today(),
  });
  const submit = async (event) => {
    event.preventDefault();
    try {
      if (data.mode === 'informe') {
        await api.post('/fifonafe', { id_tramo_nucleo: idTramoNucleo, id_convenio: data.base.id_convenio, id_afectacion: data.cycle.id_afectacion, id_ciclo_afectacion: data.cycle.id_ciclo_afectacion, tipo_afectacion: data.cycle.tipo_afectacion, tipo_tramite: 'informe_no_conflictos', estatus: 'completo', hay_conflictos: false, ...fields });
      } else if (data.mode === 'indemnizacion') {
        await api.post('/fifonafe', { id_tramo_nucleo: idTramoNucleo, id_convenio: data.base.id_convenio, id_afectacion: data.cycle.id_afectacion, id_ciclo_afectacion: data.cycle.id_ciclo_afectacion, id_tramite_no_conflictos: data.informe.id_tramite_fifonafe, tipo_afectacion: data.cycle.tipo_afectacion, tipo_tramite: 'indemnizacion', estatus: 'pendiente' });
      } else {
        await api.put(`/fifonafe/${data.tramite.id_tramite_fifonafe}`, fields);
        await api.post(`/fifonafe/${data.tramite.id_tramite_fifonafe}/completar-indemnizacion`, { confirmar: true });
      }
      onSaved();
    } catch (requestError) { setError(errorText(requestError)); }
  };
  const needsFields = data.mode !== 'indemnizacion';
  return <ModalWrapper titulo={data.mode === 'informe' ? 'Informe de no conflictos' : data.mode === 'indemnizacion' ? 'Abrir indemnización' : 'Completar indemnización'} onClose={onClose} color="#059669"><form className="form-stack" onSubmit={submit}><ErrorBanner mensaje={error} />{needsFields && Object.entries(fields).map(([key, value]) => <Campo key={key} label={key.replaceAll('_', ' ')}><input required type={key.startsWith('fecha_') ? 'date' : 'text'} style={inputStyle} value={value} onChange={(e) => setFields({ ...fields, [key]: e.target.value })} /></Campo>)}<button className="button" type="submit">Confirmar</button></form></ModalWrapper>;
}

const sectionStyle = { border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px', marginBottom: '16px' };
const titleRow = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '12px' };
const actionRow = { display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' };
const hintStyle = { color: '#64748b', fontSize: '13px', marginTop: '4px' };
