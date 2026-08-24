import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, Banknote, Calendar, ClipboardList,
  FileClock, FileSignature, FileText, Loader2,
  Layers,
} from 'lucide-react';
import api from '../api/axios';
import AuthContext from '../contexts/auth-context';
import FormAsamblea from './FormAsamblea';
import FormConvenio from './FormConvenio';

const DocumentosPanel = React.lazy(() => import('../components/fase2/DocumentosPanel'));
const FlujoLiberacionPanel = React.lazy(() => import('../components/fase2/FlujoLiberacionPanel'));
const MinutasPanel = React.lazy(() => import('../components/fase2/MinutasPanel'));
const PagosPanel = React.lazy(() => import('../components/fase2/PagosPanel'));

const BASE_TABS = [
  { key: 'flujo', label: 'Flujo', icon: FileText },
  { key: 'ciclos', label: 'Ciclo', icon: Layers },
  { key: 'convenios', label: 'Convenios', icon: FileSignature },
  { key: 'pagos', label: 'Pagos', icon: Banknote },
  { key: 'minutas', label: 'Minutas', icon: ClipboardList },
  { key: 'documentos', label: 'Documentos', icon: FileClock },
  { key: 'antecedentes', label: 'Antecedentes', icon: Calendar },
];

export default function AfectacionSubexpediente() {
  const { id_tramo_nucleo, id_afectacion } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [data, setData] = useState(null);
  const [asambleas, setAsambleas] = useState([]);
  const [convenios, setConvenios] = useState([]);
  const [ciclos, setCiclos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('flujo');
  const [modalAsamblea, setModalAsamblea] = useState(false);
  const [modalConvenio, setModalConvenio] = useState(null);

  const canWrite = user?.rol && ['admin', 'operador'].includes(user.rol);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [subResponse, asambleasResponse, conveniosResponse, ciclosResponse] = await Promise.all([
        api.get(`/tramos-nucleos/${id_tramo_nucleo}/afectaciones/${id_afectacion}/subexpediente`),
        api.get('/asambleas', {
          params: {
            id_tramo_nucleo: id_tramo_nucleo,
            id_afectacion: id_afectacion,
          },
        }),
        api.get('/convenios', {
          params: {
            id_tramo_nucleo: id_tramo_nucleo,
            id_afectacion: id_afectacion,
          },
        }),
        api.get(`/afectaciones/${id_afectacion}/ciclos`),
      ]);
      setData(subResponse.data);
      setAsambleas(asambleasResponse.data);
      setConvenios(conveniosResponse.data);
      setCiclos(ciclosResponse.data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No se pudo cargar el subexpediente.');
    } finally {
      setLoading(false);
    }
  }, [id_afectacion, id_tramo_nucleo]);

  useEffect(() => { load(); }, [load]);

  const tabs = useMemo(
    () => data?.afectacion?.tipo_afectacion === 'colectivo'
      ? [
          BASE_TABS[0],
          BASE_TABS[1],
          { key: 'asambleas', label: 'Asambleas', icon: Calendar },
          ...BASE_TABS.slice(2),
        ]
      : BASE_TABS,
    [data?.afectacion?.tipo_afectacion],
  );

  const cicloOperativo = useMemo(() => {
    return ciclos.find((item) => item.tipo_ciclo === 'cop_original') || ciclos[0] || null;
  }, [ciclos]);

  if (loading) {
    return (
      <div className="panel-loading">
        <Loader2 className="spin" /> Cargando afectación…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={errorBox}>
        <AlertCircle size={20} />
        {typeof error === 'string' ? error : 'Afectación no encontrada.'}
      </div>
    );
  }

  const { afectacion, tramo_nucleo: tramoNucleo, nucleo, estado } = data;

  return (
    <div className="affectation-page">
      <section className="affectation-header">
        <button
          type="button"
          onClick={() => navigate(`/expedientes/${id_tramo_nucleo}`)}
          style={backButton}
        >
          <ArrowLeft size={15} /> Expediente del núcleo
        </button>
        <div className="affectation-header-content">
          <div className="affectation-heading">
            <div style={eyebrow}>AFECTACIÓN #{afectacion.id_afectacion}</div>
            <h2 style={{ margin: '4px 0', fontSize: '24px', color: '#0f172a' }}>
              {nucleo.nombre_nucleo}
            </h2>
            <p style={{ color: '#64748b', margin: 0, fontSize: '14px' }}>
              {afectacion.tipo_afectacion} · Tramo {tramoNucleo.numero_tramo || '—'} · Expediente #{tramoNucleo.id_tramo_nucleo}
            </p>
          </div>
          <div className="affectation-status-grid">
            <StatusPill label="Liberación" value={estado.estado_liberacion} />
            <StatusPill label="Registral" value={estado.estado_registral} />
            <StatusPill label="Financiero" value={estado.estado_financiero} />
          </div>
        </div>
      </section>

      <section className="affectation-summary">
        <SummaryItem label="Tipo de tenencia" value={afectacion.tipo_tenencia} />
        <SummaryItem label="Superficie" value={afectacion.superficie_afectada_ha ? `${afectacion.superficie_afectada_ha} ha` : '—'} />
        <SummaryItem label="Parcela" value={afectacion.id_parcela ? `#${afectacion.id_parcela}` : 'No aplica'} />
        <SummaryItem label="Salida terminal" value={afectacion.tipo_salida_terminal || 'No'} />
      </section>

      <section className="affectation-panel">
        <div role="tablist" aria-label="Secciones de la afectación" className="affectation-tabs">
          {tabs.map((item) => {
            const Icon = item.icon;
            const active = tab === item.key;
            return (
              <button
                key={item.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setTab(item.key)}
                style={{
                  ...tabButtonStyle,
                  color: active ? '#006341' : '#64748b',
                  borderBottomColor: active ? '#006341' : 'transparent',
                  fontWeight: active ? 700 : 500,
                }}
              >
                <Icon size={16} /> {item.label}
              </button>
            );
          })}
        </div>

        <div className="affectation-panel-body">
          <React.Suspense fallback={<div className="panel-loading"><Loader2 className="spin" /> Cargando módulo…</div>}>
            {tab === 'flujo' && (
              <FlujoLiberacionPanel
                idTramoNucleo={Number(id_tramo_nucleo)}
                idNucleo={nucleo.id_nucleo}
                idAfectacion={Number(id_afectacion)}
                afectaciones={[afectacion]}
                convenios={convenios}
                canWrite={canWrite}
                onRefresh={load}
              />
            )}
            {tab === 'asambleas' && afectacion.tipo_afectacion === 'colectivo' && (
              <AsambleasSection
                asambleas={asambleas}
                canWrite={canWrite}
                onNueva={() => setModalAsamblea(true)}
              />
            )}
            {tab === 'ciclos' && (
              <CiclosSection
                ciclos={ciclos}
                estadoCiclos={estado.ciclos || []}
                canWrite={canWrite}
                idAfectacion={Number(id_afectacion)}
                onSaved={load}
              />
            )}
            {tab === 'convenios' && (
              <ConveniosSection
                convenios={convenios}
                canWrite={canWrite}
                onNuevo={() => setModalConvenio({ afectacion })}
                onEditar={(convenio) => setModalConvenio({ afectacion, convenio, isEdit: true })}
              />
            )}
            {tab === 'pagos' && (
              <PagosPanel
                idTramoNucleo={Number(id_tramo_nucleo)}
                idAfectacion={Number(id_afectacion)}
                canWrite={canWrite}
              />
            )}
            {tab === 'minutas' && (
              <MinutasPanel
                idTramoNucleo={Number(id_tramo_nucleo)}
                idAfectacion={Number(id_afectacion)}
                idCicloAfectacion={cicloOperativo?.id_ciclo_afectacion || null}
                canWrite={canWrite}
                title="Minutas propias"
                emptyText="No hay minutas propias de esta afectación."
              />
            )}
            {tab === 'documentos' && (
              <DocumentosPanel
                entidadTipo="afectacion"
                entidadId={Number(id_afectacion)}
                canWrite={canWrite}
                title="Documentos de la afectación"
                emptyText="No hay documentos propios de esta afectación."
              />
            )}
            {tab === 'antecedentes' && (
              <AntecedentesSection
                antecedentes={data.antecedentes_compartidos}
                documentos={data.documentos_maestros}
              />
            )}
          </React.Suspense>
        </div>
      </section>

      {modalAsamblea && (
        <FormAsamblea
          idNucleo={nucleo.id_nucleo}
          idTramoNucleo={Number(id_tramo_nucleo)}
          afectaciones={[afectacion]}
          onSuccess={load}
          onClose={() => setModalAsamblea(false)}
        />
      )}
      {modalConvenio && (
        <FormConvenio
          idTramoNucleo={Number(id_tramo_nucleo)}
          afectacion={modalConvenio.afectacion}
          initialData={modalConvenio.isEdit ? modalConvenio.convenio : null}
          asambleas={asambleas}
          convenios={convenios}
          onSuccess={load}
          onClose={() => setModalConvenio(null)}
        />
      )}
    </div>
  );
}

