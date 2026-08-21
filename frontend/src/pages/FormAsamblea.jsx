import React, { useEffect, useState } from 'react';
import { Calendar as CalendarIcon } from 'lucide-react';
import api from '../api/axios';
import {
  ModalWrapper, SeccionHeader, Campo,
  ErrorBanner, ExitoMsg, BotonesAccion,
} from '../components/FormUI';
import { gridDos, inputStyle } from '../components/formStyles';

const TIPOS_ASAMBLEA = [
  { value: 'informacion',    label: 'Asamblea de Información' },
  { value: 'anuencia',       label: 'Asamblea de Anuencia' },
  { value: 'retiro_fondos',  label: 'Asamblea de Retiro de Fondos' },
  { value: 'conciliacion',   label: 'Asamblea de Conciliación' },
  { value: 'no_verificativo', label: 'Asamblea Sin Verificativo' },
];

const CONTEXTOS = [
  { value: 'cop_original',         label: 'COP Original' },
  { value: 'obras_complementarias', label: 'Obras Complementarias' },
  { value: 'superficie_adicional', label: 'Superficie Adicional' },
];

export default function FormAsamblea({ idNucleo, idTramoNucleo, afectaciones = [], initialData = null, onSuccess, onClose }) {
  const [guardando, setGuardando] = useState(false);
  const [exito, setExito]         = useState(false);
  const [error, setError]         = useState(null);
  const [ciclos, setCiclos]       = useState([]);

  const [form, setForm] = useState({
    contexto_proceso:        initialData?.contexto_proceso        || 'cop_original',
    tipo_asamblea:           initialData?.tipo_asamblea           || 'anuencia',
    resultado_anuencia:      initialData?.resultado_anuencia      || 'pendiente',
    estatus_asamblea:        initialData?.estatus_asamblea        || 'programado',
    fecha_exp_1a:            initialData?.fecha_exp_1a            || '',
    fecha_prog_1a:           initialData?.fecha_prog_1a           || '',
    fecha_exp_2a:            initialData?.fecha_exp_2a            || '',
    fecha_prog_2a:           initialData?.fecha_prog_2a           || '',
    fecha_realizada:         initialData?.fecha_realizada         || '',
    documentacion_disponible: initialData?.documentacion_disponible || false,
    documentacion_faltante:  initialData?.documentacion_faltante  || '',
    observaciones:           initialData?.observaciones           || '',
    id_afectacion:           initialData?.id_afectacion           || '',
    id_ciclo_afectacion:     initialData?.id_ciclo_afectacion     || '',
  });

  const set = (campo, valor) => setForm(prev => ({ ...prev, [campo]: valor }));

  useEffect(() => {
    if (!form.id_afectacion) return;
    api.get(`/afectaciones/${form.id_afectacion}/ciclos`)
      .then((response) => { console.log("CICLOS:", response.data); setCiclos(response.data); })
      .catch(() => setCiclos([]));
  }, [form.id_afectacion]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      const payload = {
        id_nucleo:               idNucleo,
        id_tramo_nucleo:         idTramoNucleo,
        id_afectacion:           Number(form.id_afectacion),
        id_ciclo_afectacion:     Number(form.id_ciclo_afectacion),
        contexto_proceso:        form.contexto_proceso,
        tipo_asamblea:           form.tipo_asamblea,
        resultado_anuencia:      form.resultado_anuencia,
        estatus_asamblea:        form.estatus_asamblea,
        fecha_exp_1a:            form.fecha_exp_1a    || null,
        fecha_prog_1a:           form.fecha_prog_1a   || null,
        fecha_exp_2a:            form.fecha_exp_2a    || null,
        fecha_prog_2a:           form.fecha_prog_2a   || null,
        fecha_realizada:         form.fecha_realizada || null,
        documentacion_disponible: form.documentacion_disponible,
        documentacion_faltante:  form.documentacion_faltante || null,
        observaciones:           form.observaciones           || null,
      };

      if (initialData) {
        await api.put(`/asambleas/${initialData.id_asamblea}`, payload);
      } else {
        await api.post('/asambleas', payload);
      }
      setExito(true);
      setTimeout(() => { onSuccess(); onClose(); }, 1200);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al guardar la asamblea. Intente de nuevo.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ModalWrapper
      titulo={initialData ? 'Editar Asamblea' : 'Registrar Nueva Asamblea'}
      subtitulo="Agendar o registrar resultados"
      onClose={onClose}
      color="#7c3aed"
    >
      {exito ? (
        <ExitoMsg mensaje={`¡Asamblea ${initialData ? 'actualizada' : 'registrada'}!`} />
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <ErrorBanner mensaje={error} />

          <SeccionHeader icono={<CalendarIcon size={16} />} titulo="Datos Generales" />

          <div style={gridDos}>
            <Campo label="Afectación colectiva *">
              <select required value={form.id_afectacion} onChange={e => setForm(prev => ({ ...prev, id_afectacion: e.target.value, id_ciclo_afectacion: '' }))} style={inputStyle}>
                <option value="">Seleccione una afectación</option>
                {afectaciones.filter(item => item.tipo_afectacion === 'colectivo').map(item => <option key={item.id_afectacion} value={item.id_afectacion}>Afectación #{item.id_afectacion}</option>)}
              </select>
            </Campo>

            <Campo label="Ciclo *">
              <select required value={form.id_ciclo_afectacion} onChange={e => {
                const ciclo = ciclos.find(item => item.id_ciclo_afectacion === Number(e.target.value));
                setForm(prev => ({ ...prev, id_ciclo_afectacion: e.target.value, contexto_proceso: ciclo?.tipo_ciclo || prev.contexto_proceso }));
              }} style={{...inputStyle, opacity: form.id_afectacion ? 1 : 0.6}} disabled={!form.id_afectacion}>
                <option value="">{form.id_afectacion ? (ciclos.length === 0 ? "Sin ciclos disponibles" : "Seleccione un ciclo") : "Seleccione primero una afectación"}</option>
                {ciclos.map(item => <option key={item.id_ciclo_afectacion} value={item.id_ciclo_afectacion}>{item.tipo_ciclo} #{item.consecutivo}</option>)}
              </select>
            </Campo>

            <Campo label="Tipo de Asamblea *">
              <select value={form.tipo_asamblea} onChange={e => set('tipo_asamblea', e.target.value)} style={inputStyle} required>
                {TIPOS_ASAMBLEA.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Campo>

            <Campo label="Contexto del Proceso *">
              <select value={form.contexto_proceso} onChange={e => set('contexto_proceso', e.target.value)} style={inputStyle} required>
                {CONTEXTOS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </Campo>

            <Campo label="Estatus de la Asamblea *">
              <select value={form.estatus_asamblea} onChange={e => set('estatus_asamblea', e.target.value)} style={inputStyle} required>
                <option value="programado">Programada</option>
                <option value="pendiente">Pendiente (reprogramada)</option>
                <option value="completo">Completada (Celebrada)</option>
              </select>
            </Campo>

            <Campo label="Resultado de Anuencia">
              <select value={form.resultado_anuencia} onChange={e => set('resultado_anuencia', e.target.value)} style={inputStyle}>
                <option value="pendiente">Pendiente</option>
                <option value="otorgada">Otorgada</option>
                <option value="negada">Negada</option>
                <option value="no_aplica">No Aplica</option>
              </select>
            </Campo>
          </div>

          <SeccionHeader icono={<CalendarIcon size={16} />} titulo="Fechas de Convocatoria" />

          <div style={gridDos}>
            <Campo label="Fecha Expedición 1ra Conv.">
              <input type="date" value={form.fecha_exp_1a} onChange={e => set('fecha_exp_1a', e.target.value)} style={inputStyle} />
            </Campo>
            <Campo label="Fecha Programada 1ra Conv.">
              <input type="date" value={form.fecha_prog_1a} onChange={e => set('fecha_prog_1a', e.target.value)} style={inputStyle} />
            </Campo>
            <Campo label="Fecha Expedición 2da Conv.">
              <input type="date" value={form.fecha_exp_2a} onChange={e => set('fecha_exp_2a', e.target.value)} style={inputStyle} />
            </Campo>
            <Campo label="Fecha Programada 2da Conv.">
              <input type="date" value={form.fecha_prog_2a} onChange={e => set('fecha_prog_2a', e.target.value)} style={inputStyle} />
            </Campo>
          </div>

          <Campo label="Fecha en que se REALIZÓ">
            <input type="date" value={form.fecha_realizada} onChange={e => set('fecha_realizada', e.target.value)} style={inputStyle} />
          </Campo>

          <SeccionHeader icono={<CalendarIcon size={16} />} titulo="Observaciones y Soportes" />

          <Campo label="Observaciones">
            <textarea
              value={form.observaciones}
              onChange={e => set('observaciones', e.target.value)}
              placeholder="Notas adicionales..."
              rows={2}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </Campo>

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={form.documentacion_disponible}
              onChange={e => set('documentacion_disponible', e.target.checked)}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '14px', color: '#334155' }}>¿Se cuenta con el Acta de Asamblea formal?</span>
          </label>

          {!form.documentacion_disponible && (
            <Campo label="Documentación Faltante">
              <input
                type="text"
                value={form.documentacion_faltante}
                onChange={e => set('documentacion_faltante', e.target.value)}
                placeholder="Indique si faltan firmas, registro en RAN, etc."
                style={inputStyle}
              />
            </Campo>
          )}

          <BotonesAccion
            onClose={onClose}
            guardando={guardando}
            labelGuardar={initialData ? 'Guardar Cambios' : 'Guardar Asamblea'}
            color="#7c3aed"
          />
        </form>
      )}
    </ModalWrapper>
  );
}
