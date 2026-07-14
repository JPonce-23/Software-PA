import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, FolderOpen, MapPin, ChevronRight, Loader2 } from 'lucide-react';
import api from '../api/axios';

export default function ExpedientesList() {
  const navigate = useNavigate();
  const [tramosNucleos, setTramosNucleos] = useState([]);
  const [nucleosMap, setNucleosMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const [tramosRes, nucleosRes] = await Promise.all([
          api.get('/tramos-nucleos'),
          api.get('/nucleos'),
        ]);
        setTramosNucleos(tramosRes.data);

        // Crear mapa id_nucleo → nombre para mostrar en la tabla
        const mapa = {};
        nucleosRes.data.forEach(n => {
          mapa[n.id_nucleo] = n.nombre_nucleo || `Núcleo #${n.id_nucleo}`;
        });
        setNucleosMap(mapa);
      } catch (err) {
        setError('No se pudo cargar la lista de expedientes. Verifique la conexión con el servidor.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    cargarDatos();
  }, []);

  const filtrados = tramosNucleos.filter(tn => {
    const nombre = nucleosMap[tn.id_nucleo] || '';
    const tramo = String(tn.numero_tramo || '');
    const consec = String(tn.consecutivo || '');
    const termino = busqueda.toLowerCase();
    return (
      nombre.toLowerCase().includes(termino) ||
      tramo.toLowerCase().includes(termino) ||
      consec.toLowerCase().includes(termino) ||
      String(tn.id_tramo_nucleo).includes(termino)
    );
  });

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', gap: '12px', color: '#64748b' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <span>Cargando expedientes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', background: '#fef2f2', borderRadius: '12px', color: '#dc2626', border: '1px solid #fecaca' }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Barra superior */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'white', padding: '16px 24px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#006341', fontWeight: '600', fontSize: '16px' }}>
          <FolderOpen size={20} />
          Expedientes de Ejidos y Comunidades
          <span style={{ background: '#e0f0eb', color: '#006341', borderRadius: '20px', padding: '2px 10px', fontSize: '13px' }}>
            {filtrados.length} expedientes
          </span>
        </div>

        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={17} color="#888" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Buscar por ejido, tramo o consecutivo..."
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            style={{ width: '100%', padding: '10px 14px 10px 40px', borderRadius: '20px', border: '1px solid #ddd', outline: 'none', fontSize: '14px' }}
          />
        </div>
      </div>

      {/* Tabla de expedientes */}
      <div style={{ background: 'white', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
        {filtrados.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center', color: '#94a3b8' }}>
            <FolderOpen size={40} style={{ marginBottom: '12px', opacity: 0.4, display: 'block', margin: '0 auto 12px auto' }} />
            <p style={{ fontSize: '16px' }}>No se encontraron expedientes</p>
            <p style={{ fontSize: '13px', marginTop: '6px' }}>
              {busqueda ? 'Intenta con otro término de búsqueda.' : 'No hay expedientes registrados aún.'}
            </p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
                <th style={thStyle}>ID</th>
                <th style={thStyle}>Núcleo Agrario</th>
                <th style={thStyle}>No. Tramo</th>
                <th style={thStyle}>Consecutivo</th>
                <th style={thStyle}>Longitud</th>
                <th style={thStyle}>Estatus</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((tn, i) => (
                <ExpedienteRow
                  key={tn.id_tramo_nucleo}
                  tn={tn}
                  nombre={nucleosMap[tn.id_nucleo] || `Núcleo #${tn.id_nucleo}`}
                  index={i}
                  onClick={() => navigate(`/expedientes/${tn.id_tramo_nucleo}`)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ExpedienteRow({ tn, nombre, index, onClick }) {
  const [hovered, setHovered] = useState(false);
  return (
    <tr
      onClick={onClick}
      style={{
        borderBottom: '1px solid #f1f5f9',
        cursor: 'pointer',
        transition: 'background 0.15s',
        background: hovered ? '#f0fdf4' : (index % 2 === 0 ? 'white' : '#fafafa'),
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <td style={tdStyle}>
        <span style={{ background: '#f1f5f9', color: '#475569', borderRadius: '6px', padding: '3px 8px', fontSize: '12px', fontWeight: '600' }}>
          #{tn.id_tramo_nucleo}
        </span>
      </td>
      <td style={tdStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ background: '#e0f0eb', padding: '6px', borderRadius: '8px', color: '#006341', flexShrink: 0 }}>
            <MapPin size={14} />
          </div>
          <span style={{ fontWeight: '500', color: '#1e293b' }}>{nombre}</span>
        </div>
      </td>
      <td style={tdStyle}>{tn.numero_tramo || '—'}</td>
      <td style={tdStyle}>{tn.consecutivo || '—'}</td>
      <td style={tdStyle}>{tn.longitud_m ? `${Number(tn.longitud_m).toLocaleString()} m` : '—'}</td>
      <td style={tdStyle}>
        <span style={{
          background: tn.activo ? '#dcfce7' : '#fee2e2',
          color: tn.activo ? '#16a34a' : '#dc2626',
          borderRadius: '20px', padding: '3px 10px', fontSize: '12px', fontWeight: '500'
        }}>
          {tn.activo ? 'Activo' : 'Inactivo'}
        </span>
      </td>
      <td style={{ ...tdStyle, textAlign: 'right' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end', color: '#006341', fontWeight: '500', fontSize: '13px' }}>
          Abrir expediente
          <ChevronRight size={16} />
        </div>
      </td>
    </tr>
  );
}

const thStyle = {
  textAlign: 'left',
  padding: '14px 20px',
  fontSize: '12px',
  fontWeight: '600',
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const tdStyle = {
  padding: '16px 20px',
  fontSize: '14px',
  color: '#334155',
};
