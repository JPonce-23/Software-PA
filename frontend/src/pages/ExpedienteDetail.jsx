import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Users, FileText, ClipboardList,
  Loader2, AlertCircle, Building2, Layers, Calendar
} from 'lucide-react';
import api from '../api/axios';
import { AuthContext } from '../contexts/AuthContext';
import FormAfectacionColectiva from './FormAfectacionColectiva';
import FormAfectacionIndividual from './FormAfectacionIndividual';

const TABS = [
  { key: 'general',     label: 'Información General',       icon: Building2 },
  { key: 'colectivas',  label: 'Afectaciones Colectivas',   icon: Layers },
  { key: 'individuales',label: 'Afectaciones Individuales', icon: Users },
  { key: 'asambleas',   label: 'Asambleas',                 icon: Calendar },
];

export default function ExpedienteDetail() {
  const { id_tramo_nucleo } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);

  const [tramoNucleo, setTramoNucleo]     = useState(null);
  const [nucleo, setNucleo]               = useState(null);
  const [afectaciones, setAfectaciones]   = useState([]);
  const [asambleas, setAsambleas]         = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [tabActiva, setTabActiva]         = useState('general');
  const [modalColectiva, setModalColectiva]   = useState(false);
  const [modalIndividual, setModalIndividual] = useState(false);

  // Función para refrescar solo las afectaciones (se llama tras guardar un formulario)
  const refrescarAfectaciones = useCallback(async () => {
    try {
      const res = await api.get(`/afectaciones?id_tramo_nucleo=${id_tramo_nucleo}`);
      setAfectaciones(res.data);
    } catch (err) {
      console.error('Error al refrescar afectaciones', err);
    }
  }, [id_tramo_nucleo]);

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const tnRes = await api.get(`/tramos-nucleos/${id_tramo_nucleo}`);
        setTramoNucleo(tnRes.data);

        const nRes = await api.get(`/nucleos/${tnRes.data.id_nucleo}`);
        setNucleo(nRes.data);

        const [afRes, asRes] = await Promise.all([
          api.get(`/afectaciones?id_tramo_nucleo=${id_tramo_nucleo}`),
          api.get(`/asambleas?id_tramo_nucleo=${id_tramo_nucleo}`),
        ]);
        setAfectaciones(afRes.data);
        setAsambleas(asRes.data);
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
                EXPEDIENTE #{id_tramo_nucleo}
              </div>
              <h2 style={{ fontSize: '22px', color: '#0f172a', fontWeight: '700', margin: 0 }}>
                {nucleo?.nombre_nucleo || `Núcleo Agrario #${tramoNucleo.id_nucleo}`}
              </h2>
              <p style={{ color: '#64748b', fontSize: '14px', margin: '4px 0 0 0' }}>
                {nucleo?.tipo_nucleo || 'Ejido'} — Tramo {tramoNucleo.numero_tramo || '—'} / Consecutivo {tramoNucleo.consecutivo || '—'}
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
      </div>

      {/* Pestañas */}
      <div style={{ background: 'white', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '2px solid #f1f5f9', padding: '0 16px' }}>
          {TABS.map(tab => {
            const Icon = tab.icon;
            const activa = tabActiva === tab.key;
            return (
              <button
                key={tab.key}
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

        <div style={{ padding: '30px' }}>
          {tabActiva === 'general'      && <TabGeneral tramoNucleo={tramoNucleo} nucleo={nucleo} />}
          {tabActiva === 'colectivas'   && <TabAfectaciones tipo="colectivo" items={colectivas} user={user} onNueva={() => setModalColectiva(true)} />}
          {tabActiva === 'individuales' && <TabAfectaciones tipo="individual" items={individuales} user={user} onNueva={() => setModalIndividual(true)} />}
          {tabActiva === 'asambleas'    && <TabAsambleas items={asambleas} />}

          {/* Modales de captura */}
          {modalColectiva && tramoNucleo && (
            <FormAfectacionColectiva
              idNucleo={tramoNucleo.id_nucleo}
              idTramoNucleo={Number(id_tramo_nucleo)}
              onSuccess={refrescarAfectaciones}
              onClose={() => setModalColectiva(false)}
            />
          )}
          {modalIndividual && tramoNucleo && (
            <FormAfectacionIndividual
              idNucleo={tramoNucleo.id_nucleo}
              idTramoNucleo={Number(id_tramo_nucleo)}
              onSuccess={refrescarAfectaciones}
              onClose={() => setModalIndividual(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ────── Pestaña: Información General ────── */
function TabGeneral({ tramoNucleo, nucleo }) {
  const campos = [
    { label: 'Municipio',         valor: nucleo?.municipio },
    { label: 'Entidad',           valor: nucleo?.entidad },
    { label: 'Tipo de Núcleo',    valor: nucleo?.tipo_nucleo },
    { label: 'Longitud del tramo',valor: tramoNucleo.longitud_m ? `${Number(tramoNucleo.longitud_m).toLocaleString()} m` : '—' },
    { label: '¿Es Expropiación?', valor: tramoNucleo.es_expropiacion ? 'Sí' : 'No' },
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

/* ────── Pestaña: Afectaciones (Colectivas o Individuales) ────── */
function TabAfectaciones({ tipo, items, user, onNueva }) {
  const esColectivo = tipo === 'colectivo';
  const puedeCapturar = user?.rol && ['admin', 'operador', 'geografo'].includes(user.rol);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '16px', color: '#1e293b', fontWeight: '600' }}>
          Afectaciones {esColectivo ? 'Colectivas' : 'Individuales'}
          <span style={{ marginLeft: '10px', background: '#f1f5f9', color: '#475569', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', fontWeight: '400' }}>
            {items.length} registros
          </span>
        </h3>
        {puedeCapturar && (
          <button
            style={{ background: esColectivo ? '#006341' : '#d97706', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px' }}
            onClick={onNueva}
          >
            + Nueva Afectación {esColectivo ? 'Colectiva' : 'Individual'}
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px', border: '2px dashed #e2e8f0' }}>
          <FileText size={32} style={{ marginBottom: '10px', opacity: 0.4, display: 'block', margin: '0 auto 10px auto' }} />
          <p>No hay afectaciones {esColectivo ? 'colectivas' : 'individuales'} registradas.</p>
          {puedeCapturar && <p style={{ fontSize: '13px', marginTop: '6px' }}>Usa el botón de arriba para agregar la primera.</p>}
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: '10px', overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Tipo Tenencia</th>
              {!esColectivo && <th style={thStyle}>Parcela</th>}
              <th style={thStyle}>Superficie (Ha)</th>
              <th style={thStyle}>Situación Jurídica</th>
              <th style={thStyle}>Documentación</th>
            </tr>
          </thead>
          <tbody>
            {items.map(a => (
              <tr key={a.id_afectacion} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={tdStyle}><span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px' }}>#{a.id_afectacion}</span></td>
                <td style={tdStyle}>{a.tipo_tenencia || '—'}</td>
                {!esColectivo && <td style={tdStyle}>#{a.id_parcela || '—'}</td>}
                <td style={tdStyle}>{a.superficie_afectada_ha ? `${a.superficie_afectada_ha} ha` : '—'}</td>
                <td style={tdStyle}>{a.situacion_juridica || '—'}</td>
                <td style={tdStyle}>
                  <span style={{ background: a.documentacion_disponible ? '#dcfce7' : '#fef9c3', color: a.documentacion_disponible ? '#16a34a' : '#92400e', borderRadius: '20px', padding: '3px 10px', fontSize: '12px' }}>
                    {a.documentacion_disponible ? 'Disponible' : 'Pendiente'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ────── Pestaña: Asambleas ────── */
function TabAsambleas({ items }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 style={{ fontSize: '16px', color: '#1e293b', fontWeight: '600' }}>
        Asambleas
        <span style={{ marginLeft: '10px', background: '#f1f5f9', color: '#475569', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', fontWeight: '400' }}>
          {items.length} registros
        </span>
      </h3>
      {items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px', border: '2px dashed #e2e8f0' }}>
          <ClipboardList size={32} style={{ display: 'block', margin: '0 auto 10px auto', opacity: 0.4 }} />
          <p>No hay asambleas registradas para este expediente.</p>
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Tipo</th>
              <th style={thStyle}>Resultado</th>
              <th style={thStyle}>Fecha Realizada</th>
              <th style={thStyle}>Estatus</th>
            </tr>
          </thead>
          <tbody>
            {items.map(a => (
              <tr key={a.id_asamblea} style={{ borderBottom: '1px solid #f1f5f9' }}>
                <td style={tdStyle}><span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px' }}>#{a.id_asamblea}</span></td>
                <td style={tdStyle}>{a.tipo_asamblea || '—'}</td>
                <td style={tdStyle}>{a.resultado_anuencia || '—'}</td>
                <td style={tdStyle}>{a.fecha_realizada || '—'}</td>
                <td style={tdStyle}>
                  <span style={{ background: a.estatus_asamblea === 'completo' ? '#dcfce7' : '#fef3c7', color: a.estatus_asamblea === 'completo' ? '#16a34a' : '#d97706', borderRadius: '20px', padding: '3px 10px', fontSize: '12px' }}>
                    {a.estatus_asamblea || '—'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
