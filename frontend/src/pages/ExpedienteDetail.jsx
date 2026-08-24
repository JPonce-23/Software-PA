import React, { useState, useEffect, useContext, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, MapPin, FileText, ClipboardList,
  Loader2, AlertCircle, Building2, Layers, Calendar,
  Banknote, FileClock, FileSignature, FolderOpen, ShieldCheck,
} from 'lucide-react';
import api from '../api/axios';
import AuthContext from '../contexts/auth-context';
import FormAfectacionColectiva from './FormAfectacionColectiva';
import FormAfectacionIndividual from './FormAfectacionIndividual';
import FormAsamblea from './FormAsamblea';
import FormConvenio from './FormConvenio';

const OrvPanel = React.lazy(() => import('../components/fase2/OrvPanel'));
const PadronPanel = React.lazy(() => import('../components/fase2/PadronPanel'));
const MinutasPanel = React.lazy(() => import('../components/fase2/MinutasPanel'));
const PagosPanel = React.lazy(() => import('../components/fase2/PagosPanel'));
const DocumentosPanel = React.lazy(() => import('../components/fase2/DocumentosPanel'));
const FlujoLiberacionPanel = React.lazy(() => import('../components/fase2/FlujoLiberacionPanel'));

const TABS = [
  { key: 'general',     label: 'Datos generales',           icon: Building2 },
  { key: 'orv',          label: 'ORV y padrón',              icon: ShieldCheck },
  { key: 'flujo',       label: 'Investigación y seguimiento', icon: FileText },
  { key: 'afectaciones',label: 'Afectaciones',              icon: Layers },
  { key: 'asambleas',   label: 'Asambleas',                 icon: Calendar },
  { key: 'convenios',   label: 'Convenios',                 icon: FileSignature },
  { key: 'pagos',        label: 'FIFONAFE y pagos',          icon: Banknote },
  { key: 'minutas',      label: 'Minutas',                   icon: ClipboardList },
  { key: 'documentos',   label: 'Documentos',                icon: FileClock },
];

function tipoNucleoLabel(value) {
  if (value === 'ejido') return 'Ejido';
  if (value === 'comunidad') return 'Comunidad';
  return value || '—';
}

function ecLabel(value) {
  if (value === 'ejido') return 'E · Ejido';
  if (value === 'comunidad') return 'C · Comunidad';
  return '—';
}

function motivoFueraSeguimientoPA(tramoNucleo, nucleo) {
  if (tramoNucleo?.es_expropiacion) return 'Expropiación directa';
  if (nucleo?.comunidad_indigena || tramoNucleo?.comunidad_indigena) return 'Comunidad indígena';
  if (tramoNucleo?.proyecto_no_afecta_uso_comun) return 'El proyecto no afecta tierras de uso común';
  return null;
}

