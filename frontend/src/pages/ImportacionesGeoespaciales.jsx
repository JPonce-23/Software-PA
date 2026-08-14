import React from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Download,
  FileSearch,
  LoaderCircle,
  Pencil,
  RefreshCw,
  Upload,
  X,
  XCircle,
} from 'lucide-react';

import api from '../api/axios';
import './ImportacionesGeoespaciales.css';


const MAPPING_FIELDS = [
  ['nombre_nucleo', 'Nombre del núcleo', true],
  ['tipo_nucleo', 'Tipo de núcleo', true],
  ['entidad', 'Entidad', false],
  ['clave_entidad_inegi', 'Clave INEGI entidad', false],
  ['municipio', 'Municipio', false],
  ['clave_municipio_inegi', 'Clave INEGI municipio', false],
  ['id_entidad_fuente', 'ID entidad de fuente', false],
  ['id_municipio_fuente', 'ID municipio de fuente', false],
  ['id_nucleo_fuente', 'ID núcleo de fuente', false],
  ['comunidad_indigena', 'Comunidad indígena', false],
  ['residencia', 'Residencia', false],
];

const STATUS_META = {
  valido: { label: 'Válido', icon: CheckCircle2, tone: 'valid' },
  advertencia: { label: 'Advertencia', icon: AlertTriangle, tone: 'warning' },
  error: { label: 'Error', icon: XCircle, tone: 'error' },
  importado: { label: 'Importado', icon: Check, tone: 'imported' },
  descartado: { label: 'Descartado', icon: X, tone: 'muted' },
  pendiente_revision: { label: 'Pendiente', icon: LoaderCircle, tone: 'muted' },
};

const PROCESSING_STATES = new Set(['analizando', 'normalizando', 'resolviendo', 'confirmando', 'importando']);

function apiError(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ');
  return 'No fue posible completar la operación.';
}

