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
  canWrite, seguimientoPausado = false, motivoNoSeguimiento = null, onRefresh,
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
  const activityCycles = useMemo(
    () => states.flatMap((state) => state.ciclos)
      .filter((cycle) => ['superficie_adicional', 'obras_complementarias'].includes(cycle.tipo_ciclo)),
    [states],
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
          <h3>Investigación y seguimiento</h3>
          <p>Sensibilización, caminamiento, afectaciones, RAN, FIFONAFE y pagos se registran sólo cuando el expediente sigue en el flujo ordinario de la PA.</p>
        </div>
      </header>

      {seguimientoPausado && (
        <section style={{ ...sectionStyle, background: '#fff7ed', borderColor: '#fed7aa', color: '#9a3412' }}>
          <strong>Flujo ordinario detenido</strong>
          <div style={hintStyle}>Motivo: {motivoNoSeguimiento}. No se habilitan nuevas actividades, ciclos, trámites FIFONAFE ni salidas terminales de afectación.</div>
        </section>
      )}

      <section style={sectionStyle}>
        <div style={titleRow}>
          <div>
            <strong>Antecedentes compartidos</strong>
            <div style={hintStyle}>Sensibilización antes de caminamiento.</div>
          </div>
          {canWrite && !seguimientoPausado && <button className="button" type="button" onClick={() => setActivityForm(true)}><Plus size={15} /> Actividad</button>}
        </div>
        <div className="record-list">
          {activities.map((item) => (
            <article className="record-card" key={item.id_actividad}>
              <strong>{item.tipo_actividad}</strong>
              <span>
                {item.id_ciclo_afectacion ? `Ciclo ${item.contexto_proceso}` : 'Antecedente común'}
                {' · '}{item.fecha_programada ? `programada ${item.fecha_programada}` : 'sin programación'}
                {' · '}{item.fecha_realizada ? `realizada ${item.fecha_realizada}` : 'pendiente'}
              </span>
              {item.resultado && <p>{item.resultado}</p>}
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
                    {canWrite && !seguimientoPausado && !state.estado_terminal && (
                      <div style={actionRow}>
                        {base?.convenio_inscrito_fecha_ran && !informe && (
                          <button type="button" className="button secondary" onClick={() => setFifonafeForm({ mode: 'informe', cycle, base })}>Registrar no conflictos</button>
                        )}
                        {informe && (
                          <button type="button" className="button secondary" onClick={() => setFifonafeForm({ mode: 'informe', cycle, base, tramite: informe })}>Actualizar informe</button>
                        )}
                        {informe?.estatus === 'completo' && informe.hay_conflictos === false && !indemnizacion && (
                          <button type="button" className="button secondary" onClick={() => setFifonafeForm({ mode: 'indemnizacion', cycle, base, informe })}>Abrir indemnización</button>
                        )}
                        {indemnizacion && indemnizacion.estatus !== 'completo' && (
                          <button
                            type="button"
                            className="button"
                            onClick={() => setFifonafeForm({ mode: 'completar', cycle, tramite: indemnizacion })}
                            disabled={Number(cycle.saldo_disponible) > 0}
                            title={Number(cycle.saldo_disponible) > 0 ? `Saldo pendiente: $${cycle.saldo_disponible}` : ''}
                          >
                            Completar indemnización
                          </button>
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

            {canWrite && !seguimientoPausado && !state.estado_terminal && state.estado_liberacion !== 'liberada' && (
              <div style={actionRow}>
                <button type="button" className="button secondary" onClick={() => setCycleForm(affect)}>Abrir ciclo posterior</button>
                <button type="button" className="button danger" onClick={() => setTerminalForm(affect)}>Registrar salida terminal</button>
              </div>
            )}
          </section>
        );
      })}

      {activityForm && <ActivityForm idTramoNucleo={idTramoNucleo} cycles={activityCycles} onClose={() => setActivityForm(null)} onSaved={() => { setActivityForm(null); load(); }} />}
      {cycleForm && <CycleForm affect={cycleForm} onClose={() => setCycleForm(null)} onSaved={() => { setCycleForm(null); load(); }} />}
      {terminalForm && <TerminalForm affect={terminalForm} onClose={() => setTerminalForm(null)} onSaved={() => { setTerminalForm(null); load(); onRefresh?.(); }} />}
      {fifonafeForm && <FifonafeForm data={fifonafeForm} idTramoNucleo={idTramoNucleo} onClose={() => setFifonafeForm(null)} onSaved={() => { setFifonafeForm(null); load(); }} />}
    </div>
  );
}

function ActivityForm({ idTramoNucleo, cycles, onClose, onSaved }) {
  const [form, setForm] = useState({
    tipo_actividad: 'sensibilizacion',
    id_ciclo_afectacion: '',
    fecha_programada: '',
    fecha_realizada: '',
    resultado: '',
  });
  const [error, setError] = useState(null);
  const submit = async (event) => {
    event.preventDefault();
    try {
      const cycle = cycles.find((item) => item.id_ciclo_afectacion === Number(form.id_ciclo_afectacion));
      await api.post('/actividades-campo', {
        id_tramo_nucleo: idTramoNucleo,
        id_ciclo_afectacion: cycle?.id_ciclo_afectacion || null,
        contexto_proceso: cycle?.tipo_ciclo || 'cop_original',
        tipo_actividad: form.tipo_actividad,
        fecha_programada: form.fecha_programada || null,
        fecha_realizada: form.fecha_realizada || null,
        resultado: form.resultado || null,
      });
      onSaved();
    } catch (requestError) { setError(errorText(requestError)); }
  };
  return <ModalWrapper titulo="Registrar actividad" onClose={onClose} color="#2563eb"><form className="form-stack" onSubmit={submit}><ErrorBanner mensaje={error} /><Campo label="Actividad"><select style={inputStyle} value={form.tipo_actividad} onChange={(e) => setForm({ ...form, tipo_actividad: e.target.value })}><option value="sensibilizacion">Sensibilización</option><option value="caminamiento">Caminamiento</option></select></Campo><Campo label="Ámbito"><select style={inputStyle} value={form.id_ciclo_afectacion} onChange={(e) => setForm({ ...form, id_ciclo_afectacion: e.target.value })}><option value="">Antecedente común del expediente</option>{cycles.map((cycle) => <option key={cycle.id_ciclo_afectacion} value={cycle.id_ciclo_afectacion}>{cycle.tipo_ciclo} #{cycle.consecutivo}</option>)}</select></Campo><Campo label="Fecha programada"><input type="date" style={inputStyle} value={form.fecha_programada} onChange={(e) => setForm({ ...form, fecha_programada: e.target.value })} /></Campo><Campo label="Fecha realizada"><input type="date" min={form.fecha_programada} style={inputStyle} value={form.fecha_realizada} onChange={(e) => setForm({ ...form, fecha_realizada: e.target.value })} /></Campo><Campo label="Resultado"><textarea style={inputStyle} value={form.resultado} onChange={(e) => setForm({ ...form, resultado: e.target.value })} /></Campo><button className="button" type="submit">Guardar</button></form></ModalWrapper>;
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
    estatus: data.tramite?.estatus || 'programado',
    hay_conflictos: data.tramite?.hay_conflictos == null ? '' : String(data.tramite.hay_conflictos),
    no_oficio_fifonafe_a_dgaopr: data.tramite?.no_oficio_fifonafe_a_dgaopr || '',
    no_oficio_dgaopr_a_repr: data.tramite?.no_oficio_dgaopr_a_repr || '',
    no_oficio_rpta_repr_a_dgaopr: data.tramite?.no_oficio_rpta_repr_a_dgaopr || '',
    no_oficio_rpta_dgaopr_a_fifonafe: data.tramite?.no_oficio_rpta_dgaopr_a_fifonafe || '',
    fecha_oficio_fifonafe_a_dgaopr: data.tramite?.fecha_oficio_fifonafe_a_dgaopr || '',
    fecha_oficio_dgaopr_a_repr: data.tramite?.fecha_oficio_dgaopr_a_repr || '',
    fecha_oficio_rpta_repr_a_dgaopr: data.tramite?.fecha_oficio_rpta_repr_a_dgaopr || '',
    fecha_oficio_rpta_dgaopr_a_fifonafe: data.tramite?.fecha_oficio_rpta_dgaopr_a_fifonafe || '',
  });
  const submit = async (event) => {
    event.preventDefault();
    try {
      if (data.mode === 'informe') {
        const payload = Object.fromEntries(Object.entries(fields).map(([key, value]) => [
          key,
          key === 'hay_conflictos' ? (value === '' ? null : value === 'true') : (value || null),
        ]));
        if (data.tramite) await api.put(`/fifonafe/${data.tramite.id_tramite_fifonafe}`, payload);
        else await api.post('/fifonafe', { id_tramo_nucleo: idTramoNucleo, id_convenio: data.base.id_convenio, id_afectacion: data.cycle.id_afectacion, id_ciclo_afectacion: data.cycle.id_ciclo_afectacion, tipo_afectacion: data.cycle.tipo_afectacion, tipo_tramite: 'informe_no_conflictos', ...payload });
      } else if (data.mode === 'indemnizacion') {
        await api.post('/fifonafe', { id_tramo_nucleo: idTramoNucleo, id_convenio: data.base.id_convenio, id_afectacion: data.cycle.id_afectacion, id_ciclo_afectacion: data.cycle.id_ciclo_afectacion, id_tramite_no_conflictos: data.informe.id_tramite_fifonafe, tipo_afectacion: data.cycle.tipo_afectacion, tipo_tramite: 'indemnizacion', estatus: 'pendiente' });
      } else {
        await api.post(`/fifonafe/${data.tramite.id_tramite_fifonafe}/completar-indemnizacion`, { confirmar: true });
      }
      onSaved();
    } catch (requestError) { setError(errorText(requestError)); }
  };
  const complete = fields.estatus === 'completo';
  const labels = {
    no_oficio_fifonafe_a_dgaopr: 'Oficio FIFONAFE a DGAOPR',
    no_oficio_dgaopr_a_repr: 'Oficio DGAOPR a representación',
    no_oficio_rpta_repr_a_dgaopr: 'Respuesta de representación a DGAOPR',
    no_oficio_rpta_dgaopr_a_fifonafe: 'Respuesta DGAOPR a FIFONAFE',
    fecha_oficio_fifonafe_a_dgaopr: 'Fecha del oficio FIFONAFE a DGAOPR',
    fecha_oficio_dgaopr_a_repr: 'Fecha del oficio DGAOPR a representación',
    fecha_oficio_rpta_repr_a_dgaopr: 'Fecha de respuesta de representación',
    fecha_oficio_rpta_dgaopr_a_fifonafe: 'Fecha de respuesta DGAOPR a FIFONAFE',
  };
  const officeKeys = Object.keys(labels);
  return <ModalWrapper titulo={data.mode === 'informe' ? 'Informe de no conflictos' : data.mode === 'indemnizacion' ? 'Abrir indemnización' : 'Completar indemnización'} onClose={onClose} color="#059669"><form className="form-stack" onSubmit={submit}><ErrorBanner mensaje={error} />{data.mode === 'informe' && <><Campo label="Estatus"><select style={inputStyle} value={fields.estatus} onChange={(e) => setFields({ ...fields, estatus: e.target.value })}><option value="programado">Programado</option><option value="pendiente">Pendiente</option><option value="completo">Completo</option></select></Campo><Campo label="¿Se identificaron conflictos?"><select required={complete} style={inputStyle} value={fields.hay_conflictos} onChange={(e) => setFields({ ...fields, hay_conflictos: e.target.value })}><option value="">Sin determinar</option><option value="false">No</option><option value="true">Sí</option></select></Campo>{officeKeys.map((key) => <Campo key={key} label={labels[key]}><input required={complete} type={key.startsWith('fecha_') ? 'date' : 'text'} style={inputStyle} value={fields[key]} onChange={(e) => setFields({ ...fields, [key]: e.target.value })} /></Campo>)}</>}<button className="button" type="submit">Confirmar</button></form></ModalWrapper>;
}

const sectionStyle = { border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px', marginBottom: '16px' };
const titleRow = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '12px' };
const actionRow = { display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' };
const hintStyle = { color: '#64748b', fontSize: '13px', marginTop: '4px' };
