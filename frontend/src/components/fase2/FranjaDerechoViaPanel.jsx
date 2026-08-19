import React, { useCallback, useEffect, useState } from 'react';
import { Check, Upload, X } from 'lucide-react';
import api from '../../api/axios';
import GeospatialUpload from '../GeospatialUpload';

export default function FranjaDerechoViaPanel({ idProyecto, onImportSuccess }) {
  const [isOpen, setIsOpen] = useState(false);
  const [fechaVigencia, setFechaVigencia] = useState('');
  const [featureId, setFeatureId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [franjas, setFranjas] = useState([]);

  const loadFranjas = useCallback(async () => {
    try {
      const { data } = await api.get(`/proyectos/${idProyecto}/franjas`);
      setFranjas(data);
    } catch {
      setFranjas([]);
    }
  }, [idProyecto]);

  useEffect(() => { loadFranjas(); }, [loadFranjas]);

  const close = () => {
    setIsOpen(false);
    setFeatureId(null);
    setError('');
  };

  const save = async () => {
    if (!fechaVigencia || !featureId) {
      setError('Captura la vigencia y confirma la geometría del archivo.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.post(`/proyectos/${idProyecto}/franjas/importar`, {
        fecha_vigencia_inicio: fechaVigencia,
        id_carga_geoespacial_feature: featureId,
      });
      await loadFranjas();
      close();
      onImportSuccess?.();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible registrar la franja.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button type="button" onClick={() => setIsOpen(true)} style={{ width: '100%', padding: '10px', background: '#0284c7', color: 'white', border: 0, borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '15px' }}>
        <Upload size={18} /> Nueva versión de derecho de vía
      </button>
      {franjas.length > 0 && <p style={{ fontSize: '12px', color: '#64748b' }}>Versión activa: {franjas.find((item) => item.activo)?.version || 'sin versión activa'}</p>}
      {isOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <section style={{ background: '#fff', maxHeight: 'calc(100vh - 40px)', overflowY: 'auto', padding: '24px', width: 'min(820px, 100%)' }}>
            <header style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'start' }}>
              <div><h3 style={{ margin: 0 }}>Nueva versión de derecho de vía</h3><p style={{ color: '#64748b', fontSize: '13px' }}>La versión anterior se conserva como historial.</p></div>
              <button type="button" onClick={close} aria-label="Cerrar" style={{ border: 0, background: 'transparent', cursor: 'pointer' }}><X size={20} /></button>
            </header>
            <div style={{ margin: '18px 0' }}>
              <label style={{ display: 'grid', gap: '5px', fontSize: '13px' }}>Inicio de vigencia<input type="date" value={fechaVigencia} onChange={(event) => setFechaVigencia(event.target.value)} /></label>
            </div>
            <GeospatialUpload target="franja_derecho_via" value={featureId} onChange={setFeatureId} />
            {error && <p style={{ color: '#b91c1c', fontSize: '13px' }}>{error}</p>}
            <footer style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '18px' }}>
              <button type="button" onClick={close}>Cancelar</button>
              <button type="button" disabled={loading || !featureId} onClick={save} style={{ display: 'inline-flex', gap: '7px', alignItems: 'center' }}><Check size={16} />{loading ? 'Guardando...' : 'Confirmar versión'}</button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