export default function ImportacionesGeoespaciales() {
  const [imports, setImports] = React.useState([]);
  const [profiles, setProfiles] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [features, setFeatures] = React.useState({ total: 0, items: [] });
  const [filter, setFilter] = React.useState('todos');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [acceptWarnings, setAcceptWarnings] = React.useState(false);
  const [editingFeature, setEditingFeature] = React.useState(null);

  const loadImports = React.useCallback(async () => {
    const [{ data: importRecords }, { data: profileRecords }] = await Promise.all([
      api.get('/importaciones-geoespaciales'),
      api.get('/importaciones-geoespaciales/perfiles'),
    ]);
    setImports(importRecords);
    setProfiles(profileRecords);
    return importRecords;
  }, []);

  const loadSelected = React.useCallback(async (id, statusFilter = filter) => {
    const params = statusFilter === 'todos' ? {} : { estado: statusFilter };
    const [{ data: record }, { data: featurePage }] = await Promise.all([
      api.get(`/importaciones-geoespaciales/${id}`),
      api.get(`/importaciones-geoespaciales/${id}/features`, { params }),
    ]);
    setSelected(record);
    setFeatures(featurePage);
    return record;
  }, [filter]);

  React.useEffect(() => {
    loadImports().catch((requestError) => setError(apiError(requestError)));
  }, [loadImports]);

  React.useEffect(() => {
    if (!selected?.id_importacion) return undefined;
    const timer = window.setInterval(async () => {
      if (!PROCESSING_STATES.has(selected.estado)) return;
      try {
        const record = await loadSelected(selected.id_importacion);
        if (!PROCESSING_STATES.has(record.estado)) await loadImports();
      } catch (requestError) {
        setError(apiError(requestError));
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [loadImports, loadSelected, selected]);

  const chooseImport = async (record) => {
    setError('');
    setFilter('todos');
    try {
      await loadSelected(record.id_importacion, 'todos');
    } catch (requestError) {
      setError(apiError(requestError));
    }
  };

  const applyFilter = async (nextFilter) => {
    setFilter(nextFilter);
    if (!selected) return;
    try {
      await loadSelected(selected.id_importacion, nextFilter);
    } catch (requestError) {
      setError(apiError(requestError));
    }
  };

  return (
    <section className="geo-import-page">
      <header className="geo-import-toolbar">
        <div>
          <h2>Importaciones geoespaciales</h2>
          <span>{imports.length} archivos registrados</span>
        </div>
        <button className="geo-button primary" type="button" onClick={() => setSelected({ nuevo: true })}>
          <Upload size={17} /> Cargar archivo
        </button>
      </header>

      {error && <div className="geo-notice error"><XCircle size={18} />{error}</div>}

      <div className="geo-import-layout">
        <aside className="geo-import-list" aria-label="Archivos importados">
          {imports.length === 0 && <div className="geo-empty">Sin archivos registrados</div>}
          {imports.map((record) => (
            <button
              className={selected?.id_importacion === record.id_importacion ? 'active' : ''}
              key={record.id_importacion}
              type="button"
              onClick={() => chooseImport(record)}
            >
              <strong>{record.nombre_original}</strong>
              <span>{record.formato_detectado.toUpperCase()} · {record.total_features} features</span>
              <StatusPill status={record.estado} />
            </button>
          ))}
        </aside>

        <div className="geo-import-workspace">
          {!selected && <div className="geo-empty large"><FileSearch size={30} />Seleccione una importación</div>}
          {selected?.nuevo && (
            <UploadPanel
              busy={loading}
              onCancel={() => setSelected(null)}
              onUpload={async (form) => {
                setLoading(true);
                setError('');
                try {
                  const { data } = await api.post('/importaciones-geoespaciales', form);
                  await loadImports();
                  await chooseImport(data);
                } catch (requestError) {
                  setError(apiError(requestError));
                } finally {
                  setLoading(false);
                }
              }}
            />
          )}
          {selected?.id_importacion && (
            <ImportWorkspace
              record={selected}
              profiles={profiles}
              features={features}
              filter={filter}
              busy={loading}
              onFilter={applyFilter}
              onRefresh={() => loadSelected(selected.id_importacion)}
              onEdit={setEditingFeature}
              onProcess={async (mappingPayload) => {
                setLoading(true);
                setError('');
                try {
                  await api.put(`/importaciones-geoespaciales/${selected.id_importacion}/mapeo`, mappingPayload);
                  await api.post(`/importaciones-geoespaciales/${selected.id_importacion}/procesar`);
                  await loadImports();
                  await loadSelected(selected.id_importacion);
                } catch (requestError) {
                  setError(apiError(requestError));
                } finally {
                  setLoading(false);
                }
              }}
              onConfirm={() => setConfirmOpen(true)}
            />
          )}
        </div>
      </div>

      {confirmOpen && selected && (
        <ConfirmDialog
          record={selected}
          acceptWarnings={acceptWarnings}
          onAcceptWarnings={setAcceptWarnings}
          onClose={() => setConfirmOpen(false)}
          onConfirm={async () => {
            setLoading(true);
            setError('');
            try {
              await api.post(`/importaciones-geoespaciales/${selected.id_importacion}/confirmar`, {
                aceptar_advertencias: acceptWarnings,
              });
              setConfirmOpen(false);
              await loadSelected(selected.id_importacion);
            } catch (requestError) {
              setError(apiError(requestError));
            } finally {
              setLoading(false);
            }
          }}
        />
      )}

      {editingFeature && selected && (
        <FeatureDialog
          feature={editingFeature}
          onClose={() => setEditingFeature(null)}
          onSave={async (payload) => {
            setLoading(true);
            setError('');
            try {
              await api.patch(
                `/importaciones-geoespaciales/${selected.id_importacion}/features/${editingFeature.id_importacion_feature}`,
                payload,
              );
              setEditingFeature(null);
              await loadSelected(selected.id_importacion);
            } catch (requestError) {
              setError(apiError(requestError));
            } finally {
              setLoading(false);
            }
          }}
        />
      )}
    </section>
  );
}

function UploadPanel({ busy, onCancel, onUpload }) {
  const [file, setFile] = React.useState(null);
  const [source, setSource] = React.useState('RAN');
  return (
    <form className="geo-upload-panel" onSubmit={(event) => {
      event.preventDefault();
      if (!file || !source.trim()) return;
      const form = new FormData();
      form.append('file', file);
      form.append('fuente', source.trim());
      onUpload(form);
    }}>
      <header><h3>Nueva importación</h3><button className="geo-icon-button" type="button" title="Cerrar" onClick={onCancel}><X size={18} /></button></header>
      <div className="geo-form-grid">
        <label>Fuente<input maxLength="200" required value={source} onChange={(event) => setSource(event.target.value)} /></label>
        <label>Archivo KML o GeoJSON<input required type="file" accept=".kml,.geojson,.json" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
      </div>
      <footer><button className="geo-button primary" disabled={busy || !file || !source.trim()} type="submit"><Upload size={17} />{busy ? 'Inspeccionando' : 'Registrar archivo'}</button></footer>
    </form>
  );
}

function ImportWorkspace({ record, profiles, features, filter, busy, onFilter, onRefresh, onEdit, onProcess, onConfirm }) {
  const [mapping, setMapping] = React.useState(record.mapeo || {});
  const [options, setOptions] = React.useState(record.opciones_mapeo || {});
  const processing = PROCESSING_STATES.has(record.estado);
  const progress = record.total_features ? Math.round((record.features_procesados / record.total_features) * 100) : 0;
  React.useEffect(() => {
    setMapping(record.mapeo || {});
    setOptions(record.opciones_mapeo || {});
  }, [record.id_importacion, record.mapeo, record.opciones_mapeo]);

  const mappingReady = Boolean(
    mapping.nombre_nucleo
    && mapping.tipo_nucleo
    && (mapping.entidad || mapping.clave_entidad_inegi)
    && (mapping.municipio || mapping.clave_municipio_inegi || mapping.id_municipio_fuente)
  );
  return (
    <>
      <header className="geo-record-header">
        <div><h3>{record.nombre_original}</h3><span>SHA-256 {record.sha256}</span></div>
        <div className="geo-record-actions">
          <a className="geo-icon-button" href={`/api/importaciones-geoespaciales/${record.id_importacion}/reporte.csv`} title="Descargar reporte"><Download size={18} /></a>
          <button className="geo-icon-button" type="button" title="Actualizar" onClick={onRefresh}><RefreshCw size={18} /></button>
        </div>
      </header>

      <div className="geo-metadata">
        <span><b>Formato</b>{record.formato_detectado.toUpperCase()}</span>
        <span><b>CRS original</b>{record.crs_original || 'No identificado'}</span>
        <span><b>Fuente</b>{record.fuente}</span>
        <span><b>Estado</b><StatusPill status={record.estado} /></span>
      </div>

      {processing && (
        <div className="geo-progress">
          <div><span>{record.estado.replace('_', ' ')}</span><strong>{record.features_procesados.toLocaleString()} / {record.total_features.toLocaleString()}</strong></div>
          <progress max="100" value={progress} />
          <span>{progress} %</span>
        </div>
      )}
      {record.error_detalle && <div className="geo-notice error"><XCircle size={18} />{record.error_detalle}</div>}

      {['subido', 'fallido'].includes(record.estado) && record.error_codigo !== 'CONFIRMACION_FALLIDA' && (
        <MappingPanel
          columns={record.columnas_detectadas}
          profiles={profiles}
          source={record.fuente}
          mapping={mapping}
          options={options}
          onMapping={setMapping}
          onOptions={setOptions}
          disabled={busy}
          ready={mappingReady}
          onProcess={onProcess}
        />
      )}

      {['listo_revision', 'confirmando', 'importando', 'completado'].includes(record.estado) && (
        <>
          <Summary record={record} />
          <div className="geo-feature-toolbar">
            <div className="geo-segments" role="group" aria-label="Filtrar features">
              {['todos', 'valido', 'advertencia', 'error', 'importado'].map((value) => (
                <button className={filter === value ? 'active' : ''} type="button" key={value} onClick={() => onFilter(value)}>{value === 'todos' ? 'Todos' : STATUS_META[value].label}</button>
              ))}
            </div>
            {record.estado === 'listo_revision' && (
              <button className="geo-button primary" type="button" disabled={record.validos + record.advertencias === 0} onClick={onConfirm}><CheckCircle2 size={17} />Confirmar importación</button>
            )}
          </div>
          <FeatureTable features={features.items} editable={record.estado === 'listo_revision'} onEdit={onEdit} />
          {features.total > features.items.length && <div className="geo-table-note">Mostrando {features.items.length} de {features.total} registros</div>}
        </>
      )}
    </>
  );
}

function MappingPanel({ columns, profiles, source, mapping, options, onMapping, onOptions, disabled, ready, onProcess }) {
  const [profileId, setProfileId] = React.useState('');
  const [saveProfile, setSaveProfile] = React.useState(false);
  const [profileName, setProfileName] = React.useState('');
  const setField = (target, source) => {
    const next = { ...mapping };
    if (source) next[target] = source;
    else delete next[target];
    onMapping(next);
  };
  const applyProfile = (value) => {
    setProfileId(value);
    const profile = profiles.find((item) => String(item.id_perfil) === value);
    if (!profile) return;
    onMapping(Object.fromEntries(
      Object.entries(profile.mapeo).filter(([, column]) => columns.includes(column)),
    ));
    onOptions(profile.opciones || {});
  };
  const submit = () => {
    const payload = { mapeo: mapping, opciones: options };
    if (profileId) payload.id_perfil = Number(profileId);
    if (saveProfile) {
      payload.guardar_perfil = {
        nombre: profileName.trim(),
        fuente: source,
        mapeo: mapping,
        opciones: options,
      };
    }
    onProcess(payload);
  };
  return (
    <section className="geo-mapping-panel">
      <header><h4>Mapeo de columnas</h4><span>{columns.length} columnas detectadas</span></header>
      <div className="geo-profile-row">
        <label>Perfil reutilizable
          <select value={profileId} onChange={(event) => applyProfile(event.target.value)}>
            <option value="">Mapeo manual</option>
            {profiles.map((profile) => <option key={profile.id_perfil} value={profile.id_perfil}>{profile.nombre} · {profile.fuente}</option>)}
          </select>
        </label>
        <label className="geo-check"><input type="checkbox" checked={saveProfile} onChange={(event) => setSaveProfile(event.target.checked)} />Guardar como perfil</label>
        {saveProfile && <label>Nombre del perfil<input maxLength="150" required value={profileName} onChange={(event) => setProfileName(event.target.value)} /></label>}
      </div>
      <div className="geo-mapping-grid">
        {MAPPING_FIELDS.map(([target, label, required]) => (
          <label key={target}>{label}{required && <b>*</b>}
            <select value={mapping[target] || ''} onChange={(event) => setField(target, event.target.value)}>
              <option value="">Sin asignar</option>
              {columns.map((column) => <option value={column} key={column}>{column}</option>)}
            </select>
          </label>
        ))}
      </div>
      <div className="geo-policy-row">
        <label>Semántica de ID municipal
          <select value={options.id_municipio_fuente_semantica || ''} onChange={(event) => onOptions({ ...options, id_municipio_fuente_semantica: event.target.value || undefined })}>
            <option value="">Identificador de procedencia</option>
            <option value="clave_inegi_completa">Clave INEGI completa</option>
            <option value="clave_municipal_inegi">Clave municipal INEGI dentro de entidad</option>
          </select>
        </label>
        <label>Alcance del ID de núcleo
          <select value={options.alcance_id_nucleo_fuente || 'territorial'} onChange={(event) => onOptions({ ...options, alcance_id_nucleo_fuente: event.target.value })}>
            <option value="territorial">Único dentro de entidad y municipio</option>
            <option value="global">Único en toda la fuente</option>
          </select>
        </label>
        <label className="geo-check"><input type="checkbox" checked={Boolean(options.unir_partes_mismo_id)} onChange={(event) => onOptions({ ...options, unir_partes_mismo_id: event.target.checked })} />Unir partes con el mismo ID externo</label>
      </div>
      <footer><button className="geo-button primary" type="button" disabled={disabled || !ready || (saveProfile && !profileName.trim())} onClick={submit}><FileSearch size={17} />Prevalidar</button></footer>
    </section>
  );
}

function Summary({ record }) {
  return (
    <div className="geo-summary">
      <SummaryItem tone="neutral" label="Features" value={record.total_features} />
      <SummaryItem tone="valid" label="Válidos" value={record.validos} />
      <SummaryItem tone="warning" label="Advertencias" value={record.advertencias} />
      <SummaryItem tone="error" label="Errores" value={record.errores} />
      <SummaryItem tone="imported" label="Importados" value={record.importados} />
    </div>
  );
}

function SummaryItem({ tone, label, value }) {
  return <div className={`geo-summary-item ${tone}`}><span>{label}</span><strong>{Number(value).toLocaleString()}</strong></div>;
}

function FeatureTable({ features, editable, onEdit }) {
  return (
    <div className="geo-table-wrap">
      <table className="geo-feature-table">
        <thead><tr><th>Estado</th><th>Núcleo</th><th>Entidad</th><th>Municipio</th><th>Geometría</th><th>Problema</th>{editable && <th><span className="sr-only">Acciones</span></th>}</tr></thead>
        <tbody>
          {features.length === 0 && <tr><td colSpan={editable ? 7 : 6} className="geo-empty">Sin registros en este filtro</td></tr>}
          {features.map((feature) => {
            const attrs = feature.atributos_normalizados || {};
            const problems = [...(feature.errores || []), ...(feature.advertencias || [])];
            const geometryBlocked = (feature.errores || []).some((item) => item.campo === 'geometria');
            return (
              <tr key={feature.id_importacion_feature}>
                <td><StatusPill status={feature.estado} /></td>
                <td><strong>{attrs.nombre_nucleo || 'Sin nombre'}</strong><span>{feature.id_externo || ''}</span></td>
                <td>{attrs.entidad || `ID ${feature.id_entidad_resuelta || '—'}`}</td>
                <td>{attrs.municipio || `ID ${feature.id_municipio_resuelto || '—'}`}</td>
                <td>{geometryBlocked ? 'Bloqueada' : 'Normalizada'}</td>
                <td className="geo-problem-cell">{problems.length ? problems.map((item) => item.mensaje).join(' ') : 'Sin problemas'}</td>
                {editable && <td><button className="geo-icon-button" type="button" title="Revisar feature" onClick={() => onEdit(feature)}><Pencil size={16} /></button></td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: String(status).replace('_', ' '), icon: LoaderCircle, tone: 'muted' };
  const Icon = meta.icon;
  return <span className={`geo-status ${meta.tone}`}><Icon size={14} />{meta.label}</span>;
}

function ConfirmDialog({ record, acceptWarnings, onAcceptWarnings, onClose, onConfirm }) {
  return (
    <div className="geo-dialog-backdrop" role="presentation">
      <section className="geo-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-import-title">
        <header><h3 id="confirm-import-title">Confirmar importación</h3><button className="geo-icon-button" type="button" title="Cerrar" onClick={onClose}><X size={18} /></button></header>
        <dl><div><dt>Registros válidos</dt><dd>{record.validos}</dd></div><div><dt>Advertencias</dt><dd>{record.advertencias}</dd></div><div><dt>Errores bloqueados</dt><dd>{record.errores}</dd></div></dl>
        {record.advertencias > 0 && <label className="geo-check"><input type="checkbox" checked={acceptWarnings} onChange={(event) => onAcceptWarnings(event.target.checked)} />Aceptar advertencias revisadas</label>}
        <footer><button className="geo-button secondary" type="button" onClick={onClose}>Cancelar</button><button className="geo-button primary" type="button" onClick={onConfirm}><CheckCircle2 size={17} />Confirmar importación</button></footer>
      </section>
    </div>
  );
}

function FeatureDialog({ feature, onClose, onSave }) {
  const attrs = feature.atributos_normalizados || {};
  const [name, setName] = React.useState(attrs.nombre_nucleo || '');
  const [type, setType] = React.useState(attrs.tipo_nucleo || '');
  const [entityId, setEntityId] = React.useState(feature.id_entidad_resuelta ? String(feature.id_entidad_resuelta) : '');
  const [municipalityId, setMunicipalityId] = React.useState(feature.id_municipio_resuelto ? String(feature.id_municipio_resuelto) : '');
  const [entities, setEntities] = React.useState([]);
  const [municipalities, setMunicipalities] = React.useState([]);
  const [catalogError, setCatalogError] = React.useState('');
  const [accept, setAccept] = React.useState(feature.advertencias_aceptadas);
  React.useEffect(() => {
    Promise.all([api.get('/catalogos/entidades'), api.get('/catalogos/municipios')])
      .then(([entityResponse, municipalityResponse]) => {
        setEntities(entityResponse.data);
        setMunicipalities(municipalityResponse.data);
      })
      .catch((requestError) => setCatalogError(apiError(requestError)));
  }, []);
  const availableMunicipalities = municipalities.filter(
    (item) => !entityId || String(item.id_entidad) === entityId,
  );
  const save = () => {
    const payload = {
      nombre_nucleo: name,
      tipo_nucleo: type || null,
      aceptar_advertencias: accept,
    };
    if (entityId && municipalityId) {
      payload.id_entidad = Number(entityId);
      payload.id_municipio = Number(municipalityId);
    }
    onSave(payload);
  };
  return (
    <div className="geo-dialog-backdrop" role="presentation">
      <section className="geo-dialog" role="dialog" aria-modal="true" aria-labelledby="review-feature-title">
        <header><h3 id="review-feature-title">Revisar feature {feature.indice_feature}</h3><button className="geo-icon-button" type="button" title="Cerrar" onClick={onClose}><X size={18} /></button></header>
        <div className="geo-form-grid single">
          <label>Nombre del núcleo<input value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>Tipo de núcleo<select value={type} onChange={(event) => setType(event.target.value)}><option value="">Sin resolver</option><option value="ejido">Ejido</option><option value="comunidad">Comunidad</option></select></label>
          <label>Entidad<select value={entityId} onChange={(event) => { setEntityId(event.target.value); setMunicipalityId(''); }}><option value="">Sin resolver</option>{entities.map((entity) => <option key={entity.id_entidad} value={entity.id_entidad}>{entity.nombre}</option>)}</select></label>
          <label>Municipio<select value={municipalityId} disabled={!entityId} onChange={(event) => setMunicipalityId(event.target.value)}><option value="">Sin resolver</option>{availableMunicipalities.map((municipality) => <option key={municipality.id_municipio} value={municipality.id_municipio}>{municipality.nombre}</option>)}</select></label>
          {feature.advertencias.length > 0 && <label className="geo-check"><input type="checkbox" checked={accept} onChange={(event) => setAccept(event.target.checked)} />Advertencias revisadas y aceptadas</label>}
        </div>
        {catalogError && <div className="geo-notice error"><XCircle size={18} />{catalogError}</div>}
        <div className="geo-dialog-problems">{[...feature.errores, ...feature.advertencias].map((item) => <p key={`${item.codigo}-${item.mensaje}`}>{item.mensaje}</p>)}</div>
        <footer><button className="geo-button danger" type="button" onClick={() => onSave({ descartar: true })}><X size={16} />Descartar</button><button className="geo-button primary" type="button" disabled={Boolean(entityId) !== Boolean(municipalityId)} onClick={save}><Check size={16} />Guardar revisión</button></footer>
      </section>
    </div>
  );
}
