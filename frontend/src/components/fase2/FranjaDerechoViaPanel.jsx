import React, { useState } from 'react';
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

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.name.endsWith('.geojson')) {
      setFile(selected);
      setError(null);
    } else {
      setFile(null);
      setError('Por favor, selecciona un archivo .geojson válido.');
    }
  };

  const handleImport = async () => {
    if (!file || !fuente || !fechaVigencia) {
      setError('Fuente, Fecha y Archivo son obligatorios.');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const content = JSON.parse(e.target.result);
          // Simplified validation before sending
          if (content.type === 'FeatureCollection' && content.features.length !== 1) {
             setError('El archivo debe estar consolidado en un único Feature (Polygon o MultiPolygon). No se admiten colecciones dispersas.');
             setLoading(false);
             return;
          }
          
          let wkt = '';
          // We will mock parsing GeoJSON to WKT for simplicity, relying on backend for strict checks
          // A robust app uses a library like 'wellknown' stringify, but here we expect the user to send valid GeoJSON 
          // that our backend API will actually parse.
          // Wait, backend expects `geometria_wkt: str` in the payload!
          // We need to convert GeoJSON to WKT. Let's use `wellknown`.
          let feature = content.type === 'FeatureCollection' ? content.features[0] : content;
          wkt = stringify(feature.geometry);
          
          if (!wkt) {
            setError('No se pudo extraer la geometría WKT.');
            setLoading(false);
            return;
          }

          const payload = {
            fuente,
            fecha_vigencia_inicio: fechaVigencia,
            geometria_wkt: wkt,
            ancho_izquierdo_m: anchoIzq ? parseFloat(anchoIzq) : null,
            ancho_derecho_m: anchoDer ? parseFloat(anchoDer) : null,
          };
          
          await api.post(`/tramos/${idTramo}/franjas/importar`, payload);
          setIsOpen(false);
          setFile(null);
          setFuente('');
          setFechaVigencia('');
          setAnchoIzq('');
          setAnchoDer('');
          if (onImportSuccess) onImportSuccess();
        } catch (err) {
          setError(err.response?.data?.detail || 'Error procesando el archivo.');
        } finally {
          setLoading(false);
        }
      };
      reader.readAsText(file);
    } catch (err) {
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
          border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', 
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
            background: 'white', padding: '25px', borderRadius: '12px', width: '400px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.1)', fontFamily: 'Inter, sans-serif'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '15px'}}>
              <h3 style={{margin: 0, color: '#0f172a'}}>Importar Franja GeoJSON</h3>
              <button onClick={() => setIsOpen(false)} style={{background: 'transparent', border: 'none', cursor: 'pointer'}}><X size={20}/></button>
            </div>
            
            <p style={{fontSize: '12px', color: '#64748b', marginBottom: '15px'}}>
              Cargue el polígono oficial consolidado (WGS84). Una vez aprobado, sustituirá a la versión actual.
            </p>

            {error && <div style={{background: '#fef2f2', color: '#b91c1c', padding: '10px', borderRadius: '6px', fontSize: '12px', marginBottom: '15px'}}>{error}</div>}

            <div style={{display: 'flex', flexDirection: 'column', gap: '12px'}}>
              <div>
                <label style={{fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '5px'}}>Fuente Documental *</label>
                <input type="text" value={fuente} onChange={e => setFuente(e.target.value)} style={{width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px'}} placeholder="Ej. Oficio SCT-2026-102" />
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
    </>
  );
}