function StatusPill({ label, value }) {
  return (
    <div style={statusPill}>
      <span>{label}</span>
      <strong>{value || '—'}</strong>
    </div>
  );
}

function SummaryItem({ label, value }) {
  return (
    <div>
      <span style={summaryLabel}>{label}</span>
      <strong style={summaryValue}>{value || '—'}</strong>
    </div>
  );
}

function AsambleasSection({ asambleas, canWrite, onNueva }) {
  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Asambleas de la afectación</h3>
          <p>Solo se listan asambleas vinculadas a este subexpediente.</p>
        </div>
        {canWrite && <button type="button" className="button" onClick={onNueva}>Nueva asamblea</button>}
      </header>
      <SimpleList
        idKey="id_asamblea"
        items={asambleas}
        empty="No hay asambleas de esta afectación."
        render={(item) => (
          <>
            <strong>Asamblea #{item.id_asamblea} · {item.tipo_asamblea}</strong>
            <span>Motivo: {item.contexto_proceso || '—'} · {item.estatus_asamblea} · {item.fecha_realizada || 'Sin fecha realizada'}</span>
            <span>RAN: ingreso {item.ingreso_ran_fecha || '—'} · solicitud {item.numero_solicitud_ran || '—'} · inscripción acta {item.acta_inscripcion_fecha_ran || '—'}</span>
            <span>Documentación: {item.documentacion_disponible ? 'disponible' : (item.documentacion_faltante || 'pendiente')}</span>
          </>
        )}
      />
    </div>
  );
}

