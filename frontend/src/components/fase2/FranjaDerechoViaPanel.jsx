import React, { useCallback, useEffect, useState } from 'react';
import api from '../../api/axios';
import { Upload, X, Check } from 'lucide-react';
import { stringify } from 'wellknown';

export default function FranjaDerechoViaPanel({ idTramo, onImportSuccess }) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [fuente, setFuente] = useState('');
  const [fechaVigencia, setFechaVigencia] = useState('');
  const [anchoIzq, setAnchoIzq] = useState('');
  const [anchoDer, setAnchoDer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [franjas, setFranjas] = useState([]);

  const loadFranjas = useCallback(async () => {
    try {
      const { data } = await api.get(`/tramos/${idTramo}/franjas`);
      setFranjas(data);
    } catch {
      setFranjas([]);
    }
  }, [idTramo]);

  useEffect(() => {
    loadFranjas();
  }, [loadFranjas]);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.name.toLowerCase().endsWith('.geojson')) {
      setFile(selected);
      setError(null);
    } else {
      setFile(null);
      setError('Por favor, selecciona un archivo .geojson válido.');
    }
  };

  const handleImport = async () => {
    if (!file || !fuente.trim() || !fechaVigencia) {
      setError('Fuente, Fecha y Archivo son obligatorios.');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const reader = new FileReader();
      reader.onerror = () => {
        setError('Error al leer el archivo.');
        setLoading(false);
      };
      reader.onload = async (e) => {
        try {
          const content = JSON.parse(e.target.result);
          if (content.type === 'FeatureCollection') {
            setError('FeatureCollection no está permitido para una franja.');
            return;
          }

          const geometry = content.type === 'Feature' ? content.geometry : content;
          if (!geometry || !['Polygon', 'MultiPolygon'].includes(geometry.type)) {
            setError('La franja debe ser Polygon o MultiPolygon.');
            return;
          }
          const wkt = stringify(geometry);
          
          if (!wkt) {
            setError('No se pudo extraer la geometría WKT.');
            setLoading(false);
            return;
          }

          const payload = {
            fuente: fuente.trim(),
            fecha_vigencia_inicio: fechaVigencia,
            geometria_wkt: wkt,
            ancho_izquierdo_m: anchoIzq || null,
            ancho_derecho_m: anchoDer || null,
          };
          
          await api.post(`/tramos/${idTramo}/franjas/importar`, payload);
          setIsOpen(false);
          setFile(null);
          setFuente('');
          setFechaVigencia('');
          setAnchoIzq('');
          setAnchoDer('');
          await loadFranjas();
          if (onImportSuccess) onImportSuccess();
        } catch (err) {
          const detail = err.response?.data?.detail;
          if (typeof detail === 'string') {
            setError(detail);
          } else if (Array.isArray(detail)) {
            setError(detail.map((item) => item.msg).filter(Boolean).join('\n') || 'Datos de franja inválidos.');
          } else {
            setError('Error procesando el archivo.');
          }
        } finally {
          setLoading(false);
        }
      };
      reader.readAsText(file);
    } catch {
      setError('Error al leer el archivo.');
      setLoading(false);
    }
  };

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        style={{
          width: '100%', padding: '10px', background: '#0284c7', color: 'white', 
          border: 'none', borderRadius: '6px', cursor: 'pointer', display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: '8px',
          marginTop: '15px'
        }}
      >
        <Upload size={18} />
        Importar Nueva Franja
      </button>

      {isOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            background: 'white', padding: '25px', borderRadius: '8px', width: 'min(400px, calc(100vw - 32px))',
            boxShadow: '0 10px 25px rgba(0,0,0,0.1)', fontFamily: 'Inter, sans-serif'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '15px'}}>
              <h3 style={{margin: 0, color: '#0f172a'}}>Importar Franja GeoJSON</h3>
              <button onClick={() => setIsOpen(false)} style={{background: 'transparent', border: 'none', cursor: 'pointer'}}><X size={20}/></button>
            </div>
            
            {error && <div style={{background: '#fef2f2', color: '#b91c1c', padding: '10px', borderRadius: '6px', fontSize: '12px', marginBottom: '15px'}}>{error}</div>}

            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              <div>
                <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Fuente Documental *</label>
                <input type="text" maxLength={200} value={fuente} onChange={e => setFuente(e.target.value)} style={{width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px'}} placeholder="Ej. Oficio SCT-2026-102" />
              </div>
              <div>
                <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Fecha Vigencia *</label>
                <input type="date" value={fechaVigencia} onChange={e => setFechaVigencia(e.target.value)} style={{width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px'}} />
              </div>
              <div style={{display: 'flex', gap: '10px'}}>
                <div style={{flex: 1}}>
                  <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Ancho Izq (Opcional)</label>
                  <input type="number" step="0.01" value={anchoIzq} onChange={e => setAnchoIzq(e.target.value)} style={{width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px'}} placeholder="m" />
                </div>
                <div style={{flex: 1}}>
                  <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Ancho Der (Opcional)</label>
                  <input type="number" step="0.01" value={anchoDer} onChange={e => setAnchoDer(e.target.value)} style={{width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px'}} placeholder="m" />
                </div>
              </div>
              <div>
                <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Archivo .geojson *</label>
                <input type="file" accept=".geojson" onChange={handleFileChange} style={{fontSize: '12px'}} />
              </div>
            </div>

            <button 
              onClick={handleImport}
              disabled={loading}
              style={{
                width: '100%', padding: '10px', background: loading ? '#94a3b8' : '#22c55e', color: 'white', 
                border: 'none', borderRadius: '8px', cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', 
                alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '20px'
              }}
            >
              <Check size={18} />
              {loading ? 'Procesando...' : 'Confirmar Importación'}
            </button>
          </div>
        </div>
      )}
      {franjas.length > 0 && (
        <div style={{ marginTop: '10px', fontSize: '12px', color: '#475569' }}>
          {franjas.slice(0, 3).map((franja) => (
            <div key={franja.id_franja} style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', padding: '4px 0' }}>
              <span>Versión {franja.version}</span>
              <span>{franja.activo ? 'Activa' : 'Histórica'}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
