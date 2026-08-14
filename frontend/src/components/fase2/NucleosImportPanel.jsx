import React, { useEffect, useMemo, useState } from 'react';
import { CheckSquare, Upload, X } from 'lucide-react';

import api from '../../api/axios';


export default function NucleosImportPanel({ role, onImportSuccess }) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [tramos, setTramos] = useState([]);
  const [municipios, setMunicipios] = useState([]);
  const [entidades, setEntidades] = useState([]);
  const [selectedTramos, setSelectedTramos] = useState([]);
  const [entidadFallback, setEntidadFallback] = useState('');
  const [municipioFallback, setMunicipioFallback] = useState('');
  const [tipoFallback, setTipoFallback] = useState('ejido');
  const [globalMode, setGlobalMode] = useState(role === 'admin');
  const [contextLoading, setContextLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setContextLoading(true);
    setError(null);
    Promise.all([api.get('/tramos'), api.get('/catalogos/municipios'), api.get('/catalogos/entidades')])
      .then(([tramosResponse, municipiosResponse, entidadesResponse]) => {
        setTramos(tramosResponse.data);
        setMunicipios(municipiosResponse.data);
        setEntidades(entidadesResponse.data);
      })
      .catch(() => setError('No fue posible cargar el contexto de importación.'))
      .finally(() => setContextLoading(false));
  }, [isOpen]);

  const allSelected = useMemo(
    () => tramos.length > 0 && selectedTramos.length === tramos.length,
    [selectedTramos, tramos],
  );

  const toggleTramo = (idTramo) => {
    setSelectedTramos((current) => current.includes(idTramo)
      ? current.filter((id) => id !== idTramo)
      : [...current, idTramo]);
  };

  const handleImport = async () => {
    if (!file) {
      setError('Seleccione un archivo GeoJSON.');
      return;
    }
    if (!globalMode && selectedTramos.length === 0) {
      setError('Seleccione al menos un tramo.');
      return;
    }

    const form = new FormData();
    form.append('file', file);
    if (entidadFallback) form.append('id_entidad_fallback', entidadFallback);
    if (municipioFallback) form.append('id_municipio_fallback', municipioFallback);
    if (tipoFallback) form.append('tipo_nucleo_fallback', tipoFallback);
    if (!globalMode) {
      selectedTramos.forEach((idTramo) => form.append('ids_tramo_contexto', idTramo));
    }

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post('/nucleos/importacion-masiva', form);
      setResult(data.mensaje);
      setFile(null);
      if (onImportSuccess) onImportSuccess();
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      if (detail?.errores) {
        setError(detail.errores.map((item) => `Feature ${item.index}: ${item.motivo}`).join('\n'));
      } else {
        setError(typeof detail === 'string' ? detail : 'No fue posible completar la importación.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button className="map-import-button" type="button" onClick={() => setIsOpen(true)} title="Importar núcleos agrarios">
        <Upload size={18} />
        Importar núcleos
      </button>

      {isOpen && (
        <div className="import-modal-backdrop" role="presentation">
          <section className="import-modal" role="dialog" aria-modal="true" aria-labelledby="nucleos-import-title">
            <header className="import-modal-header">
              <h3 id="nucleos-import-title">Importar núcleos agrarios</h3>
              <button className="icon-button" type="button" onClick={() => setIsOpen(false)} title="Cerrar">
                <X size={20} />
              </button>
            </header>

            {role === 'admin' && (
              <label className="check-row">
                <input type="checkbox" checked={globalMode} onChange={(event) => setGlobalMode(event.target.checked)} />
                Importación global
              </label>
            )}

            {!globalMode && (
              <fieldset className="tramo-selector">
                <legend>Tramos autorizados</legend>
                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => setSelectedTramos(allSelected ? [] : tramos.map((tramo) => tramo.id_tramo))}
                  />
                  Todos mis tramos
                </label>
                <div className="tramo-options">
                  {contextLoading && <span>Cargando tramos...</span>}
                  {!contextLoading && tramos.length === 0 && (
                    <span>No tiene tramos activos asignados.</span>
                  )}
                  {tramos.map((tramo) => (
                    <label className="check-row" key={tramo.id_tramo}>
                      <input
                        type="checkbox"
                        checked={selectedTramos.includes(tramo.id_tramo)}
                        onChange={() => toggleTramo(tramo.id_tramo)}
                      />
                      {tramo.nombre_tramo}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            <label className="import-field">
              Entidad predeterminada
              <select value={entidadFallback} onChange={(event) => setEntidadFallback(event.target.value)}>
                <option value="">Usar la entidad de cada feature</option>
                {entidades.map((entidad) => (
                  <option key={entidad.id_entidad} value={entidad.id_entidad}>
                    {entidad.nombre}
                  </option>
                ))}
              </select>
            </label>

            <label className="import-field">
              Municipio predeterminado
              <select value={municipioFallback} onChange={(event) => setMunicipioFallback(event.target.value)}>
                <option value="">Usar el municipio de cada feature</option>
                {municipios.filter((municipio) => !entidadFallback || municipio.id_entidad === Number(entidadFallback)).map((municipio) => (
                  <option key={municipio.id_municipio} value={municipio.id_municipio}>
                    {municipio.nombre}
                  </option>
                ))}
              </select>
            </label>

            <label className="import-field">
              Tipo predeterminado
              <select value={tipoFallback} onChange={(event) => setTipoFallback(event.target.value)}>
                <option value="ejido">Ejido</option>
                <option value="comunidad">Comunidad</option>
                <option value="">Usar el tipo de cada feature</option>
              </select>
            </label>

            <label className="import-field">
              Archivo GeoJSON
              <input type="file" accept=".geojson,.json,application/geo+json,application/json" onChange={(event) => setFile(event.target.files[0] || null)} />
            </label>

            {error && <div className="import-error">{error}</div>}
            {result && <div className="import-success">{result}</div>}

            <button className="import-submit" type="button" disabled={contextLoading || loading || (role === 'geografo' && tramos.length === 0)} onClick={handleImport}>
              <CheckSquare size={18} />
              {loading ? 'Procesando' : 'Importar'}
            </button>
          </section>
        </div>
      )}
    </>
  );
}
