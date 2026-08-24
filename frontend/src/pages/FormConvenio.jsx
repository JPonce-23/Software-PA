import React, { useEffect, useMemo, useState } from 'react';
import { FileCheck2, FileSignature } from 'lucide-react';
import api from '../api/axios';
import {
  ModalWrapper, SeccionHeader, Campo,
  ErrorBanner, ExitoMsg, BotonesAccion,
} from '../components/FormUI';
import { gridDos, inputStyle } from '../components/formStyles';

const TIPOS_CONVENIO = [
  { value: 'cop_original', label: 'Convenio de Ocupación Previa (Original)' },
  { value: 'modificatorio', label: 'Convenio Modificatorio' },
  { value: 'superficie_adicional', label: 'Superficie Adicional' },
  { value: 'obras_complementarias', label: 'Obras Complementarias' },
  { value: 'ampliacion', label: 'Ampliación' },
  { value: 'ampliacion_remanente', label: 'Ampliación Remanente' },
];

const valueOrNull = (value) => value === '' ? null : value;

export default function FormConvenio({
  idTramoNucleo, afectacion, asambleas = [], convenios = [], initialData = null,
  onSuccess, onClose,
}) {
  const [guardando, setGuardando] = useState(false);
  const [exito, setExito] = useState(false);
  const [error, setError] = useState(null);
  const [ciclos, setCiclos] = useState([]);
  const colectivo = afectacion?.tipo_afectacion === 'colectivo';

  const [form, setForm] = useState({
    tipo_convenio: initialData?.tipo_convenio || 'cop_original',
    fecha_firma: initialData?.fecha_firma || '',
    superficie_real_afectada_ha: initialData?.superficie_real_afectada_ha
      || (colectivo ? afectacion?.superficie_afectada_ha : '') || '',
    superficie_total_ha: initialData?.superficie_total_ha
      || (!colectivo ? afectacion?.superficie_afectada_ha : '') || '',
    superficie_adicional_ha: initialData?.superficie_adicional_ha || '',
    superficie_ampliacion_ha: initialData?.superficie_ampliacion_ha || '',
    monto_100: initialData?.monto_100 || '',
    monto_90: initialData?.monto_90 || '',
    monto_bdt: initialData?.monto_bdt || '',
    id_asamblea_autorizacion: initialData?.id_asamblea_autorizacion || '',
    id_ciclo_afectacion: initialData?.id_ciclo_afectacion || '',
    id_convenio_padre: initialData?.id_convenio_padre || '',
    ingreso_ran_fecha: initialData?.ingreso_ran_fecha || '',
    numero_solicitud_ingreso: initialData?.numero_solicitud_ingreso || '',
    calificacion_registral: initialData?.calificacion_registral || '',
    convenio_inscrito_fecha_ran: initialData?.convenio_inscrito_fecha_ran || '',
    documentacion_disponible: initialData?.documentacion_disponible || false,
    documentacion_faltante: initialData?.documentacion_faltante || '',
    observaciones: initialData?.observaciones || '',
  });

  const set = (campo, valor) => setForm((current) => ({ ...current, [campo]: valor }));

  useEffect(() => {
    if (!afectacion?.id_afectacion) return;
    api.get(`/afectaciones/${afectacion.id_afectacion}/ciclos`)
      .then(({ data }) => {
        setCiclos(data);
        if (!form.id_ciclo_afectacion) {
          const original = data.find((item) => item.tipo_ciclo === 'cop_original');
          if (original) set('id_ciclo_afectacion', String(original.id_ciclo_afectacion));
        }
      })
      .catch((requestError) => setError(
        requestError.response?.data?.detail || 'No fue posible cargar los ciclos.',
      ));
  // El formulario se reconstruye cuando cambia la afectación.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [afectacion?.id_afectacion]);

  const tiposPermitidos = useMemo(
    () => TIPOS_CONVENIO.filter((item) => colectivo
      ? ['cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'].includes(item.value)
      : ['cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'].includes(item.value)),
    [colectivo],
  );
  const padres = convenios.filter(
    (item) => item.id_afectacion === afectacion?.id_afectacion
      && item.tipo_convenio !== 'modificatorio',
  );
  const ciclosPermitidos = form.tipo_convenio === 'modificatorio'
    ? ciclos
    : ciclos.filter((item) => item.tipo_ciclo === form.tipo_convenio);
  const asambleasPermitidas = asambleas.filter((item) => (
    item.id_afectacion === afectacion?.id_afectacion
    && item.id_ciclo_afectacion === Number(form.id_ciclo_afectacion)
    && item.estatus_asamblea === 'completo'
    && item.resultado_anuencia === 'otorgada'
  ));

  const changeTipo = (tipo) => {
    const ciclo = ciclos.find((item) => item.tipo_ciclo === tipo);
    setForm((current) => ({
      ...current,
      tipo_convenio: tipo,
      id_ciclo_afectacion: ciclo ? String(ciclo.id_ciclo_afectacion) : '',
      id_convenio_padre: tipo === 'modificatorio' ? current.id_convenio_padre : '',
      id_asamblea_autorizacion: '',
    }));
  };

  const surfaceField = colectivo
    ? (form.tipo_convenio === 'superficie_adicional'
      ? ['superficie_adicional_ha', 'Superficie adicional (ha)']
      : form.tipo_convenio !== 'modificatorio'
        ? ['superficie_real_afectada_ha', 'Superficie real afectada (ha)'] : null)
    : (form.tipo_convenio === 'cop_original'
      ? ['superficie_total_ha', 'Superficie total (ha)']
      : ['ampliacion', 'ampliacion_remanente'].includes(form.tipo_convenio)
        ? ['superficie_ampliacion_ha', 'Superficie de ampliación (ha)'] : null);
  const ranAplicable = !(form.tipo_convenio === 'modificatorio' && !colectivo);
  const bdtAplicable = form.tipo_convenio !== 'obras_complementarias'
    && !(form.tipo_convenio === 'modificatorio' && !colectivo);

  const mutablePayload = () => ({
    fecha_firma: valueOrNull(form.fecha_firma),
    ingreso_ran_fecha: ranAplicable ? valueOrNull(form.ingreso_ran_fecha) : null,
    numero_solicitud_ingreso: ranAplicable ? valueOrNull(form.numero_solicitud_ingreso) : null,
    calificacion_registral: ranAplicable ? valueOrNull(form.calificacion_registral) : null,
    convenio_inscrito_fecha_ran: ranAplicable ? valueOrNull(form.convenio_inscrito_fecha_ran) : null,
    documentacion_disponible: form.documentacion_disponible,
    documentacion_faltante: form.documentacion_faltante || null,
    superficie_real_afectada_ha: surfaceField?.[0] === 'superficie_real_afectada_ha'
      ? valueOrNull(form.superficie_real_afectada_ha) : null,
    superficie_total_ha: surfaceField?.[0] === 'superficie_total_ha'
      ? valueOrNull(form.superficie_total_ha) : null,
    superficie_adicional_ha: surfaceField?.[0] === 'superficie_adicional_ha'
      ? valueOrNull(form.superficie_adicional_ha) : null,
    superficie_ampliacion_ha: surfaceField?.[0] === 'superficie_ampliacion_ha'
      ? valueOrNull(form.superficie_ampliacion_ha) : null,
    monto_100: valueOrNull(form.monto_100),
    monto_90: valueOrNull(form.monto_90),
    monto_bdt: bdtAplicable ? valueOrNull(form.monto_bdt) : null,
    observaciones: form.observaciones || null,
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    if (!afectacion) {
      setError('No se ha provisto una afectación válida.');
      return;
    }
    setGuardando(true);
    try {
      if (initialData) {
        await api.put(`/convenios/${initialData.id_convenio}`, mutablePayload());
      } else {
        await api.post('/convenios', {
          id_tramo_nucleo: idTramoNucleo,
          id_afectacion: afectacion.id_afectacion,
          id_ciclo_afectacion: Number(form.id_ciclo_afectacion),
          tipo_afectacion: afectacion.tipo_afectacion,
          tipo_convenio: form.tipo_convenio,
          id_convenio_padre: form.id_convenio_padre ? Number(form.id_convenio_padre) : null,
          id_asamblea_autorizacion: colectivo && form.id_asamblea_autorizacion
            ? Number(form.id_asamblea_autorizacion) : null,
          ...mutablePayload(),
        });
      }
      setExito(true);
      setTimeout(() => { onSuccess(); onClose(); }, 900);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Error al guardar el convenio.');
    } finally {
      setGuardando(false);
    }
  };

  const tipoLabel = colectivo ? 'Tierras de Uso Común' : 'Parcela Individual';
  const idLabel = colectivo
    ? `Afectación #${afectacion?.id_afectacion}`
    : `Parcela #${afectacion?.id_parcela || 'N/A'} · Afectación #${afectacion?.id_afectacion}`;

  return (
    <ModalWrapper
      titulo={initialData ? `Editar convenio (${tipoLabel})` : `Registrar convenio (${tipoLabel})`}
      subtitulo={idLabel}
      onClose={onClose}
      color="#059669"
      maxWidth="760px"
    >
      {exito ? <ExitoMsg mensaje={`Convenio ${initialData ? 'actualizado' : 'registrado'}.`} /> : (
        <form className="form-stack" onSubmit={handleSubmit}>
          <ErrorBanner mensaje={error} />
          <SeccionHeader icono={<FileSignature size={16} />} titulo="Datos del acuerdo" />
          <div style={gridDos}>
            <Campo label="Tipo de convenio *">
              <select disabled={Boolean(initialData)} required value={form.tipo_convenio} onChange={(event) => changeTipo(event.target.value)} style={inputStyle}>
                {tiposPermitidos.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </Campo>
            <Campo label="Ciclo de la afectación *">
              <select disabled={Boolean(initialData) || form.tipo_convenio === 'modificatorio'} required value={form.id_ciclo_afectacion} onChange={(event) => set('id_ciclo_afectacion', event.target.value)} style={inputStyle}>
                <option value="">Seleccione un ciclo</option>
                {ciclosPermitidos.map((item) => <option key={item.id_ciclo_afectacion} value={item.id_ciclo_afectacion}>{item.tipo_ciclo} #{item.consecutivo}</option>)}
              </select>
            </Campo>
            <Campo label="Fecha de firma">
              <input type="date" value={form.fecha_firma} onChange={(event) => set('fecha_firma', event.target.value)} style={inputStyle} />
            </Campo>
            {surfaceField && (
              <Campo label={surfaceField[1]}>
                <input type="number" step="0.0001" min="0" value={form[surfaceField[0]]} onChange={(event) => set(surfaceField[0], event.target.value)} style={inputStyle} />
              </Campo>
            )}
          </div>

          {form.tipo_convenio === 'modificatorio' && (
            <Campo label="Convenio base que se sustituye *">
              <select disabled={Boolean(initialData)} required value={form.id_convenio_padre} onChange={(event) => {
                const padre = padres.find((item) => item.id_convenio === Number(event.target.value));
                setForm((current) => ({ ...current, id_convenio_padre: event.target.value, id_ciclo_afectacion: padre ? String(padre.id_ciclo_afectacion) : '' }));
              }} style={inputStyle}>
                <option value="">Seleccione el convenio base</option>
                {padres.map((item) => <option key={item.id_convenio} value={item.id_convenio}>Convenio #{item.id_convenio} · {item.tipo_convenio}</option>)}
              </select>
            </Campo>
          )}

          {colectivo && form.tipo_convenio !== 'modificatorio' && (
            <Campo label="Asamblea de autorización *">
              <select disabled={Boolean(initialData)} required value={form.id_asamblea_autorizacion} onChange={(event) => set('id_asamblea_autorizacion', event.target.value)} style={inputStyle}>
                <option value="">Seleccione una asamblea con anuencia otorgada</option>
                {asambleasPermitidas.map((item) => <option key={item.id_asamblea} value={item.id_asamblea}>Asamblea #{item.id_asamblea} · {item.fecha_realizada || 'sin fecha'}</option>)}
              </select>
            </Campo>
          )}

          <SeccionHeader icono={<FileSignature size={16} />} titulo="Cantidades acordadas" />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
            <Campo label="Monto al 100% ($)"><input type="number" step="0.01" min="0" value={form.monto_100} onChange={(event) => set('monto_100', event.target.value)} style={inputStyle} /></Campo>
            <Campo label="Monto al 90% ($)"><input type="number" step="0.01" min="0" value={form.monto_90} onChange={(event) => set('monto_90', event.target.value)} style={inputStyle} /></Campo>
            {bdtAplicable && <Campo label="Monto BDT ($)"><input type="number" step="0.01" min="0" value={form.monto_bdt} onChange={(event) => set('monto_bdt', event.target.value)} style={inputStyle} /></Campo>}
          </div>

          {ranAplicable && (
            <>
              <SeccionHeader icono={<FileCheck2 size={16} />} titulo="Trámite ante el RAN" />
              <div style={gridDos}>
                <Campo label="Fecha de ingreso"><input type="date" value={form.ingreso_ran_fecha} onChange={(event) => set('ingreso_ran_fecha', event.target.value)} style={inputStyle} /></Campo>
                <Campo label="Número de solicitud"><input value={form.numero_solicitud_ingreso} onChange={(event) => set('numero_solicitud_ingreso', event.target.value)} style={inputStyle} /></Campo>
                <Campo label="Calificación registral"><input value={form.calificacion_registral} onChange={(event) => set('calificacion_registral', event.target.value)} style={inputStyle} /></Campo>
                <Campo label="Fecha de inscripción"><input type="date" value={form.convenio_inscrito_fecha_ran} onChange={(event) => set('convenio_inscrito_fecha_ran', event.target.value)} style={inputStyle} /></Campo>
              </div>
            </>
          )}

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input type="checkbox" checked={form.documentacion_disponible} onChange={(event) => set('documentacion_disponible', event.target.checked)} />
            Documentación soporte disponible
          </label>
          {!form.documentacion_disponible && <Campo label="Documentación faltante"><input value={form.documentacion_faltante} onChange={(event) => set('documentacion_faltante', event.target.value)} style={inputStyle} /></Campo>}
          <Campo label="Observaciones"><textarea rows={2} value={form.observaciones} onChange={(event) => set('observaciones', event.target.value)} style={inputStyle} /></Campo>

          <BotonesAccion onClose={onClose} guardando={guardando} labelGuardar={initialData ? 'Guardar cambios' : 'Registrar convenio'} color="#059669" />
          {initialData?.tipo_convenio === 'modificatorio' && !initialData?.vigencia_financiera_desde && (
            <button type="button" className="button" onClick={() => {
              setGuardando(true);
              api.post(`/convenios/${initialData.id_convenio}/activar-modificatorio`, { confirmar: true })
                .then(() => { onSuccess(); onClose(); })
                .catch((requestError) => setError(requestError.response?.data?.detail?.message || requestError.response?.data?.detail || 'No fue posible activar el modificatorio.'))
                .finally(() => setGuardando(false));
            }}>Activar sustitución financiera</button>
          )}
        </form>
      )}
    </ModalWrapper>
  );
}
