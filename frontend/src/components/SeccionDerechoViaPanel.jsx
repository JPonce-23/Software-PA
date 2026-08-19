import React, { useState } from 'react';
import { Check, X } from 'lucide-react';
import api from '../api/axios';
import GeospatialUpload from './GeospatialUpload';

export default function SeccionDerechoViaPanel({ tramo, onSaved, onClose }) {
  const [fuente, setFuente] = useState('');
  const [featureId, setFeatureId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    if (!fuente.trim() || !featureId) {
      setError('Captura la fuente y confirma la sección del archivo.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await api.post(`/tramos/${tramo.id_tramo}/secciones-derecho-via/importar`, {
        fuente: fuente.trim(), id_carga_geoespacial_feature: featureId,
      });
      await onSaved?.();
      onClose();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible registrar la sección.');
    } finally { setSaving(false); }
  };

  return (
    <div className="admin-dialog-backdrop" role="presentation">
      <section className="admin-dialog admin-dialog-wide">
        <header><div><h2>Sección espacial del tramo</h2><p>{tramo.clave_tramo} · {tramo.nombre_tramo}</p></div><button className="admin-icon-button" type="button" title="Cerrar" onClick={onClose}><X size={18} /></button></header>
        <label className="admin-field"><span>Fuente oficial</span><input value={fuente} onChange={(event) => setFuente(event.target.value)} /></label>
        <GeospatialUpload target="seccion_derecho_via" source={fuente} value={featureId} onChange={setFeatureId} />
        {error && <p className="admin-error">{error}</p>}
        <footer><button type="button" className="admin-button secondary" onClick={onClose}>Cancelar</button><button type="button" className="admin-button" disabled={saving || !featureId} onClick={save}><Check size={16} />{saving ? 'Guardando...' : 'Confirmar sección'}</button></footer>
      </section>
    </div>
  );
}
