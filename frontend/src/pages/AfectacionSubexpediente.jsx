import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, Banknote, Calendar, ClipboardList,
  FileClock, FileSignature, FileText, Loader2,
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
      const [subResponse, asambleasResponse, conveniosResponse] = await Promise.all([
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
      ]);
      setData(subResponse.data);
      setAsambleas(asambleasResponse.data);
      setConvenios(conveniosResponse.data);
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
          { key: 'asambleas', label: 'Asambleas', icon: Calendar },
          ...BASE_TABS,
        ]
      : BASE_TABS,
    [data?.afectacion?.tipo_afectacion],
  );

  const cicloOperativo = useMemo(() => {
    const ciclos = data?.estado?.ciclos || [];
    return ciclos.find((item) => item.tipo_ciclo === 'cop_original') || ciclos[0] || null;
  }, [data?.estado?.ciclos]);

  if (loading) {
    return (
      <div className="panel-loading">
        <Loader2 className="spin" /> Cargando subexpediente…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={errorBox}>
        <AlertCircle size={20} />
        {typeof error === 'string' ? error : 'Subexpediente no encontrado.'}
      </div>
    );
  }

  const { afectacion, tramo_nucleo: tramoNucleo, nucleo, estado } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <section style={headerStyle}>
        <button
          type="button"
          onClick={() => navigate(`/expedientes/${id_tramo_nucleo}`)}
          style={backButton}
        >
          <ArrowLeft size={15} /> Expediente maestro
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '18px', alignItems: 'flex-start' }}>
          <div>
            <div style={eyebrow}>SUBEXPEDIENTE #{afectacion.id_afectacion}</div>
            <h2 style={{ margin: '4px 0', fontSize: '24px', color: '#0f172a' }}>
              {nucleo.nombre_nucleo}
            </h2>
            <p style={{ color: '#64748b', margin: 0, fontSize: '14px' }}>
              {afectacion.tipo_afectacion} · Tramo {tramoNucleo.numero_tramo || '—'} · Expediente #{tramoNucleo.id_tramo_nucleo}
            </p>
          </div>
          <div style={statusGrid}>
            <StatusPill label="Liberación" value={estado.estado_liberacion} />
            <StatusPill label="Registral" value={estado.estado_registral} />
            <StatusPill label="Financiero" value={estado.estado_financiero} />
          </div>
        </div>
      </section>

      <section style={summaryStyle}>
        <SummaryItem label="Tipo de tenencia" value={afectacion.tipo_tenencia} />
        <SummaryItem label="Superficie" value={afectacion.superficie_afectada_ha ? `${afectacion.superficie_afectada_ha} ha` : '—'} />
        <SummaryItem label="Parcela" value={afectacion.id_parcela ? `#${afectacion.id_parcela}` : 'No aplica'} />
        <SummaryItem label="Salida terminal" value={afectacion.tipo_salida_terminal || 'No'} />
      </section>

      <section style={panelStyle}>
        <div role="tablist" aria-label="Secciones del subexpediente" style={tabListStyle}>
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

        <div style={{ padding: '24px' }}>
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
        items={asambleas}
        empty="No hay asambleas de esta afectación."
        render={(item) => (
          <>
            <strong>Asamblea #{item.id_asamblea} · {item.tipo_asamblea}</strong>
            <span>{item.estatus_asamblea} · {item.fecha_realizada || 'Sin fecha realizada'}</span>
          </>
        )}
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

function SimpleList({ items, empty, render }) {
  if (!items.length) return <div className="empty-state">{empty}</div>;
  return (
    <div className="record-list">
      {items.map((item) => (
        <article className="record-card" key={item.id_asamblea || item.id_convenio || item.id_actividad || item.id_documento}>
          {render(item)}
        </article>
      ))}
    </div>
  );
}

const headerStyle = {
  background: 'white',
  borderRadius: '12px',
  padding: '22px 28px',
  borderLeft: '5px solid #006341',
  boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
};
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
const statusGrid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(110px, 1fr))',
  gap: '10px',
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
const summaryStyle = {
  background: 'white',
  borderRadius: '12px',
  padding: '18px 24px',
  boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: '16px',
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
const panelStyle = {
  background: 'white',
  borderRadius: '12px',
  boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
  overflow: 'hidden',
};
const tabListStyle = {
  display: 'flex',
  overflowX: 'auto',
  borderBottom: '2px solid #f1f5f9',
  padding: '0 16px',
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
