import React from 'react';
import { CheckCircle2, FileSearch, Upload, X } from 'lucide-react';
import api from '../api/axios';

const tipos = [
  { value: 'tramos', label: 'Tramos' },
  { value: 'nucleos', label: 'Núcleos agrarios' },
  { value: 'derecho_via', label: 'Derecho de vía' },
  { value: 'parcelas', label: 'Parcelas' },
  { value: 'cruces_operativos', label: 'Cruces operativos' },
];

const apiError = (error) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join('\n');
  return 'No fue posible procesar la importación.';
};

export default function ImportacionTerritorialPanel({ role, data, activeTab, onImported }) {
  const [open, setOpen] = React.useState(false);
  const [tipo, setTipo] = React.useState(tipoFromTab(activeTab));
  const [file, setFile] = React.useState(null);
  const [context, setContext] = React.useState({
    id_proyecto: '',
    id_tramo: '',
    id_nucleo: '',
    id_tramo_nucleo: '',
    id_entidad_fallback: '',
    id_municipio_fallback: '',
    fuente: '',
    fecha_vigencia_inicio: '',
    ancho_izquierdo_m: '',
    ancho_derecho_m: '',
    tipo_nucleo_fallback: 'ejido',
    ids_tramo_contexto: [],
  });
  const [preview, setPreview] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const allowedTypes = React.useMemo(
    () => tipos.filter((item) => role === 'admin' || item.value !== 'cruces_operativos'),
    [role],
  );

  React.useEffect(() => {
    if (open) setTipo(tipoFromTab(activeTab));
  }, [activeTab, open]);

  const update = (key, value) => {
    setContext((current) => ({ ...current, [key]: value }));
    setPreview(null);
  };

  const toggleTramoContexto = (idTramo) => {
    setContext((current) => {
      const selected = current.ids_tramo_contexto.includes(idTramo);
      return {
        ...current,
        ids_tramo_contexto: selected
          ? current.ids_tramo_contexto.filter((id) => id !== idTramo)
          : [...current.ids_tramo_contexto, idTramo],
      };
    });
    setPreview(null);
  };

  const buildForm = () => {
    const form = new FormData();
    form.append('file', file);
    Object.entries(context).forEach(([key, value]) => {
      if (key === 'ids_tramo_contexto') {
        value.forEach((id) => form.append(key, id));
      } else if (value !== '' && value != null) {
        form.append(key, value);
      }
    });
    return form;
  };

  const handlePreview = async () => {
    if (!file) {
      setError('Selecciona un archivo .geojson o .json con contenido GeoJSON.');
      return;
    }
    setLoading(true);
    setError('');
    setPreview(null);
    try {
      const { data: response } = await api.post(`/importaciones-territoriales/${tipo}/previsualizar`, buildForm());
      setPreview(response);
    } catch (requestError) {
      setError(apiError(requestError));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview || preview.errores > 0) return;
    setLoading(true);
    setError('');
    try {
      await api.post(`/importaciones-territoriales/${tipo}/confirmar`, {
        archivo_sha256: preview.archivo_sha256,
        items: preview.items,
      });
      setOpen(false);
      setFile(null);
      setPreview(null);
      if (onImported) await onImported();
    } catch (requestError) {
      setError(apiError(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button className="admin-button secondary" type="button" onClick={() => setOpen(true)}>
        <Upload size={16} /> Importar GeoJSON
      </button>
      {open && (
        <div className="import-modal-backdrop" role="presentation">
          <section className="territorial-import-modal" role="dialog" aria-modal="true" aria-labelledby="territorial-import-title">
            <header className="import-modal-header">
              <div>
                <h3 id="territorial-import-title">Importación territorial GeoJSON</h3>
                <p>Previsualiza y confirma antes de guardar.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setOpen(false)} title="Cerrar"><X size={20} /></button>
            </header>

            <div className="territorial-import-grid">
              <label className="import-field">
                Tipo de importación
                <select value={tipo} onChange={(event) => { setTipo(event.target.value); setPreview(null); }}>
                  {allowedTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
              {tipo === 'tramos' && <ProyectoSelect data={data} value={context.id_proyecto} onChange={(value) => update('id_proyecto', value)} />}
              {(tipo === 'derecho_via' || tipo === 'cruces_operativos') && <TramoSelect data={data} value={context.id_tramo} onChange={(value) => update('id_tramo', value)} />}
              {(tipo === 'parcelas' || tipo === 'cruces_operativos') && <NucleoSelect data={data} value={context.id_nucleo} onChange={(value) => update('id_nucleo', value)} />}
              {tipo === 'nucleos' && <EntidadSelect data={data} value={context.id_entidad_fallback} onChange={(value) => { update('id_entidad_fallback', value); update('id_municipio_fallback', ''); }} />}
              {tipo === 'nucleos' && <MunicipioSelect data={data} idEntidad={context.id_entidad_fallback} value={context.id_municipio_fallback} onChange={(value) => update('id_municipio_fallback', value)} />}
              {tipo === 'nucleos' && (
                <label className="import-field">Tipo predeterminado
                  <select value={context.tipo_nucleo_fallback} onChange={(event) => update('tipo_nucleo_fallback', event.target.value)}>
                    <option value="ejido">Ejido</option>
                    <option value="comunidad">Comunidad</option>
                    <option value="">Usar el tipo de cada feature</option>
                  </select>
                </label>
              )}
              {tipo === 'derecho_via' && (
                <>
                  <label className="import-field">Fuente<input value={context.fuente} onChange={(event) => update('fuente', event.target.value)} /></label>
                  <label className="import-field">Inicio de vigencia<input type="date" value={context.fecha_vigencia_inicio} onChange={(event) => update('fecha_vigencia_inicio', event.target.value)} /></label>
                  <label className="import-field">Ancho izquierdo (m)<input type="number" step="0.01" min="0.01" value={context.ancho_izquierdo_m} onChange={(event) => update('ancho_izquierdo_m', event.target.value)} /></label>
                  <label className="import-field">Ancho derecho (m)<input type="number" step="0.01" min="0.01" value={context.ancho_derecho_m} onChange={(event) => update('ancho_derecho_m', event.target.value)} /></label>
                </>
              )}
              <label className="import-field">
                Archivo GeoJSON
                <input type="file" accept=".geojson,.json,application/geo+json,application/json" onChange={(event) => { setFile(event.target.files[0] || null); setPreview(null); }} />
              </label>
            </div>

            {tipo === 'nucleos' && role === 'geografo' && (
              <fieldset className="tramo-selector compact">
                <legend>Tramos de contexto</legend>
                {data.tramos.filter((tramo) => tramo.activo).map((tramo) => (
                  <label className="check-row" key={tramo.id_tramo}>
                    <input type="checkbox" checked={context.ids_tramo_contexto.includes(tramo.id_tramo)} onChange={() => toggleTramoContexto(tramo.id_tramo)} />
                    {tramo.clave_tramo} · {tramo.nombre_tramo}
                  </label>
                ))}
              </fieldset>
            )}

            {error && <div className="import-error">{error}</div>}
            {preview && <PreviewTable preview={preview} />}

            <footer className="territorial-import-actions">
              <button className="admin-button secondary" type="button" onClick={handlePreview} disabled={loading}>
                <FileSearch size={16} /> {loading ? 'Validando...' : 'Previsualizar'}
              </button>
              <button className="admin-button" type="button" onClick={handleConfirm} disabled={!preview || preview.errores > 0 || loading}>
                <CheckCircle2 size={16} /> Confirmar importación
              </button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}

function tipoFromTab(tab) {
  if (tab === 'tramos') return 'tramos';
  if (tab === 'nucleos') return 'nucleos';
  if (tab === 'relaciones') return 'cruces_operativos';
  return 'tramos';
}

function ProyectoSelect({ data, value, onChange }) {
  return (
    <label className="import-field">Proyecto
      <select required value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Selecciona</option>
        {data.proyectos.filter((item) => item.activo).map((item) => (
          <option key={item.id_proyecto} value={item.id_proyecto}>{item.clave_proyecto} · {item.nombre_proyecto}</option>
        ))}
      </select>
    </label>
  );
}

function TramoSelect({ data, value, onChange }) {
  return (
    <label className="import-field">Tramo
      <select required value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Selecciona</option>
        {data.tramos.filter((item) => item.activo).map((item) => (
          <option key={item.id_tramo} value={item.id_tramo}>{item.clave_tramo} · {item.nombre_tramo}</option>
        ))}
      </select>
    </label>
  );
}

function NucleoSelect({ data, value, onChange }) {
  return (
    <label className="import-field">Núcleo
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Usar id_nucleo del archivo</option>
        {data.nucleos.filter((item) => item.activo).map((item) => (
          <option key={item.id_nucleo} value={item.id_nucleo}>{item.nombre_nucleo}</option>
        ))}
      </select>
    </label>
  );
}

function EntidadSelect({ data, value, onChange }) {
  return (
    <label className="import-field">Entidad predeterminada
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Usar entidad del archivo</option>
        {data.entidades.map((item) => (
          <option key={item.id_entidad} value={item.id_entidad}>{item.nombre}</option>
        ))}
      </select>
    </label>
  );
}

function MunicipioSelect({ data, idEntidad, value, onChange }) {
  return (
    <label className="import-field">Municipio predeterminado
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Usar municipio de cada feature</option>
        {data.municipios.filter((item) => !idEntidad || item.id_entidad === Number(idEntidad)).map((item) => (
          <option key={item.id_municipio} value={item.id_municipio}>{item.nombre}</option>
        ))}
      </select>
    </label>
  );
}

function PreviewTable({ preview }) {
  return (
    <div className="territorial-preview">
      <div className="territorial-preview-summary">
        <strong>{preview.validos}</strong> válidos · <strong>{preview.errores}</strong> errores · <strong>{preview.advertencias}</strong> advertencias
      </div>
      <div className="territorial-preview-table-wrap">
        <table className="admin-table territorial-preview-table">
          <thead><tr><th>#</th><th>Estado</th><th>Registro</th><th>Detalle</th></tr></thead>
          <tbody>
            {preview.items.map((item) => (
              <tr key={item.index} className={item.estado === 'error' ? 'inactive' : ''}>
                <td>{item.index}</td>
                <td><span className={`admin-status ${item.estado === 'error' ? 'inactive' : 'active'}`}>{item.estado}</span></td>
                <td>{item.resumen}</td>
                <td>{[...item.errores, ...item.advertencias].join('\n') || 'Listo para confirmar'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
