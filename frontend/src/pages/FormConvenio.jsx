import React, { useState } from 'react';
import { X, Loader2, CheckCircle2, FileSignature } from 'lucide-react';
import api from '../api/axios';

const TIPOS_CONVENIO = [
  { value: 'cop_original', label: 'Convenio de Ocupación Previa (Original)' },
  { value: 'modificatorio', label: 'Convenio Modificatorio' },
  { value: 'superficie_adicional', label: 'Superficie Adicional' },
  { value: 'obras_complementarias', label: 'Obras Complementarias' },
  { value: 'ampliacion', label: 'Ampliación' },
];

export default function FormConvenio({ idTramoNucleo, afectacion, asambleas, initialData = null, onSuccess, onClose }) {
  const [guardando, setGuardando] = useState(false);
  const [exito, setExito] = useState(false);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({
    tipo_convenio: initialData?.tipo_convenio || 'cop_original',
    fecha_firma: initialData?.fecha_firma || '',
    superficie_real_afectada_ha: initialData?.superficie_real_afectada_ha || afectacion?.superficie_afectada_ha || '',
    superficie_total_ha: initialData?.superficie_total_ha || '',
    monto_100: initialData?.monto_100 || '',
    monto_90: initialData?.monto_90 || '',
    monto_bdt: initialData?.monto_bdt || '',
    id_asamblea_autorizacion: initialData?.id_asamblea_autorizacion || '',
    observaciones: initialData?.observaciones || '',
  });

  const set = (campo, valor) => setForm(prev => ({ ...prev, [campo]: valor }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!afectacion) {
      setError('Error interno: No se ha provisto una afectación válida.');
      return;
    }

    setGuardando(true);

    try {
      const payload = {
        id_tramo_nucleo: idTramoNucleo,
        id_afectacion: afectacion.id_afectacion,
        tipo_afectacion: afectacion.tipo_afectacion, // 'colectivo' o 'individual'
        tipo_convenio: form.tipo_convenio,
        fecha_firma: form.fecha_firma || null,
        superficie_real_afectada_ha: form.superficie_real_afectada_ha ? Number(form.superficie_real_afectada_ha) : null,
        superficie_total_ha: form.superficie_total_ha ? Number(form.superficie_total_ha) : null,
        monto_100: form.monto_100 ? Number(form.monto_100) : null,
        monto_90: form.monto_90 ? Number(form.monto_90) : null,
        monto_bdt: form.monto_bdt ? Number(form.monto_bdt) : null,
        id_asamblea_autorizacion: form.id_asamblea_autorizacion ? Number(form.id_asamblea_autorizacion) : null,
        observaciones: form.observaciones || null,
      };

      if (initialData) {
        await api.put(`/convenios/${initialData.id_convenio}`, payload);
      } else {
        await api.post('/convenios', payload);
      }
      setExito(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar el convenio. Intente de nuevo.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setGuardando(false);
    }
  };

  const tipoLabel = afectacion?.tipo_afectacion === 'colectivo' ? 'Tierras de Uso Común' : 'Parcela Individual';
  const idLabel = afectacion?.tipo_afectacion === 'colectivo' ? `#${afectacion.id_afectacion}` : `Parcela #${afectacion.id_parcela || 'N/A'} (Afectación #${afectacion.id_afectacion})`;

  return (
    <ModalWrapper 
      titulo={initialData ? `Editar Convenio (${tipoLabel})` : `Registrar Convenio (${tipoLabel})`} 
      subtitulo={`Vinculado a: ${idLabel}`} 
      onClose={onClose} color="#059669"
    >
      {exito ? (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <CheckCircle2 size={48} color="#16a34a" style={{ display: 'block', margin: '0 auto 12px auto' }} />
          <p style={{ fontSize: '16px', color: '#16a34a', fontWeight: '600' }}>
            ¡Convenio {initialData ? 'actualizado' : 'registrado'} exitosamente!
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '12px 16px', borderRadius: '8px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          <SeccionHeader icono={<FileSignature size={16} />} titulo="Datos del Acuerdo" />

          <div style={gridDos}>
            <Campo label="Tipo de Convenio *">
              <select value={form.tipo_convenio} onChange={e => set('tipo_convenio', e.target.value)} style={inputStyle} required>
                {TIPOS_CONVENIO.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Campo>

            <Campo label="Fecha de Firma">
              <input type="date" value={form.fecha_firma} onChange={e => set('fecha_firma', e.target.value)} style={inputStyle} />
            </Campo>

            <Campo label="Superficie Afectada Real (Ha)">
              <input type="number" step="0.0001" min="0" value={form.superficie_real_afectada_ha} onChange={e => set('superficie_real_afectada_ha', e.target.value)} placeholder="0.0000" style={inputStyle} />
            </Campo>

            <Campo label="Superficie Total (Ha) [Opcional]">
              <input type="number" step="0.0001" min="0" value={form.superficie_total_ha} onChange={e => set('superficie_total_ha', e.target.value)} placeholder="0.0000" style={inputStyle} />
            </Campo>
          </div>

          {afectacion?.tipo_afectacion === 'colectivo' && asambleas && (
            <Campo label="Asamblea de Autorización (Vinculación)">
              <select value={form.id_asamblea_autorizacion} onChange={e => set('id_asamblea_autorizacion', e.target.value)} style={inputStyle}>
                <option value="">-- Ninguna / Seleccionar Asamblea --</option>
                {asambleas.map(a => (
                  <option key={a.id_asamblea} value={a.id_asamblea}>
                    Asamblea #{a.id_asamblea} - {a.tipo_asamblea} ({a.fecha_realizada || 'Sin fecha'})
                  </option>
                ))}
              </select>
            </Campo>
          )}

          <SeccionHeader icono={<FileSignature size={16} />} titulo="Cantidades Acordadas / Pagos" />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <Campo label="Monto al 100% ($)">
              <input type="number" step="0.01" min="0" value={form.monto_100} onChange={e => set('monto_100', e.target.value)} placeholder="0.00" style={inputStyle} />
            </Campo>
            <Campo label="Monto al 90% ($)">
              <input type="number" step="0.01" min="0" value={form.monto_90} onChange={e => set('monto_90', e.target.value)} placeholder="0.00" style={inputStyle} />
            </Campo>
            <Campo label="Monto BDT ($)">
              <input type="number" step="0.01" min="0" value={form.monto_bdt} onChange={e => set('monto_bdt', e.target.value)} placeholder="0.00" style={inputStyle} />
            </Campo>
          </div>

          <Campo label="Observaciones Adicionales">
            <textarea
              value={form.observaciones}
              onChange={e => set('observaciones', e.target.value)}
              placeholder="Notas, acuerdos especiales, etc."
              rows={2}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </Campo>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', paddingTop: '10px', borderTop: '1px solid #f1f5f9', marginTop: '8px' }}>
            <button type="button" onClick={onClose} style={btnSecundario} disabled={guardando}>Cancelar</button>
            <button type="submit" style={{ ...btnPrimario, background: '#059669' }} disabled={guardando}>
              {guardando ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Guardando...</> : initialData ? 'Guardar Cambios' : 'Registrar Convenio'}
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
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
      <div style={{ background: 'white', borderRadius: '16px', width: '100%', maxWidth: '700px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.2)' }}>
        <div style={{ padding: '24px 28px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderLeft: `5px solid ${color}` }}>
          <div>
            <h2 style={{ fontSize: '18px', color: '#0f172a', fontWeight: '700', margin: 0 }}>{titulo}</h2>
            <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0 0' }}>{subtitulo}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: '6px' }}>
            <X size={20} />
          </button>
        </div>
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
  color: 'white', border: 'none', padding: '11px 24px',
  borderRadius: '8px', cursor: 'pointer', fontWeight: '600', fontSize: '14px',
  display: 'flex', alignItems: 'center', gap: '8px',
};

const btnSecundario = {
  background: 'white', color: '#64748b', border: '1px solid #e2e8f0', padding: '11px 24px',
  borderRadius: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px',
};
