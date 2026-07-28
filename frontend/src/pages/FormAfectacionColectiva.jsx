import React, { useState } from 'react';
import { Layers } from 'lucide-react';
import api from '../api/axios';
import {
  ModalWrapper, SeccionHeader, Campo,
  ErrorBanner, ExitoMsg, BotonesAccion,
} from '../components/FormUI';
import { gridDos, inputStyle } from '../components/formStyles';

const TIPOS_TENENCIA = [
  'Tierras de Uso Común',
  'Parcelas con Destino Específico',
  'Sin Asignar',
  'Asentamiento Humano',
  'Zona de Urbanización Ejidal',
];

const SUBTIPOS = ['individual', 'copropiedad', 'sin asignar'];

export default function FormAfectacionColectiva({ idNucleo, idTramoNucleo, initialData = null, onSuccess, onClose }) {
  const [guardando, setGuardando] = useState(false);
  const [exito, setExito]         = useState(false);
  const [error, setError]         = useState(null);
  const [form, setForm] = useState({
    tipo_tenencia:           initialData?.tipo_tenencia           || '',
    subtipo_tenencia:        initialData?.subtipo_tenencia        || '',
    destino_superficie:      initialData?.destino_superficie      || '',
    no_parcela_solar:        initialData?.no_parcela_solar        || '',
    superficie_afectada_ha:  initialData?.superficie_afectada_ha  || '',
    num_personas_afectadas:  initialData?.num_personas_afectadas  || '',
    situacion_juridica:      initialData?.situacion_juridica      || '',
    documentacion_disponible: initialData?.documentacion_disponible || false,
    documentacion_faltante:  initialData?.documentacion_faltante  || '',
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
        id_nucleo:               idNucleo,
        id_tramo_nucleo:         idTramoNucleo,
        tipo_afectacion:         'colectivo',
        tipo_tenencia:           form.tipo_tenencia,
        subtipo_tenencia:        form.subtipo_tenencia        || null,
        destino_superficie:      form.destino_superficie      || null,
        no_parcela_solar:        form.no_parcela_solar        || null,
        superficie_afectada_ha:  form.superficie_afectada_ha  ? Number(form.superficie_afectada_ha) : null,
        num_personas_afectadas:  form.num_personas_afectadas  ? Number(form.num_personas_afectadas) : null,
        situacion_juridica:      form.situacion_juridica      || null,
        documentacion_disponible: form.documentacion_disponible,
        documentacion_faltante:  form.documentacion_faltante  || null,
        origen_registro:         'captura_sistema',
      };

      if (initialData) {
        await api.put(`/afectaciones/${initialData.id_afectacion}`, payload);
      } else {
        await api.post('/afectaciones', payload);
      }

      setExito(true);
      setTimeout(() => { onSuccess(); onClose(); }, 1200);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar la afectación. Intente de nuevo.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ModalWrapper
      titulo={initialData ? 'Editar Afectación Colectiva' : 'Nueva Afectación Colectiva'}
      subtitulo="Tierras de Uso Común"
      onClose={onClose}
      color="#0284c7"
    >
      {exito ? (
        <ExitoMsg mensaje={`¡Afectación colectiva ${initialData ? 'actualizada' : 'guardada'}!`} />
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>

          <ErrorBanner mensaje={error} />

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
                type="number" step="0.0001" min="0"
                value={form.superficie_afectada_ha}
                onChange={e => set('superficie_afectada_ha', e.target.value)}
                placeholder="0.0000" style={inputStyle}
              />
            </Campo>

            <Campo label="No. de Parcela / Solar">
              <input
                type="text"
                value={form.no_parcela_solar}
                onChange={e => set('no_parcela_solar', e.target.value)}
                placeholder="Ej. 25-A" style={inputStyle}
              />
            </Campo>

            <Campo label="Número de Personas Afectadas">
              <input
                type="number" min="0"
                value={form.num_personas_afectadas}
                onChange={e => set('num_personas_afectadas', e.target.value)}
                placeholder="0" style={inputStyle}
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

          <BotonesAccion
            onClose={onClose}
            guardando={guardando}
            labelGuardar={initialData ? 'Guardar Cambios' : 'Guardar Afectación Colectiva'}
            color="#0284c7"
          />
        </form>
      )}
    </ModalWrapper>
  );
}