export default function ExpedienteDetail() {
  const { id_tramo_nucleo } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);

  const [tramoNucleo, setTramoNucleo]     = useState(null);
  const [nucleo, setNucleo]               = useState(null);
  const [afectaciones, setAfectaciones]   = useState([]);
  const [asambleas, setAsambleas]         = useState([]);
  const [convenios, setConvenios]         = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [tabActiva, setTabActiva]         = useState('general');
  const [modalColectiva, setModalColectiva]   = useState(false);
  const [modalIndividual, setModalIndividual] = useState(false);
  const [modalAsamblea, setModalAsamblea]     = useState(false);
  // modalConvenio guardará el objeto 'afectacion' que fue seleccionado para crearle el convenio
  const [modalConvenio, setModalConvenio]     = useState(null);

  // Función para refrescar solo las afectaciones (se llama tras guardar un formulario)
  const refrescarAfectaciones = useCallback(async () => {
    try {
      const res = await api.get(`/afectaciones?id_tramo_nucleo=${id_tramo_nucleo}`);
      setAfectaciones(res.data);
    } catch (err) {
      console.error('Error al refrescar afectaciones', err);
    }
  }, [id_tramo_nucleo]);

  const refrescarAsambleas = useCallback(async () => {
    try {
      const res = await api.get(`/asambleas?id_tramo_nucleo=${id_tramo_nucleo}`);
      setAsambleas(res.data);
    } catch (err) {
      console.error('Error al refrescar asambleas', err);
    }
  }, [id_tramo_nucleo]);

  const refrescarConvenios = useCallback(async () => {
    try {
      const res = await api.get(`/convenios?id_tramo_nucleo=${id_tramo_nucleo}`);
      setConvenios(res.data);
    } catch (err) {
      console.error('Error al refrescar convenios', err);
    }
  }, [id_tramo_nucleo]);

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const tnRes = await api.get(`/tramos-nucleos/${id_tramo_nucleo}`);
        setTramoNucleo(tnRes.data);

        const nRes = await api.get(`/nucleos/${tnRes.data.id_nucleo}`);
        setNucleo(nRes.data);

        const [afRes, asRes, convRes] = await Promise.all([
          api.get(`/afectaciones?id_tramo_nucleo=${id_tramo_nucleo}`),
          api.get(`/asambleas?id_tramo_nucleo=${id_tramo_nucleo}`),
          api.get(`/convenios?id_tramo_nucleo=${id_tramo_nucleo}`),
        ]);
        setAfectaciones(afRes.data);
        setAsambleas(asRes.data);
        setConvenios(convRes.data);
      } catch (err) {
        setError('No se pudo cargar el expediente. Verifique la conexión.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    cargarDatos();
  }, [id_tramo_nucleo]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', gap: '12px', color: '#64748b' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <span>Cargando expediente...</span>
      </div>
    );
  }

  if (error || !tramoNucleo) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', background: '#fef2f2', borderRadius: '12px', color: '#dc2626', border: '1px solid #fecaca', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
        <AlertCircle size={20} />
        {error || 'Expediente no encontrado.'}
      </div>
    );
  }

  const colectivas   = afectaciones.filter(a => a.tipo_afectacion === 'colectivo');
  const individuales = afectaciones.filter(a => a.tipo_afectacion === 'individual');
  const canWrite = user?.rol && ['admin', 'operador'].includes(user.rol);
  const motivoNoSeguimiento = motivoFueraSeguimientoPA(tramoNucleo, nucleo);
  const seguimientoPausado = Boolean(motivoNoSeguimiento);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Header del Expediente */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '24px 30px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', borderLeft: '5px solid #006341' }}>
        <button
          onClick={() => navigate('/expedientes')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '13px', marginBottom: '16px', padding: 0 }}
        >
          <ArrowLeft size={15} /> Volver a la lista
        </button>

        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ background: '#e0f0eb', padding: '14px', borderRadius: '12px', color: '#006341' }}>
              <MapPin size={28} />
            </div>
            <div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                EXPEDIENTE DEL NÚCLEO EN EL TRAMO
              </div>
              <h2 style={{ fontSize: '22px', color: '#0f172a', fontWeight: '700', margin: 0 }}>
                {nucleo?.nombre_nucleo || `Núcleo Agrario #${tramoNucleo.id_nucleo}`}
              </h2>
              <p style={{ color: '#64748b', fontSize: '14px', margin: '4px 0 0 0' }}>
                {ecLabel(nucleo?.tipo_nucleo)} · Tramo {tramoNucleo.numero_tramo || '—'} / Consecutivo {tramoNucleo.consecutivo || '—'}
              </p>
            </div>
          </div>

          {/* Contador de afectaciones */}
          <div style={{ display: 'flex', gap: '12px' }}>
            <StatBadge label="Colectivas" value={colectivas.length} color="#0284c7" bg="#e0f2fe" />
            <StatBadge label="Individuales" value={individuales.length} color="#d97706" bg="#fef3c7" />
            <StatBadge label="Asambleas" value={asambleas.length} color="#7c3aed" bg="#f3e8ff" />
          </div>
        </div>
        {seguimientoPausado && (
          <div style={{ marginTop: '18px', padding: '14px 16px', background: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <AlertCircle size={18} />
            <div>
              <strong>Sin seguimiento ordinario por parte de la PA</strong>
              <p style={{ margin: '4px 0 0', fontSize: '13px' }}>
                Motivo: {motivoNoSeguimiento}. Este caso no se marca como liberado y no debe continuar artificialmente con afectaciones, convenios, RAN, FIFONAFE o pagos.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Pestañas */}
      <div style={{ background: 'white', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
        <div role="tablist" aria-label="Secciones del expediente" style={{ display: 'flex', overflowX: 'auto', borderBottom: '2px solid #f1f5f9', padding: '0 16px' }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const activa = tabActiva === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activa}
                onClick={() => setTabActiva(tab.key)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: '16px 20px', display: 'flex', alignItems: 'center', gap: '8px',
                  fontSize: '14px', fontWeight: activa ? '600' : '400',
                  color: activa ? '#006341' : '#64748b',
                  borderBottom: activa ? '2px solid #006341' : '2px solid transparent',
                  marginBottom: '-2px', transition: 'all 0.2s',
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div role="tabpanel" style={{ padding: '30px' }}>
          {tabActiva === 'general'      && <TabGeneral tramoNucleo={tramoNucleo} nucleo={nucleo} motivoNoSeguimiento={motivoNoSeguimiento} />}
          {tabActiva === 'afectaciones' && (
            <TabAfectacionesUnificadas 
              colectivas={colectivas} 
              individuales={individuales} 
              convenios={convenios} 
              user={user} 
              onNuevaColectiva={() => setModalColectiva(true)} 
              onNuevaIndividual={() => setModalIndividual(true)} 
              onEditarColectiva={setModalColectiva} 
              onEditarIndividual={setModalIndividual} 
              onCrearConvenio={setModalConvenio} 
              onAbrir={(afectacion) => navigate(`/expedientes/${id_tramo_nucleo}/afectaciones/${afectacion.id_afectacion}`)} 
              seguimientoPausado={seguimientoPausado}
              motivoNoSeguimiento={motivoNoSeguimiento}
            />
          )}
          {tabActiva === 'asambleas'    && <TabAsambleas items={asambleas} user={user} onNueva={() => setModalAsamblea(true)} onEditar={setModalAsamblea} />}
          {tabActiva === 'convenios'    && (
            <TabConvenios
              items={convenios}
              afectaciones={afectaciones}
              user={user}
              onNuevo={(afectacion) => setModalConvenio(afectacion)}
              onEditar={(afectacion, convenio) => setModalConvenio({ afectacion, convenio, isEdit: true })}
              seguimientoPausado={seguimientoPausado}
              motivoNoSeguimiento={motivoNoSeguimiento}
            />
          )}
          <React.Suspense fallback={<div className="panel-loading"><Loader2 className="spin" /> Cargando módulo…</div>}>
            {tabActiva === 'flujo' && (
              <FlujoLiberacionPanel
                idTramoNucleo={Number(id_tramo_nucleo)}
                idNucleo={tramoNucleo.id_nucleo}
                afectaciones={afectaciones}
                convenios={convenios}
                canWrite={canWrite}
                seguimientoPausado={seguimientoPausado}
                motivoNoSeguimiento={motivoNoSeguimiento}
                onRefresh={() => {
                  refrescarAfectaciones();
                  refrescarAsambleas();
                  refrescarConvenios();
                }}
              />
            )}
            {tabActiva === 'orv' && (
              <div className="form-stack">
                <OrvPanel idNucleo={tramoNucleo.id_nucleo} canWrite={canWrite} />
                <PadronPanel idNucleo={tramoNucleo.id_nucleo} canWrite={canWrite} />
              </div>
            )}
            {tabActiva === 'minutas'       && <MinutasPanel idTramoNucleo={Number(id_tramo_nucleo)} canWrite={canWrite} />}
            {tabActiva === 'pagos'         && <PagosPanel idTramoNucleo={Number(id_tramo_nucleo)} canWrite={canWrite} />}
            {tabActiva === 'documentos'    && <DocumentosPanel idTramoNucleo={Number(id_tramo_nucleo)} canWrite={canWrite} />}
          </React.Suspense>

          {/* Modales de captura */}
          {modalColectiva && tramoNucleo && (
            <FormAfectacionColectiva
              idNucleo={tramoNucleo.id_nucleo}
              idTramoNucleo={Number(id_tramo_nucleo)}
              initialData={typeof modalColectiva === 'object' ? modalColectiva : null}
              onSuccess={refrescarAfectaciones}
              onClose={() => setModalColectiva(false)}
            />
          )}
          {modalIndividual && tramoNucleo && (
            <FormAfectacionIndividual
              idNucleo={tramoNucleo.id_nucleo}
              idTramoNucleo={Number(id_tramo_nucleo)}
              initialData={typeof modalIndividual === 'object' ? modalIndividual : null}
              onSuccess={refrescarAfectaciones}
              onClose={() => setModalIndividual(false)}
            />
          )}
          {modalAsamblea && tramoNucleo && (
            <FormAsamblea
              idNucleo={tramoNucleo.id_nucleo}
              idTramoNucleo={Number(id_tramo_nucleo)}
              afectaciones={afectaciones}
              initialData={typeof modalAsamblea === 'object' ? modalAsamblea : null}
              onSuccess={refrescarAsambleas}
              onClose={() => setModalAsamblea(false)}
            />
          )}
          {modalConvenio && tramoNucleo && (
            <FormConvenio
              idTramoNucleo={Number(id_tramo_nucleo)}
              afectacion={modalConvenio.afectacion || modalConvenio}
              initialData={modalConvenio.isEdit ? modalConvenio.convenio : null}
              asambleas={asambleas}
              convenios={convenios}
              onSuccess={() => {
                refrescarConvenios();
              }}
              onClose={() => setModalConvenio(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ────── Pestaña: Información General ────── */
function TabGeneral({ tramoNucleo, nucleo, motivoNoSeguimiento }) {
  const afectaUsoComun = !motivoNoSeguimiento;
  const campos = [
    { label: 'Entidad',           valor: nucleo?.entidad_nombre || '—' },
    { label: 'Municipio',         valor: nucleo?.municipio_nombre || '—' },
    { label: 'Residencia',        valor: nucleo?.residencia || '—' },
    { label: 'Núcleo agrario',    valor: nucleo?.nombre_nucleo || tramoNucleo.nombre_nucleo || '—' },
    { label: 'E/C',               valor: ecLabel(nucleo?.tipo_nucleo || tramoNucleo.tipo_nucleo) },
    { label: 'Tipo de núcleo',    valor: tipoNucleoLabel(nucleo?.tipo_nucleo || tramoNucleo.tipo_nucleo) },
    { label: 'Clave del tramo',   valor: tramoNucleo.nombre_tramo || '—' },
    { label: 'Número de tramo',   valor: tramoNucleo.numero_tramo || '—' },
    { label: 'Consecutivo',       valor: tramoNucleo.consecutivo || '—' },
    { label: 'Longitud del tramo',valor: tramoNucleo.longitud_m ? `${Number(tramoNucleo.longitud_m).toLocaleString()} m` : '—' },
    { label: '¿El proyecto afecta tierras de uso común?', valor: afectaUsoComun ? 'Sí' : 'No' },
    { label: 'Motivo sin seguimiento PA', valor: motivoNoSeguimiento || 'No aplica' },
    { label: 'Observaciones',     valor: tramoNucleo.observaciones || '—' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
      {campos.map(c => (
        <div key={c.label} style={{ background: '#f8fafc', borderRadius: '10px', padding: '16px 20px' }}>
          <div style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>{c.label}</div>
          <div style={{ fontSize: '15px', color: '#1e293b', fontWeight: '500' }}>{c.valor || '—'}</div>
        </div>
      ))}
    </div>
  );
}

/* ────── Pestaña: Afectaciones Unificadas ────── */
function TabAfectacionesUnificadas({ colectivas, individuales, convenios, user, onNuevaColectiva, onNuevaIndividual, onEditarColectiva, onEditarIndividual, onCrearConvenio, onAbrir, seguimientoPausado, motivoNoSeguimiento }) {
  const puedeCapturar = user?.rol && ['admin', 'operador'].includes(user.rol);
  const [filtro, setFiltro] = useState('todas');

  const items = useMemo(() => {
    const cols = colectivas.map(c => ({ ...c, _tipo: 'colectivo' }));
    const inds = individuales.map(i => ({ ...i, _tipo: 'individual' }));
    if (filtro === 'colectivas') return cols;
    if (filtro === 'individuales') return inds;
    return [...cols, ...inds].sort((a, b) => b.id_afectacion - a.id_afectacion);
  }, [colectivas, individuales, filtro]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h3 style={{ fontSize: '16px', color: '#1e293b', fontWeight: '600', margin: 0 }}>
            Afectaciones Registradas
            <span style={{ marginLeft: '10px', background: '#f1f5f9', color: '#475569', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', fontWeight: '400' }}>
              {items.length}
            </span>
          </h3>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#f8fafc', padding: '4px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            {[
              { id: 'todas', label: 'Todas' },
              { id: 'colectivas', label: 'Colectivas' },
              { id: 'individuales', label: 'Individuales' }
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setFiltro(f.id)}
                style={{
                  padding: '6px 12px', borderRadius: '6px', border: 'none',
                  background: filtro === f.id ? '#0f172a' : 'transparent',
                  color: filtro === f.id ? 'white' : '#64748b',
                  fontSize: '13px', fontWeight: '500', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {puedeCapturar && !seguimientoPausado && (
            <>
              <button
                style={{ background: '#006341', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontWeight: '500', fontSize: '13px' }}
                onClick={onNuevaColectiva}
              >
                + Colectiva
              </button>
              <button
                style={{ background: '#d97706', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontWeight: '500', fontSize: '13px' }}
                onClick={onNuevaIndividual}
              >
                + Individual
              </button>
            </>
          )}
        </div>
      </div>

      {items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px', border: '2px dashed #e2e8f0' }}>
          <FileText size={32} style={{ marginBottom: '10px', opacity: 0.4, display: 'block', margin: '0 auto 10px auto' }} />
          <p>{seguimientoPausado ? 'Este expediente no continúa con afectaciones dentro del seguimiento ordinario de la PA.' : 'No hay afectaciones registradas con este filtro.'}</p>
          {seguimientoPausado && <p style={{ fontSize: '13px', marginTop: '6px' }}>Motivo: {motivoNoSeguimiento}.</p>}
          {puedeCapturar && !seguimientoPausado && <p style={{ fontSize: '13px', marginTop: '6px' }}>Usa los botones superiores para registrar una nueva.</p>}
        </div>
      ) : (
        <div className="responsive-table">
        <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '10px', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Tipo</th>
              <th style={thStyle}>Tipo Tenencia</th>
              <th style={thStyle}>Parcela</th>
              <th style={thStyle}>Superficie (Ha)</th>
              <th style={thStyle}>Situación Jurídica</th>
              <th style={thStyle}>Convenios</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map(a => {
              const convs = convenios.filter(c => c.id_afectacion === a.id_afectacion);
              const hasConvenio = convs.length > 0;
              const esColectivo = a._tipo === 'colectivo';
              return (
              <tr key={a.id_afectacion} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={tdStyle}><span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px' }}>#{a.id_afectacion}</span></td>
                <td style={tdStyle}>
                  <span style={{ 
                    background: esColectivo ? '#ecfdf5' : '#fffbeb', 
                    color: esColectivo ? '#059669' : '#d97706', 
                    borderRadius: '12px', padding: '2px 8px', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase'
                  }}>
                    {esColectivo ? 'Colectiva' : 'Individual'}
                  </span>
                </td>
                <td style={tdStyle}>{a.tipo_tenencia || '—'}</td>
                <td style={tdStyle}>{!esColectivo && a.id_parcela ? `#${a.id_parcela}` : '—'}</td>
                <td style={tdStyle}>{a.superficie_afectada_ha ? `${a.superficie_afectada_ha} ha` : '—'}</td>
                <td style={tdStyle}>{a.situacion_juridica || '—'}</td>
                <td style={tdStyle}>
                  {hasConvenio ? (
                    <span style={{ background: '#ecfdf5', color: '#059669', borderRadius: '20px', padding: '4px 10px', fontSize: '12px', fontWeight: '500' }}>
                       {convs.length} Registrado(s)
                    </span>
                  ) : (
                    <span style={{ color: '#94a3b8', fontSize: '13px' }}>Ninguno</span>
                  )}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => onAbrir(a)}
                      style={{
                        background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe',
                        padding: '6px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: '600', cursor: 'pointer',
                        display: 'inline-flex', alignItems: 'center', gap: '6px',
                      }}
                    >
                      <FolderOpen size={14} /> Abrir
                    </button>
                    {puedeCapturar && !seguimientoPausado && (
                      <>
                      <button
                        onClick={() => esColectivo ? onEditarColectiva(a) : onEditarIndividual(a)}
                        style={{
                          background: 'white', color: '#64748b', border: '1px solid #e2e8f0', 
                          padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer',
                        }}
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => hasConvenio ? onCrearConvenio({ afectacion: a, convenio: convs[0], isEdit: true }) : onCrearConvenio(a)}
                        style={{
                          background: 'white', color: hasConvenio ? '#0ea5e9' : '#059669', border: `1px solid ${hasConvenio ? '#0ea5e9' : '#059669'}`, 
                          padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '600', cursor: 'pointer',
                        }}
                      >
                        {hasConvenio ? 'Editar Conv.' : '+ Convenio'}
                      </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )})}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}

/* ────── Pestaña: Asambleas ────── */
function TabAsambleas({ items, user, onNueva, onEditar }) {
  const puedeCapturar = user?.rol && ['admin', 'operador'].includes(user.rol);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '16px', color: '#1e293b', fontWeight: '600' }}>
          Asambleas
          <span style={{ marginLeft: '10px', background: '#f1f5f9', color: '#475569', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', fontWeight: '400' }}>
            {items.length} registros
          </span>
        </h3>
        {puedeCapturar && (
          <button
            style={{ background: '#7c3aed', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px' }}
            onClick={onNueva}
          >
            + Nueva Asamblea
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px', border: '2px dashed #e2e8f0' }}>
          <ClipboardList size={32} style={{ display: 'block', margin: '0 auto 10px auto', opacity: 0.4 }} />
          <p>No hay asambleas registradas para este expediente.</p>
          {puedeCapturar && <p style={{ fontSize: '13px', marginTop: '6px' }}>Usa el botón de arriba para registrar la primera asamblea.</p>}
        </div>
      ) : (
        <div className="responsive-table">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Tipo</th>
              <th style={thStyle}>Motivo</th>
              <th style={thStyle}>Resultado</th>
              <th style={thStyle}>Fecha Realizada</th>
              <th style={thStyle}>RAN</th>
              <th style={thStyle}>Documentación</th>
              <th style={thStyle}>Estatus</th>
              {puedeCapturar && <th style={{ ...thStyle, textAlign: 'right' }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {items.map(a => (
              <tr key={a.id_asamblea} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={tdStyle}><span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px' }}>#{a.id_asamblea}</span></td>
                <td style={tdStyle}>{a.tipo_asamblea || '—'}</td>
                <td style={tdStyle}>{a.contexto_proceso || '—'}</td>
                <td style={tdStyle}>{a.resultado_anuencia || '—'}</td>
                <td style={tdStyle}>{a.fecha_realizada || '—'}</td>
                <td style={tdStyle}>
                  Ingreso: {a.ingreso_ran_fecha || '—'}<br />
                  Solicitud: {a.numero_solicitud_ran || '—'}<br />
                  Inscripción acta: {a.acta_inscripcion_fecha_ran || '—'}
                </td>
                <td style={tdStyle}>{a.documentacion_disponible ? 'Disponible' : (a.documentacion_faltante || 'Pendiente')}</td>
                <td style={tdStyle}>
                  <span style={{ background: a.estatus_asamblea === 'completo' ? '#dcfce7' : '#fef3c7', color: a.estatus_asamblea === 'completo' ? '#16a34a' : '#d97706', borderRadius: '20px', padding: '3px 10px', fontSize: '12px' }}>
                    {a.estatus_asamblea || '—'}
                  </span>
                </td>
                {puedeCapturar && (
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    <button
                      onClick={() => onEditar(a)}
                      style={{
                        background: 'white', color: '#64748b', border: '1px solid #e2e8f0', 
                        padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer',
                      }}
                    >
                      Editar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}

/* ────── Pestaña: Convenios ────── */
function TabConvenios({ items, afectaciones, user, onNuevo, onEditar, seguimientoPausado, motivoNoSeguimiento }) {
  const puedeCapturar = user?.rol && ['admin', 'operador'].includes(user.rol);
  const [selectedId, setSelectedId] = useState(String(afectaciones[0]?.id_afectacion || ''));
  const afectacionMap = useMemo(
    () => Object.fromEntries(afectaciones.map((item) => [item.id_afectacion, item])),
    [afectaciones],
  );
  const selectedAfectacion = afectacionMap[Number(selectedId)];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <h3 style={{ fontSize: '16px', color: '#1e293b', fontWeight: '600', margin: 0 }}>
          Convenios
          <span style={{ marginLeft: '10px', background: '#f1f5f9', color: '#475569', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', fontWeight: '400' }}>
            {items.length} registros
          </span>
        </h3>
        {puedeCapturar && !seguimientoPausado && afectaciones.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
              style={{ border: '1px solid #cbd5e1', borderRadius: '8px', padding: '8px 10px', fontSize: '13px' }}
            >
              {afectaciones.map((item) => (
                <option key={item.id_afectacion} value={item.id_afectacion}>
                  Afectación #{item.id_afectacion} · {item.tipo_afectacion}
                </option>
              ))}
            </select>
            <button
              type="button"
              style={{ background: '#059669', color: 'white', border: 'none', padding: '9px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: '600', fontSize: '13px' }}
              disabled={!selectedAfectacion}
              onClick={() => onNuevo(selectedAfectacion)}
            >
              + Nuevo convenio
            </button>
          </div>
        )}
      </div>
      {seguimientoPausado && (
        <div style={{ padding: '14px 16px', background: '#fff7ed', color: '#9a3412', border: '1px solid #fed7aa', borderRadius: '8px' }}>
          Sin captura de convenios por seguimiento PA detenido. Motivo: {motivoNoSeguimiento}.
        </div>
      )}
      {items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px', border: '2px dashed #e2e8f0' }}>
          <FileSignature size={32} style={{ display: 'block', margin: '0 auto 10px auto', opacity: 0.4 }} />
          <p>No hay convenios registrados para este expediente.</p>
        </div>
      ) : (
        <div className="responsive-table">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Tipo de convenio</th>
              <th style={thStyle}>Afectación</th>
              <th style={thStyle}>Firma</th>
              <th style={thStyle}>Superficie</th>
              <th style={thStyle}>Montos</th>
              <th style={thStyle}>RAN</th>
              <th style={thStyle}>Documentación</th>
              {puedeCapturar && <th style={{ ...thStyle, textAlign: 'right' }}>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((convenio) => {
              const afectacion = afectacionMap[convenio.id_afectacion];
              const superficie = convenio.superficie_total_ha
                || convenio.superficie_real_afectada_ha
                || convenio.superficie_adicional_ha
                || convenio.superficie_ampliacion_ha;
              return (
                <tr key={convenio.id_convenio} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={tdStyle}><span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px' }}>#{convenio.id_convenio}</span></td>
                  <td style={tdStyle}>{convenio.tipo_convenio || '—'}</td>
                  <td style={tdStyle}>#{convenio.id_afectacion} · {afectacion?.tipo_afectacion || convenio.tipo_afectacion || '—'}</td>
                  <td style={tdStyle}>{convenio.fecha_firma || '—'}</td>
                  <td style={tdStyle}>{superficie ? `${superficie} ha` : '—'}</td>
                  <td style={tdStyle}>
                    100%: {convenio.monto_100 || '—'}<br />
                    90%: {convenio.monto_90 || '—'}<br />
                    BDT: {convenio.monto_bdt || '—'}
                  </td>
                  <td style={tdStyle}>
                    Ingreso: {convenio.ingreso_ran_fecha || '—'}<br />
                    Solicitud: {convenio.numero_solicitud_ingreso || '—'}<br />
                    Inscripción: {convenio.convenio_inscrito_fecha_ran || '—'}
                  </td>
                  <td style={tdStyle}>{convenio.documentacion_disponible ? 'Disponible' : (convenio.documentacion_faltante || 'Pendiente')}</td>
                  {puedeCapturar && (
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      <button
                        type="button"
                        onClick={() => onEditar(afectacion || convenio, convenio)}
                        style={{ background: 'white', color: '#64748b', border: '1px solid #e2e8f0', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: '500', cursor: 'pointer' }}
                      >
                        Editar
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}

/* ────── Componente auxiliar: Estadística badge ────── */
function StatBadge({ label, value, color, bg }) {
  return (
    <div style={{ textAlign: 'center', background: bg, borderRadius: '10px', padding: '12px 20px', minWidth: '90px' }}>
      <div style={{ fontSize: '24px', fontWeight: '700', color }}>{value}</div>
      <div style={{ fontSize: '11px', color, opacity: 0.8, marginTop: '2px' }}>{label}</div>
    </div>
  );
}

const thStyle = {
  textAlign: 'left', padding: '12px 16px', fontSize: '12px',
  fontWeight: '600', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px',
};

const tdStyle = {
  padding: '14px 16px', fontSize: '14px', color: '#334155',
};