function CiclosSection({ ciclos, estadoCiclos, canWrite, idAfectacion, onSaved }) {
  const [editingId, setEditingId] = useState(null);
  const [observaciones, setObservaciones] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const estadoMap = useMemo(
    () => Object.fromEntries(estadoCiclos.map((item) => [item.id_ciclo_afectacion, item])),
    [estadoCiclos],
  );

  const guardar = async (ciclo) => {
    setSaving(true);
    setError(null);
    try {
      await api.put(`/afectaciones/${idAfectacion}/ciclos/${ciclo.id_ciclo_afectacion}`, {
        observaciones: observaciones || null,
      });
      setEditingId(null);
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible guardar el ciclo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Ciclo de la afectación</h3>
          <p>Consulta el ciclo operativo, su estado y las observaciones existentes.</p>
        </div>
      </header>
      {error && <div className="error-banner">{typeof error === 'string' ? error : JSON.stringify(error)}</div>}
      <SimpleList
        idKey="id_ciclo_afectacion"
        items={ciclos}
        empty="No hay ciclos registrados para esta afectación."
        render={(item) => {
          const estado = estadoMap[item.id_ciclo_afectacion] || {};
          const editing = editingId === item.id_ciclo_afectacion;
          return (
            <>
              <strong>Ciclo #{item.id_ciclo_afectacion} · {item.tipo_ciclo} #{item.consecutivo}</strong>
              <span>Tipo de afectación: {item.tipo_afectacion}</span>
              <span>Operativo: {estado.estado_operativo || '—'} · Registral: {estado.estado_registral || '—'} · Financiero: {estado.estado_financiero || '—'}</span>
              <span>Superficie base: {item.superficie_base_ciclo_ha || '—'} ha · Superficie ciclo: {estado.superficie_ciclo_ha || '—'} ha</span>
              <span>Límite pagable: {estado.limite_pagable || '—'} · Pagado: {estado.total_pagado || '—'} · Saldo: {estado.saldo_disponible || '—'}</span>
              {editing ? (
                <div className="form-stack">
                  <textarea
                    value={observaciones}
                    onChange={(event) => setObservaciones(event.target.value)}
                    rows={3}
                    style={{ width: '100%', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '10px' }}
                  />
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button type="button" className="button secondary compact" onClick={() => setEditingId(null)}>
                      Cancelar
                    </button>
                    <button type="button" className="button compact" disabled={saving} onClick={() => guardar(item)}>
                      {saving && <Loader2 size={14} className="spin" />} Guardar
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <span>Observaciones: {item.observaciones || '—'}</span>
                  {canWrite && (
                    <button
                      type="button"
                      className="button secondary compact"
                      onClick={() => {
                        setEditingId(item.id_ciclo_afectacion);
                        setObservaciones(item.observaciones || '');
                      }}
                    >
                      Editar observaciones
                    </button>
                  )}
                </>
              )}
            </>
          );
        }}
      />
    </div>
  );
}

function ConveniosSection({ convenios, canWrite, onNuevo, onEditar }) {
  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Convenios de la afectación</h3>
          <p>COP, modificatorios y variantes del subexpediente.</p>
        </div>
        {canWrite && <button type="button" className="button" onClick={onNuevo}>Nuevo convenio</button>}
      </header>
      <SimpleList
        idKey="id_convenio"
        items={convenios}
        empty="No hay convenios de esta afectación."
        render={(item) => (
          <>
            <strong>Convenio #{item.id_convenio} · {item.tipo_convenio}</strong>
            <span>Firma {item.fecha_firma || '—'} · RAN {item.convenio_inscrito_fecha_ran || 'pendiente'}</span>
            {canWrite && (
              <button type="button" className="button secondary compact" onClick={() => onEditar(item)}>
                Editar
              </button>
            )}
          </>
        )}
      />
    </div>
  );
}

