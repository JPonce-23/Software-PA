import React, { useState } from 'react';
import { X, Loader2, CheckCircle2, Layers } from 'lucide-react';
import api from '../api/axios';

const TIPOS_TENENCIA = [
  'Tierras de Uso Común',
  'Parcelas con Destino Específico',
  'Sin Asignar',
  'Asentamiento Humano',
  'Zona de Urbanización Ejidal',
];

const SUBTIPOS = [
  'individual',
  'copropiedad',
  'sin asignar',
];

export default function FormAfectacionColectiva({ idNucleo, idTramoNucleo, onSuccess, onClose }) {
  const [guardando, setGuardando]   = useState(false);
  const [exito, setExito]           = useState(false);
  const [error, setError]           = useState(null);
  const [form, setForm] = useState({
    tipo_tenencia: '',
    subtipo_tenencia: '',
    destino_superficie: '',
    no_parcela_solar: '',
    superficie_afectada_ha: '',
    num_personas_afectadas: '',
    situacion_juridica: '',
    documentacion_disponible: false,
    documentacion_faltante: '',
  });

  const set = (campo, valor) => setForm(prev => ({ ...prev, [campo]: valor }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!form.tipo_tenencia) {
      setError('El Tipo de Tenencia es obligatorio.');
      return;
    }

    setGuardando(true);
    try {
      const payload = {
        id_nucleo: idNucleo,
        id_tramo_nucleo: idTramoNucleo,
        tipo_afectacion: 'colectivo',
        tipo_tenencia: form.tipo_tenencia,
        subtipo_tenencia: form.subtipo_tenencia || null,
        destino_superficie: form.destino_superficie || null,
        no_parcela_solar: form.no_parcela_solar || null,
        superficie_afectada_ha: form.superficie_afectada_ha ? Number(form.superficie_afectada_ha) : null,
        num_personas_afectadas: form.num_personas_afectadas ? Number(form.num_personas_afectadas) : null,
        situacion_juridica: form.situacion_juridica || null,
        documentacion_disponible: form.documentacion_disponible,
        documentacion_faltante: form.documentacion_faltante || null,
        origen_registro: 'captura_sistema',
      };

      await api.post('/afectaciones', payload);
      setExito(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar la afectación. Intente de nuevo.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ModalWrapper titulo="Nueva Afectación Colectiva" subtitulo="Tierras de Uso Común" onClose={onClose} color="#0284c7">
      {exito ? (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <CheckCircle2 size={48} color="#16a34a" style={{ display: 'block', margin: '0 auto 12px auto' }} />
          <p style={{ fontSize: '16px', color: '#16a34a', fontWeight: '600' }}>¡Afectación colectiva guardada!</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '12px 16px', borderRadius: '8px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          {/* SECCIÓN 1: Tipo de tenencia */}
          <SeccionHeader icono={<Layers size={16} />} titulo="Tipo de Afectación" />

          <div style={gridDos}>
            <Campo label="Tipo de Tenencia *">
              <select value={form.tipo_tenencia} onChange={e => set('tipo_tenencia', e.target.value)} style={inputStyle} required>
                <option value="">Seleccione...</option>
                {TIPOS_TENENCIA.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Campo>

            <Campo label="Subtipo de Tenencia">
              <select value={form.subtipo_tenencia} onChange={e => set('subtipo_tenencia', e.target.value)} style={inputStyle}>
                <option value="">Seleccione (opcional)</option>
                {SUBTIPOS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Campo>
          </div>

          <Campo label="Destino de la Superficie">
            <input
              type="text"
              value={form.destino_superficie}
              onChange={e => set('destino_superficie', e.target.value)}
              placeholder="Ej. Derecho de vía, Zona de amortiguamiento..."
              style={inputStyle}
            />
          </Campo>

          {/* SECCIÓN 2: Datos de afectación */}
          <SeccionHeader icono={<Layers size={16} />} titulo="Datos de la Afectación" />

          <div style={gridDos}>
            <Campo label="Superficie Afectada (Ha)">
              <input
                type="number"
                step="0.0001"
                min="0"
                value={form.superficie_afectada_ha}
                onChange={e => set('superficie_afectada_ha', e.target.value)}
                placeholder="0.0000"
                style={inputStyle}
              />
            </Campo>

            <Campo label="No. de Parcela / Solar">
              <input
                type="text"
                value={form.no_parcela_solar}
                onChange={e => set('no_parcela_solar', e.target.value)}
                placeholder="Ej. 25-A"
                style={inputStyle}
              />
            </Campo>

            <Campo label="Número de Personas Afectadas">
              <input
                type="number"
                min="0"
                value={form.num_personas_afectadas}
                onChange={e => set('num_personas_afectadas', e.target.value)}
                placeholder="0"
                style={inputStyle}
              />
            </Campo>
          </div>

          <Campo label="Situación Jurídica (Observaciones)">
            <textarea
              value={form.situacion_juridica}
              onChange={e => set('situacion_juridica', e.target.value)}
              placeholder="Indique conflictos, amparos, sucesiones en proceso, etc."
              rows={3}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </Campo>

          {/* SECCIÓN 3: Documentación */}
          <SeccionHeader icono={<Layers size={16} />} titulo="Soporte Documental" />

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={form.documentacion_disponible}
              onChange={e => set('documentacion_disponible', e.target.checked)}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '14px', color: '#334155' }}>¿La documentación está disponible y completa?</span>
          </label>

          {!form.documentacion_disponible && (
            <Campo label="Documentación Faltante">
              <textarea
                value={form.documentacion_faltante}
                onChange={e => set('documentacion_faltante', e.target.value)}
                placeholder="Describa qué documentos faltan..."
                rows={2}
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </Campo>
          )}

          {/* Acciones */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', paddingTop: '10px', borderTop: '1px solid #f1f5f9', marginTop: '8px' }}>
            <button type="button" onClick={onClose} style={btnSecundario} disabled={guardando}>Cancelar</button>
            <button type="submit" style={btnPrimario} disabled={guardando}>
              {guardando ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Guardando...</> : 'Guardar Afectación Colectiva'}
            </button>
          </div>
        </form>
      )}
    </ModalWrapper>
  );
}

// ─── Helpers de UI ───────────────────────────────────────────────────────────

function ModalWrapper({ titulo, subtitulo, onClose, color, children }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
    }}>
      <div style={{
        background: 'white', borderRadius: '16px', width: '100%', maxWidth: '680px',
        maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 60px rgba(0,0,0,0.2)',
      }}>
        {/* Header del modal */}
        <div style={{ padding: '24px 28px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderLeft: `5px solid ${color}` }}>
          <div>
            <h2 style={{ fontSize: '18px', color: '#0f172a', fontWeight: '700', margin: 0 }}>{titulo}</h2>
            <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0 0' }}>{subtitulo}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: '6px' }}>
            <X size={20} />
          </button>
        </div>
        {/* Contenido scrollable */}
        <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>{children}</div>
      </div>
    </div>
  );
}

function SeccionHeader({ icono, titulo }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '6px', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '13px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
      {icono} {titulo}
    </div>
  );
}

function Campo({ label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label style={{ fontSize: '13px', color: '#475569', fontWeight: '500' }}>{label}</label>
      {children}
    </div>
  );
}

const gridDos = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' };

const inputStyle = {
  padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0',
  outline: 'none', fontSize: '14px', color: '#1e293b', background: 'white',
  width: '100%', boxSizing: 'border-box',
};

const btnPrimario = {
  background: '#006341', color: 'white', border: 'none', padding: '11px 24px',
  borderRadius: '8px', cursor: 'pointer', fontWeight: '600', fontSize: '14px',
  display: 'flex', alignItems: 'center', gap: '8px',
};

const btnSecundario = {
  background: 'white', color: '#64748b', border: '1px solid #e2e8f0', padding: '11px 24px',
  borderRadius: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px',
};
