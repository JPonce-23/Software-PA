import React from 'react';
import { Check, LoaderCircle, ScanSearch, X } from 'lucide-react';
import api from '../api/axios';
import './TramoNucleoCandidates.css';

export default function TramoNucleoCandidates({ tramos, onChanged }) {
  const [tramoId, setTramoId] = React.useState('');
  const [candidates, setCandidates] = React.useState([]);
  const [consecutivos, setConsecutivos] = React.useState({});
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const [notice, setNotice] = React.useState('');

  const load = React.useCallback(async (id = tramoId) => {
    if (!id) return;
    const { data } = await api.get(`/cargas-geoespaciales/tramos/${id}/candidatos`);
    setCandidates(data);
  }, [tramoId]);

  const detect = async () => {
    if (!tramoId) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const { data } = await api.post(`/cargas-geoespaciales/tramos/${tramoId}/candidatos/detectar`);
      await load();
      setNotice(data.candidatos_nuevos ? `${data.candidatos_nuevos} candidatos nuevos detectados.` : 'No se detectaron candidatos nuevos.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible detectar candidatos.');
    } finally { setBusy(false); }
  };

  const resolve = async (candidate, accepted) => {
    setBusy(true); setError('');
    try {
      if (accepted) {
        const consecutivo = Number(consecutivos[candidate.id_candidato]);
        if (!consecutivo) throw new Error('Indica el consecutivo del expediente.');
        await api.post(`/cargas-geoespaciales/candidatos/${candidate.id_candidato}/confirmar`, { consecutivo });
      } else {
        await api.post(`/cargas-geoespaciales/candidatos/${candidate.id_candidato}/rechazar`, { motivo: 'Descartado después de revisión territorial.' });
      }
      await load();
      await onChanged?.();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'No fue posible resolver el candidato.');
    } finally { setBusy(false); }
  };

  return (
    <section className="tramo-nucleo-candidates">
      <header><div><h2>Detección asistida de cruces</h2><p>La detección no crea expedientes: cada candidato debe confirmarse o rechazarse.</p></div></header>
      <div className="tramo-nucleo-candidates-actions">
        <select value={tramoId} onChange={(event) => { setTramoId(event.target.value); setCandidates([]); setNotice(''); setError(''); }}>
          <option value="">Selecciona un tramo</option>
          {tramos.filter((item) => item.activo).map((item) => <option key={item.id_tramo} value={item.id_tramo}>{item.clave_tramo} · {item.nombre_tramo}</option>)}
        </select>
        <button type="button" disabled={!tramoId || busy} onClick={detect}><ScanSearch size={16} />Detectar con la sección activa</button>
        <button type="button" disabled={!tramoId || busy} onClick={() => load().catch((requestError) => setError(requestError.response?.data?.detail || 'No fue posible consultar candidatos.'))}>Actualizar</button>
      </div>
      {error && <p className="tramo-nucleo-candidates-error">{error}</p>}
      {notice && <p className="tramo-nucleo-candidates-notice">{notice}</p>}
      {busy && <p className="tramo-nucleo-candidates-notice"><LoaderCircle className="tramo-nucleo-candidates-spin" size={15} />Procesando…</p>}
      {candidates.length > 0 && <div className="tramo-nucleo-candidates-table">
        {candidates.map((candidate) => <div key={candidate.id_candidato} className="tramo-nucleo-candidate-row">
          <div><strong>{candidate.nombre_nucleo}</strong><span>{(Number(candidate.area_interseccion_m2) / 10000).toLocaleString(undefined, { maximumFractionDigits: 4 })} ha dentro del derecho de vía</span></div>
          <span className={`tramo-nucleo-candidate-state ${candidate.estado}`}>{candidate.estado}</span>
          {candidate.estado === 'pendiente' && <><input type="number" min="1" placeholder="Consecutivo" value={consecutivos[candidate.id_candidato] || ''} onChange={(event) => setConsecutivos((current) => ({ ...current, [candidate.id_candidato]: event.target.value }))} /><button type="button" disabled={busy} onClick={() => resolve(candidate, true)} title="Confirmar expediente"><Check size={16} /></button><button type="button" disabled={busy} onClick={() => resolve(candidate, false)} title="Rechazar candidato"><X size={16} /></button></>}
        </div>)}
      </div>}
    </section>
  );
}