function AntecedentesSection({ antecedentes, documentos }) {
  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Antecedentes compartidos</h3>
          <p>Sensibilización, caminamiento y documentos maestros visibles como contexto.</p>
        </div>
      </header>
      <SimpleList
        idKey="id_actividad"
        items={antecedentes}
        empty="No hay antecedentes compartidos registrados."
        render={(item) => (
          <>
            <strong>{item.tipo_actividad}</strong>
            <span>{item.contexto_proceso} · {item.fecha_realizada || item.fecha_programada || 'Sin fecha'}</span>
          </>
        )}
      />
      <h4 style={{ margin: '20px 0 10px', color: '#334155' }}>Documentos maestros</h4>
      <SimpleList
        idKey="id_documento"
        items={documentos}
        empty="No hay documentos maestros registrados."
        render={(item) => (
          <>
            <strong>{item.tipo_documento}</strong>
            <span>{item.categoria}{item.es_critico ? ' · Crítico' : ''}</span>
          </>
        )}
      />
    </div>
  );
}

function SimpleList({ items, idKey, empty, render }) {
  if (!items.length) return <div className="empty-state">{empty}</div>;
  return (
    <div className="record-list">
      {items.map((item) => (
        <article className="record-card" key={item[idKey]}>
          {render(item)}
        </article>
      ))}
    </div>
  );
}

const backButton = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  color: '#64748b',
  fontSize: '13px',
  marginBottom: '14px',
  padding: 0,
};
const eyebrow = {
  fontSize: '12px',
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '1px',
};
const statusPill = {
  background: '#f8fafc',
  border: '1px solid #e2e8f0',
  borderRadius: '10px',
  padding: '10px 12px',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  fontSize: '12px',
  color: '#64748b',
};
const summaryLabel = {
  color: '#94a3b8',
  display: 'block',
  fontSize: '12px',
  textTransform: 'uppercase',
  marginBottom: '4px',
};
const summaryValue = {
  color: '#1e293b',
  fontSize: '15px',
};
const tabButtonStyle = {
  background: 'none',
  border: 'none',
  borderBottom: '2px solid transparent',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  fontSize: '14px',
  marginBottom: '-2px',
  padding: '16px 18px',
};
const errorBox = {
  padding: '40px',
  textAlign: 'center',
  background: '#fef2f2',
  borderRadius: '12px',
  color: '#dc2626',
  border: '1px solid #fecaca',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '10px',
};
