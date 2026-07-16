import React, { useState, useEffect } from 'react';
import { X, Loader2, CheckCircle2, Search, User, UserPlus, FileText } from 'lucide-react';
import api from '../api/axios';

const TIPOS_PARCELA = ['individual', 'copropiedad'];

export default function FormAfectacionIndividual({ idNucleo, idTramoNucleo, initialData = null, onSuccess, onClose }) {
  // Modo: 'buscar', 'nuevo', o 'editar_afectacion'
  const [modoTitular, setModoTitular] = useState(initialData ? 'editar_afectacion' : 'buscar');

  // Estado búsqueda de titular existente
  const [busqueda, setBusqueda] = useState('');
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [parcelaSeleccionada, setParcelaSeleccionada] = useState(null);

  // Formulario nuevo titular
  const [titular, setTitular] = useState({
    nombre_titular: '',
    tipo_parcela: '',
    no_parcela_ppt: '',
    certificado_parcelario: '',
    folio_derechos: '',
    constancia_vigencia_fecha: '',
    documentacion_disponible: false,
    documentacion_faltante: '',
  });

  // Datos de la Afectación
  const [afectacion, setAfectacion] = useState({
    tipo_tenencia: initialData?.tipo_tenencia || 'Parcelada',
    subtipo_tenencia: initialData?.subtipo_tenencia || '',
    no_parcela_solar: initialData?.no_parcela_solar || '',
    superficie_afectada_ha: initialData?.superficie_afectada_ha || '',
    situacion_juridica: initialData?.situacion_juridica || '',
    documentacion_disponible: initialData?.documentacion_disponible || false,
    documentacion_faltante: initialData?.documentacion_faltante || '',
  });

  const [guardando, setGuardando] = useState(false);
  const [exito, setExito]         = useState(false);
  const [error, setError]         = useState(null);

  const setT = (campo, valor) => setTitular(prev => ({ ...prev, [campo]: valor }));
  const setA = (campo, valor) => setAfectacion(prev => ({ ...prev, [campo]: valor }));

  // Buscar parcelas existentes en tiempo real
  useEffect(() => {
    if (modoTitular !== 'buscar' || busqueda.length < 2) {
      setResultados([]);
      return;
    }
    const timer = setTimeout(async () => {
      setBuscando(true);
      try {
        const res = await api.get(`/parcelas?id_nucleo=${idNucleo}`);
        const filtradas = res.data.filter(p =>
          (p.nombre_titular || '').toLowerCase().includes(busqueda.toLowerCase()) ||
          (p.no_parcela_ppt || '').toLowerCase().includes(busqueda.toLowerCase()) ||
          (p.certificado_parcelario || '').toLowerCase().includes(busqueda.toLowerCase())
        );
        setResultados(filtradas);
      } catch {
        setResultados([]);
      } finally {
        setBuscando(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [busqueda, idNucleo, modoTitular]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validaciones mínimas
    if (modoTitular === 'buscar' && !parcelaSeleccionada) {
      setError('Selecciona un titular de la lista o cambia al modo "Registrar Nuevo Titular".');
      return;
    }
    if (modoTitular === 'nuevo' && !titular.nombre_titular.trim()) {
      setError('El nombre del titular es obligatorio.');
      return;
    }

    setGuardando(true);
    try {
      let idParcela;

      if (modoTitular === 'buscar') {
        // Titular ya existe, usar su ID directamente
        idParcela = parcelaSeleccionada.id_parcela;
      } else {
        // PASO 1: Crear la parcela (nuevo titular)
        const parcela_payload = {
          id_nucleo: idNucleo,
          nombre_titular: titular.nombre_titular.trim(),
          tipo_parcela: titular.tipo_parcela || null,
          no_parcela_ppt: titular.no_parcela_ppt || null,
          certificado_parcelario: titular.certificado_parcelario || null,
          folio_derechos: titular.folio_derechos || null,
          constancia_vigencia_fecha: titular.constancia_vigencia_fecha || null,
          documentacion_disponible: titular.documentacion_disponible,
          documentacion_faltante: titular.documentacion_faltante || null,
        };
        const parcelaRes = await api.post('/parcelas', parcela_payload);
        idParcela = parcelaRes.data.id_parcela;
      }

      // PASO 2: Crear la afectación con el id_parcela obtenido
      const afectacion_payload = {
        id_nucleo: idNucleo,
        id_tramo_nucleo: idTramoNucleo,
        id_parcela: idParcela,
        tipo_afectacion: 'individual',
        tipo_tenencia: afectacion.tipo_tenencia || 'Parcelada',
        subtipo_tenencia: afectacion.subtipo_tenencia || null,
        no_parcela_solar: afectacion.no_parcela_solar || null,
        superficie_afectada_ha: afectacion.superficie_afectada_ha ? Number(afectacion.superficie_afectada_ha) : null,
        situacion_juridica: afectacion.situacion_juridica || null,
        documentacion_disponible: afectacion.documentacion_disponible,
        documentacion_faltante: afectacion.documentacion_faltante || null,
        origen_registro: 'captura_sistema',
      };
      if (initialData) {
        // Solo actualizamos la afectación
        await api.put(`/afectaciones/${initialData.id_afectacion}`, afectacion_payload);
      } else {
        await api.post('/afectaciones', afectacion_payload);
      }

      setExito(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar. Intente de nuevo.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ModalWrapper 
      titulo={initialData ? "Editar Afectación Individual" : "Nueva Afectación Individual"} 
      subtitulo="Derechos Parcelarios" 
      onClose={onClose} color="#d97706"
    >
      {exito ? (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <CheckCircle2 size={48} color="#16a34a" style={{ display: 'block', margin: '0 auto 12px auto' }} />
          <p style={{ fontSize: '16px', color: '#16a34a', fontWeight: '600' }}>¡Afectación individual guardada!</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '12px 16px', borderRadius: '8px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          {/* ══════════════════════════════════════════════ */}
          {/* SECCIÓN 1: Datos del Titular / Parcela         */}
          {/* ══════════════════════════════════════════════ */}
          <div style={{ background: '#f8fafc', borderRadius: '12px', padding: '20px', border: '1px solid #e2e8f0' }}>
            <SeccionHeader icono={<User size={16} />} titulo="Sección 1 — Datos del Titular" />

            {/* Selector de modo (oculto en modo edición) */}
            {!initialData && (
              <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                <ModoBtn
                  activo={modoTitular === 'buscar'}
                  icono={<Search size={15} />}
                  label="Buscar titular existente"
                  onClick={() => { setModoTitular('buscar'); setParcelaSeleccionada(null); }}
                />
                <ModoBtn
                  activo={modoTitular === 'nuevo'}
                  icono={<UserPlus size={15} />}
                  label="Registrar nuevo titular"
                  onClick={() => { setModoTitular('nuevo'); setParcelaSeleccionada(null); setBusqueda(''); }}
                />
              </div>
            )}

            {/* ── Modo edición (solo lectura del ID de parcela) ── */}
            {modoTitular === 'editar_afectacion' && (
              <div style={{ marginTop: '16px', background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '12px 16px' }}>
                <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 4px 0' }}>Titular vinculado a esta afectación</p>
                <p style={{ fontSize: '14px', color: '#1e293b', margin: 0, fontWeight: '500' }}>
                  ID de Parcela: #{initialData.id_parcela}
                </p>
                <p style={{ fontSize: '11px', color: '#64748b', margin: '4px 0 0 0' }}>La edición de datos personales del titular debe realizarse desde su propio registro.</p>
              </div>
            )}

            {/* ── Modo búsqueda ── */}
            {modoTitular === 'buscar' && (
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ position: 'relative' }}>
                  <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="text"
                    value={busqueda}
                    onChange={e => setBusqueda(e.target.value)}
                    placeholder="Buscar por nombre, No. PPT o certificado..."
                    style={{ ...inputStyle, paddingLeft: '38px' }}
                  />
                </div>
                {buscando && <span style={{ fontSize: '13px', color: '#94a3b8' }}>Buscando...</span>}
                {resultados.length > 0 && (
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden', maxHeight: '200px', overflowY: 'auto' }}>
                    {resultados.map(p => (
                      <div
                        key={p.id_parcela}
                        onClick={() => { setParcelaSeleccionada(p); setBusqueda(p.nombre_titular || ''); setResultados([]); }}
                        style={{
                          padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid #f1f5f9',
                          background: parcelaSeleccionada?.id_parcela === p.id_parcela ? '#f0fdf4' : 'white',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
                        onMouseLeave={e => e.currentTarget.style.background = parcelaSeleccionada?.id_parcela === p.id_parcela ? '#f0fdf4' : 'white'}
                      >
                        <div style={{ fontWeight: '500', color: '#1e293b', fontSize: '14px' }}>{p.nombre_titular || '—'}</div>
                        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                          PPT: {p.no_parcela_ppt || '—'} · Cert: {p.certificado_parcelario || '—'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {parcelaSeleccionada && (
                  <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '8px', padding: '12px 16px' }}>
                    <p style={{ fontSize: '13px', color: '#16a34a', fontWeight: '600', margin: '0 0 4px 0' }}>
                      ✓ Titular seleccionado
                    </p>
                    <p style={{ fontSize: '14px', color: '#1e293b', margin: 0 }}>
                      {parcelaSeleccionada.nombre_titular} · Parcela #{parcelaSeleccionada.id_parcela}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* ── Modo nuevo titular ── */}
            {modoTitular === 'nuevo' && (
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <Campo label="Nombre completo del titular *">
                  <input
                    type="text"
                    value={titular.nombre_titular}
                    onChange={e => setT('nombre_titular', e.target.value)}
                    placeholder="Nombre completo del ejidatario o comunero"
                    style={inputStyle}
                    required
                  />
                </Campo>
                <div style={gridDos}>
                  <Campo label="Tipo de Parcela">
                    <select value={titular.tipo_parcela} onChange={e => setT('tipo_parcela', e.target.value)} style={inputStyle}>
                      <option value="">Seleccione...</option>
                      {TIPOS_PARCELA.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </Campo>
                  <Campo label="No. Parcela PPT">
                    <input type="text" value={titular.no_parcela_ppt} onChange={e => setT('no_parcela_ppt', e.target.value)} placeholder="Ej. 125" style={inputStyle} />
                  </Campo>
                  <Campo label="Certificado Parcelario">
                    <input type="text" value={titular.certificado_parcelario} onChange={e => setT('certificado_parcelario', e.target.value)} placeholder="Ej. 0815-CP-0025" style={inputStyle} />
                  </Campo>
                  <Campo label="Folio de Derechos">
                    <input type="text" value={titular.folio_derechos} onChange={e => setT('folio_derechos', e.target.value)} placeholder="Folio" style={inputStyle} />
                  </Campo>
                  <Campo label="Constancia Vigencia (fecha)">
                    <input type="date" value={titular.constancia_vigencia_fecha} onChange={e => setT('constancia_vigencia_fecha', e.target.value)} style={inputStyle} />
                  </Campo>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', userSelect: 'none' }}>
                  <input type="checkbox" checked={titular.documentacion_disponible} onChange={e => setT('documentacion_disponible', e.target.checked)} style={{ width: '18px', height: '18px' }} />
                  <span style={{ fontSize: '14px', color: '#334155' }}>¿Documentación del titular disponible?</span>
                </label>
                {!titular.documentacion_disponible && (
                  <Campo label="Documentación faltante del titular">
                    <textarea value={titular.documentacion_faltante} onChange={e => setT('documentacion_faltante', e.target.value)} placeholder="Qué falta por obtener..." rows={2} style={{ ...inputStyle, resize: 'vertical' }} />
                  </Campo>
                )}
              </div>
            )}
          </div>

          {/* ══════════════════════════════════════════════ */}
          {/* SECCIÓN 2: Datos de la Afectación              */}
          {/* ══════════════════════════════════════════════ */}
          <div style={{ background: '#f8fafc', borderRadius: '12px', padding: '20px', border: '1px solid #e2e8f0' }}>
            <SeccionHeader icono={<FileText size={16} />} titulo="Sección 2 — Datos de la Afectación" />
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={gridDos}>
                <Campo label="Superficie Afectada (Ha)">
                  <input type="number" step="0.0001" min="0" value={afectacion.superficie_afectada_ha} onChange={e => setA('superficie_afectada_ha', e.target.value)} placeholder="0.0000" style={inputStyle} />
                </Campo>
                <Campo label="No. de Parcela / Solar">
                  <input type="text" value={afectacion.no_parcela_solar} onChange={e => setA('no_parcela_solar', e.target.value)} placeholder="Ej. 25-B" style={inputStyle} />
                </Campo>
              </div>
              <Campo label="Situación Jurídica">
                <textarea value={afectacion.situacion_juridica} onChange={e => setA('situacion_juridica', e.target.value)} placeholder="Conflictos, amparos, sucesiones en trámite..." rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
              </Campo>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', userSelect: 'none' }}>
                <input type="checkbox" checked={afectacion.documentacion_disponible} onChange={e => setA('documentacion_disponible', e.target.checked)} style={{ width: '18px', height: '18px' }} />
                <span style={{ fontSize: '14px', color: '#334155' }}>¿Documentación de la afectación disponible?</span>
              </label>
              {!afectacion.documentacion_disponible && (
                <Campo label="Documentación faltante de la afectación">
                  <textarea value={afectacion.documentacion_faltante} onChange={e => setA('documentacion_faltante', e.target.value)} placeholder="Qué falta por obtener..." rows={2} style={{ ...inputStyle, resize: 'vertical' }} />
                </Campo>
              )}
            </div>
          </div>

          {/* Acciones */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', borderTop: '1px solid #f1f5f9' }}>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
              {modoTitular === 'nuevo' ? '* Se crearán la parcela y la afectación en 2 pasos automáticos.' : '* Se creará la afectación vinculada al titular seleccionado.'}
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button type="button" onClick={onClose} style={btnSecundario} disabled={guardando}>Cancelar</button>
              <button type="submit" style={{ ...btnPrimario, background: '#d97706' }} disabled={guardando}>
                {guardando ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Guardando...</> : initialData ? 'Guardar Cambios' : 'Guardar Afectación Individual'}
              </button>
            </div>
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
      <div style={{ background: 'white', borderRadius: '16px', width: '100%', maxWidth: '740px', maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.2)' }}>
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

function ModoBtn({ activo, icono, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1, padding: '10px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px',
        fontWeight: activo ? '600' : '400', display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'center',
        background: activo ? '#006341' : 'white',
        color: activo ? 'white' : '#64748b',
        border: `1px solid ${activo ? '#006341' : '#e2e8f0'}`,
        transition: 'all 0.2s',
      }}
    >
      {icono} {label}
    </button>
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

const gridDos = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' };

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
