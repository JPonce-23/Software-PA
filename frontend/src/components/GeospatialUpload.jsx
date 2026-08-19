import React from 'react';
import { AlertTriangle, CheckCircle2, FileSearch, LoaderCircle, Upload, XCircle } from 'lucide-react';
import L from 'leaflet';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import api from '../api/axios';
import 'leaflet/dist/leaflet.css';
import './GeospatialUpload.css';

const TARGET_LABELS = {
  franja_derecho_via: 'derecho de vía',
  seccion_derecho_via: 'sección de derecho de vía',
  nucleo_agrario: 'núcleo agrario',
  parcela: 'parcela',
};

const stateIcon = {
  valido: <CheckCircle2 size={16} />,
  advertencia: <AlertTriangle size={16} />,
  error: <XCircle size={16} />,
};

function FitGeometry({ geometry }) {
  const map = useMap();

  React.useEffect(() => {
    const bounds = L.geoJSON(geometry).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 15 });
  }, [geometry, map]);

  return null;
}

export default function GeospatialUpload({ target, source, value, onChange, disabled = false }) {
  const [record, setRecord] = React.useState(null);
  const [selected, setSelected] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');

  const selectedFeature = record?.features?.find((feature) => feature.id_carga_feature === selected) || null;
  const validFeatures = record?.features?.filter((feature) => feature.estado !== 'error') || [];
  const layerGroups = React.useMemo(() => {
    const groups = new Map();
    (record?.features || []).forEach((feature) => {
      const key = feature.capa_origen || '__sin_capa__';
      if (!groups.has(key)) groups.set(key, { key, name: feature.capa_origen || 'Capa sin nombre', features: [] });
      groups.get(key).features.push(feature);
    });
    return [...groups.values()].map((group) => ({
      ...group,
      valid: group.features.filter((feature) => feature.estado !== 'error'),
      errors: group.features.filter((feature) => feature.estado === 'error'),
      types: [...new Set(group.features.filter((feature) => feature.estado !== 'error').map((feature) => feature.tipo_geometria))],
    }));
  }, [record]);
  const selectedLayer = layerGroups.find((group) => group.features.some((feature) => feature.id_carga_feature === selected)) || null;
  const isTrace = target === 'franja_derecho_via';
  const selectedLayerHasErrors = Boolean(isTrace && selectedLayer?.errors.length);
  const selectedGeometry = isTrace && selectedLayer
    ? { type: 'FeatureCollection', features: selectedLayer.valid.filter((feature) => feature.geometria_geojson).map((feature) => ({ type: 'Feature', properties: {}, geometry: feature.geometria_geojson })) }
    : selectedFeature?.geometria_geojson;

  const upload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setBusy(true);
    setError('');
    setRecord(null);
    setSelected(null);
    try {
      const body = new FormData();
      body.append('tipo_objetivo', target);
      body.append('file', file);
      if (source?.trim()) body.append('fuente', source.trim());
      const { data } = await api.post('/cargas-geoespaciales', body);
      setRecord(data);
      const valid = data.features.filter((feature) => feature.estado !== 'error');
      const groups = new Map();
      data.features.forEach((feature) => {
        const key = feature.capa_origen || '__sin_capa__';
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(feature);
      });
      if (target === 'franja_derecho_via' && groups.size === 1 && valid.length > 0) {
        setSelected(valid[0].id_carga_feature);
      } else if (target !== 'franja_derecho_via' && valid.length === 1) {
        setSelected(valid[0].id_carga_feature);
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible prevalidar el archivo.');
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!record || !selected) return;
    setBusy(true);
    setError('');
    try {
      await api.post(`/cargas-geoespaciales/${record.id_carga}/confirmar`, {
        id_carga_feature: selected,
      });
      onChange(selected);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible confirmar la geometría.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="geospatial-upload">
      <header>
        <div>
          <strong>Archivo geoespacial</strong>
          <span>Carga la geometría oficial del {TARGET_LABELS[target]}.</span>
        </div>
        {value && <span className="geospatial-upload-confirmed"><CheckCircle2 size={15} /> Geometría confirmada</span>}
      </header>
      <label className="geospatial-upload-picker">
        <Upload size={17} />
        <span>{busy ? 'Prevalidando archivo...' : 'Seleccionar archivo'}</span>
        <input type="file" accept=".kml,.geojson,.json,.zip" onChange={upload} disabled={busy || disabled} />
      </label>
      <small>Formatos admitidos: KML, GeoJSON y Shapefile (.zip).</small>
      {error && <p className="geospatial-upload-error"><XCircle size={15} />{error}</p>}
      {record && (
        <div className="geospatial-upload-result">
          <div className="geospatial-upload-meta">
            <span><b>Archivo</b>{record.nombre_original}</span>
            <span><b>Formato</b>{record.formato_detectado.toUpperCase()}</span>
            <span><b>CRS</b>{record.crs_original}</span>
            <span><b>Features</b>{record.total_features}</span>
          </div>
          <div className="geospatial-upload-counts">
            <span className="valid"><CheckCircle2 size={14} /> {record.features_validos} válidas</span>
            <span className="warning"><AlertTriangle size={14} /> {record.features_advertencia} advertencias</span>
            <span className="error"><XCircle size={14} /> {record.features_error} errores</span>
          </div>
          {validFeatures.length > 0 && (
            <div className="geospatial-feature-selector">
              <b>{isTrace ? 'Selecciona la capa que representa el trazo' : validFeatures.length === 1 ? 'Geometría encontrada' : 'Selecciona una geometría'}</b>
              {isTrace ? layerGroups.map((layer) => {
                const representative = layer.valid[0];
                const selectedHere = selectedLayer?.key === layer.key;
                const geometryLabel = layer.types.length === 1 ? layer.types[0] : 'Tipos mixtos';
                return (
                  <button
                    className={selectedHere ? 'selected' : ''}
                    type="button"
                    key={layer.key}
                    disabled={!representative}
                    onClick={() => representative && setSelected(representative.id_carga_feature)}
                  >
                    {layer.errors.length > 0 ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
                    {layer.name} · {layer.valid.length} geometrías · {geometryLabel}
                    {layer.errors.length > 0 && ` · ${layer.errors.length} con error`}
                  </button>
                );
              }) : validFeatures.map((feature) => (
                <button
                  className={selected === feature.id_carga_feature ? 'selected' : ''}
                  type="button"
                  key={feature.id_carga_feature}
                  onClick={() => setSelected(feature.id_carga_feature)}
                >
                  {stateIcon[feature.estado]}
                  Feature {feature.indice_feature + 1} · {feature.tipo_geometria}
                  {feature.advertencias?.length > 0 && ' · Revisar advertencia'}
                </button>
              ))}
            </div>
          )}
          {selectedGeometry && (
            <div className="geospatial-upload-map">
              <MapContainer center={[23.6345, -102.5528]} zoom={5} scrollWheelZoom={false}>
                <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <FitGeometry geometry={selectedGeometry} />
                <GeoJSON data={selectedGeometry} />
              </MapContainer>
            </div>
          )}
          {isTrace && selectedLayer && !selectedLayerHasErrors && <p className="geospatial-upload-warning"><AlertTriangle size={15} />Al confirmar, el sistema consolidará únicamente las {selectedLayer.valid.length} geometrías de la capa seleccionada.</p>}
          {isTrace && selectedLayerHasErrors && <p className="geospatial-upload-error"><XCircle size={15} />La capa seleccionada contiene errores. Selecciona otra capa o corrige el archivo de origen.</p>}
          {record.features.filter((feature) => feature.estado === 'error').flatMap((feature) => (
            feature.errores.map((issue) => (
              <p className="geospatial-upload-error" key={`${feature.id_carga_feature}-${issue.codigo}`}>
                <XCircle size={15} />Feature {feature.indice_feature + 1}: {issue.detalle}
              </p>
            ))
          ))}
          {selectedFeature?.errores?.map((issue) => <p className="geospatial-upload-error" key={issue.codigo}>{issue.detalle}</p>)}
          {selectedFeature?.advertencias?.map((issue) => <p className="geospatial-upload-warning" key={issue.codigo}>{issue.detalle}</p>)}
          <button className="geospatial-upload-confirm" type="button" disabled={!selected || busy || selectedLayerHasErrors} onClick={confirm}>
            {busy ? <LoaderCircle className="geospatial-upload-spin" size={16} /> : <FileSearch size={16} />}
            {isTrace ? 'Confirmar capa seleccionada' : 'Confirmar geometría seleccionada'}
          </button>
        </div>
      )}
    </section>
  );
}
