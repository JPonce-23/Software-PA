import React from 'react';
import {
  AlertTriangle,
  Archive,
  Check,
  CheckCircle2,
  Download,
  FileSearch,
  LoaderCircle,
  Pencil,
  RefreshCw,
  SlidersHorizontal,
  Upload,
  X,
  XCircle,
} from 'lucide-react';

import api from '../api/axios';
import PaginatedTable from '../components/PaginatedTable';
import './ImportacionesGeoespaciales.css';


const CORE_MAPPING_FIELDS = [
  { targets: ['nombre_nucleo'], defaultTarget: 'nombre_nucleo', label: 'Nombre del núcleo agrario' },
  { targets: ['tipo_nucleo'], defaultTarget: 'tipo_nucleo', label: 'Tipo de núcleo' },
  { targets: ['entidad', 'clave_entidad_inegi'], defaultTarget: 'entidad', label: 'Entidad federativa' },
  { targets: ['municipio', 'clave_municipio_inegi', 'id_municipio_fuente'], defaultTarget: 'municipio', label: 'Municipio' },
];

const ADVANCED_MAPPING_FIELDS = [
  ['clave_entidad_inegi', 'Clave INEGI de entidad'],
  ['clave_municipio_inegi', 'Clave INEGI de municipio'],
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
const IMPORT_PAGE_SIZE = 25;
const FEATURE_PAGE_SIZE = 100;

function apiError(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ');
  return 'No fue posible completar la operación.';
}

export default function ImportacionesGeoespaciales() {
  const [imports, setImports] = React.useState([]);
  const [importTotal, setImportTotal] = React.useState(0);
  const [profiles, setProfiles] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [features, setFeatures] = React.useState({ total: 0, items: [] });
  const [filter, setFilter] = React.useState('todos');
  const [estadoVista, setEstadoVista] = React.useState('activas');
  const [importPage, setImportPage] = React.useState(1);
  const [featurePage, setFeaturePage] = React.useState(1);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [acceptWarnings, setAcceptWarnings] = React.useState(false);
  const [editingFeature, setEditingFeature] = React.useState(null);

  const [archiveTarget, setArchiveTarget] = React.useState(null);
  const [archiveReason, setArchiveReason] = React.useState('');

  const loadImports = React.useCallback(async (vista, page) => {
    const [{ data: importRecords }, { data: profileRecords }] = await Promise.all([
      api.get('/importaciones-geoespaciales', {
        params: { estado_vista: vista, offset: (page - 1) * IMPORT_PAGE_SIZE, limit: IMPORT_PAGE_SIZE, _t: Date.now() },
      }),
      api.get('/importaciones-geoespaciales/perfiles', { params: { _t: Date.now() } }),
    ]);
    setImports(importRecords.items);
    setImportTotal(importRecords.total);
    setProfiles(profileRecords);
    return importRecords;
  }, []);

  const loadSelected = React.useCallback(async (id, statusFilter, page) => {
    const params = {
      offset: (page - 1) * FEATURE_PAGE_SIZE,
      limit: FEATURE_PAGE_SIZE,
      _t: Date.now(),
      ...(statusFilter === 'todos' ? {} : { estado: statusFilter }),
    };
    const [{ data: record }, { data: featurePage }, sampleResponse] = await Promise.all([
      api.get(`/importaciones-geoespaciales/${id}`, { params: { _t: Date.now() } }),
      api.get(`/importaciones-geoespaciales/${id}/features`, { params }),
      api.get(`/importaciones-geoespaciales/${id}/muestras-columnas`, { params: { _t: Date.now() } })
        .catch(() => ({ data: { muestras: {} } })),
    ]);
    setSelected({ ...record, muestras_columnas: sampleResponse.data.muestras || {} });
    setFeatures(featurePage);
    return { ...record, muestras_columnas: sampleResponse.data.muestras || {} };
  }, []);

  React.useEffect(() => {
    loadImports(estadoVista, importPage).catch((requestError) => setError(apiError(requestError)));
  }, [estadoVista, importPage, loadImports]);

  React.useEffect(() => {
    if (!selected?.id_importacion) return undefined;
    const timer = window.setInterval(async () => {
      if (!PROCESSING_STATES.has(selected.estado)) return;
      try {
        const record = await loadSelected(selected.id_importacion, filter, featurePage);
        if (!PROCESSING_STATES.has(record.estado)) await loadImports(estadoVista, importPage);
      } catch (requestError) {
        setError(apiError(requestError));
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [estadoVista, featurePage, filter, importPage, loadImports, loadSelected, selected]);

  const chooseImport = async (record) => {
    setError('');
    setFilter('todos');
    setFeaturePage(1);
    setAcceptWarnings(false);
    try {
      await loadSelected(record.id_importacion, 'todos', 1);
    } catch (requestError) {
      setError(apiError(requestError));
    }
  };

  const applyFilter = async (nextFilter) => {
    setFilter(nextFilter);
    setFeaturePage(1);
    if (!selected) return;
    try {
      await loadSelected(selected.id_importacion, nextFilter, 1);
    } catch (requestError) {
      setError(apiError(requestError));
    }
  };

  const handleArchive = async () => {
    if (loading || !archiveTarget || !archiveReason.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api.post(`/importaciones-geoespaciales/${archiveTarget.id_importacion}/archivar`, { motivo_baja: archiveReason });
      await loadImports(estadoVista, importPage);
      if (selected?.id_importacion === archiveTarget.id_importacion) {
        if (estadoVista === 'activas') {
          setSelected(null);
        } else {
          await loadSelected(selected.id_importacion, filter, featurePage);
        }
      }
      setArchiveTarget(null);
      setArchiveReason('');
    } catch (requestError) {
      setError(apiError(requestError));
    } finally {
      setLoading(false);
    }
  };

  const handleChangeEstadoVista = async (e) => {
    const vista = e.target.value;
    setEstadoVista(vista);
    setImportPage(1);
    setLoading(true);
    try {
      await loadImports(vista, 1);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="geo-import-page">
      <header className="geo-import-toolbar">
        <div>
          <h2>Importaciones geoespaciales</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginTop: '4px' }}>
            <span>{importTotal.toLocaleString()} archivos registrados</span>
            <select
              value={estadoVista}
              onChange={handleChangeEstadoVista}
              style={{
                padding: '4px 8px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '12px',
                background: '#fff'
              }}
            >
              <option value="activas">Vista: Activas</option>
              <option value="archivadas">Vista: Archivadas</option>
              <option value="todas">Vista: Todas</option>
            </select>
          </div>
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
          {importTotal > IMPORT_PAGE_SIZE && (
            <div style={{ padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid #dde2e6', background: '#fff', position: 'sticky', bottom: 0 }}>
              <div style={{ fontSize: '11px', textAlign: 'center', color: '#66717d' }}>
                Mostrando {(importPage - 1) * IMPORT_PAGE_SIZE + 1}-{Math.min(importPage * IMPORT_PAGE_SIZE, importTotal)} de {importTotal}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button
                  className="geo-button secondary"
                  disabled={importPage === 1}
                  onClick={() => setImportPage(p => p - 1)}
                  style={{ minHeight: '28px', padding: '4px 8px', fontSize: '12px' }}
                >
                  Anterior
                </button>
                <button
                  className="geo-button secondary"
                  disabled={importPage === Math.ceil(importTotal / IMPORT_PAGE_SIZE)}
                  onClick={() => setImportPage(p => p + 1)}
                  style={{ minHeight: '28px', padding: '4px 8px', fontSize: '12px' }}
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </aside>

        <div className="geo-import-workspace">
          {!selected && <div className="geo-empty large"><FileSearch size={30} />Seleccione una importación</div>}
          {selected?.nuevo && (
            <UploadPanel
              busy={loading}
              onCancel={() => setSelected(null)}
              onUpload={async (form) => {
                if (loading) return;
                setLoading(true);
                setError('');
                try {
                  const { data } = await api.post('/importaciones-geoespaciales', form);
                  setImportPage(1);
                  await loadImports(estadoVista, 1);
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
              imports={imports}
              profiles={profiles}
              features={features}
              filter={filter}
              busy={loading}
              onFilter={applyFilter}
              onRefresh={() => loadSelected(selected.id_importacion, filter, featurePage)}
              onEdit={setEditingFeature}
              onArchive={() => setArchiveTarget(selected)}
              onProcess={async (mappingPayload) => {
                if (loading) return;
                setLoading(true);
                setError('');
                try {
                  await api.put(`/importaciones-geoespaciales/${selected.id_importacion}/mapeo`, mappingPayload);
                  await api.post(`/importaciones-geoespaciales/${selected.id_importacion}/procesar`);
                  await loadImports(estadoVista, importPage);
                  await loadSelected(selected.id_importacion, filter, featurePage);
                } catch (requestError) {
                  setError(apiError(requestError));
                } finally {
                  setLoading(false);
                }
              }}
              onFeaturePage={async (page) => {
                setFeaturePage(page);
                await loadSelected(selected.id_importacion, filter, page);
              }}
              featurePage={featurePage}
              featurePageSize={FEATURE_PAGE_SIZE}
              onConfirm={() => { setAcceptWarnings(false); setConfirmOpen(true); }}
            />
          )}
        </div>
      </div>

      {confirmOpen && selected && (
        <ConfirmDialog
          record={selected}
          acceptWarnings={acceptWarnings}
          onAcceptWarnings={setAcceptWarnings}
          onClose={() => { setConfirmOpen(false); setAcceptWarnings(false); }}
          onConfirm={async () => {
            if (loading) return;
            setLoading(true);
            setError('');
            try {
              await api.post(`/importaciones-geoespaciales/${selected.id_importacion}/confirmar`, {
                aceptar_advertencias: acceptWarnings,
              });
              setConfirmOpen(false);
              setAcceptWarnings(false);
              await loadSelected(selected.id_importacion, filter, featurePage);
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
            if (loading) return;
            setLoading(true);
            setError('');
            try {
              await api.patch(
                `/importaciones-geoespaciales/${selected.id_importacion}/features/${editingFeature.id_importacion_feature}`,
                payload,
              );
              setEditingFeature(null);
              await loadSelected(selected.id_importacion, filter, featurePage);
            } catch (requestError) {
              setError(apiError(requestError));
            } finally {
              setLoading(false);
            }
          }}
        />
      )}

      {archiveTarget && (
        <div className="geo-dialog-backdrop" role="presentation">
          <section className="geo-dialog" role="dialog" aria-modal="true" aria-labelledby="archive-dialog-title">
            <header>
              <h3 id="archive-dialog-title">¿Archivar esta importación?</h3>
              <button className="geo-icon-button" type="button" title="Cerrar" onClick={() => { setArchiveTarget(null); setArchiveReason(''); }}><X size={18} /></button>
            </header>
            <div style={{ padding: '20px' }}>
              <p style={{ margin: '0 0 15px', fontSize: '14px', color: '#475569', lineHeight: 1.5 }}>
                El archivo dejará de mostrarse en la lista activa, pero se conservará su historial y trazabilidad.
              </p>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', fontWeight: 500, color: '#334155' }}>
                Motivo de archivado (obligatorio)
                <textarea
                  value={archiveReason}
                  onChange={(e) => setArchiveReason(e.target.value)}
                  placeholder="Especifica por qué se está archivando..."
                  style={{ padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', minHeight: '80px', fontFamily: 'Inter, sans-serif' }}
                />
              </label>
            </div>
            <footer>
              <button className="geo-button secondary" type="button" onClick={() => { setArchiveTarget(null); setArchiveReason(''); }}>Cancelar</button>
              <button className="geo-button danger" type="button" disabled={loading || !archiveReason.trim()} onClick={handleArchive}>
                {loading ? <LoaderCircle className="geo-spin" size={16} /> : <Archive size={16} />}
                Archivar importación
              </button>
            </footer>
          </section>
        </div>
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

function ImportWorkspace({ record, imports, profiles, features, filter, busy, onFilter, onRefresh, onEdit, onArchive, onProcess, onFeaturePage, featurePage, featurePageSize, onConfirm }) {
  const [mapping, setMapping] = React.useState(record.mapeo || {});
  const [options, setOptions] = React.useState(record.opciones_mapeo || {});
  const [provenance, setProvenance] = React.useState(record.procedencia_archivo || 'original');
  const [originImportId, setOriginImportId] = React.useState(record.id_importacion_origen || '');
  const [reconfigureOpen, setReconfigureOpen] = React.useState(false);
  const processing = PROCESSING_STATES.has(record.estado);
  const progress = record.total_features ? Math.round((record.features_procesados / record.total_features) * 100) : 0;
  React.useEffect(() => {
    setMapping(record.mapeo || {});
    setOptions(record.opciones_mapeo || {});
    setProvenance(record.procedencia_archivo || '');
    setOriginImportId(record.id_importacion_origen || '');
  }, [
    record.id_importacion,
    record.id_importacion_origen,
    record.mapeo,
    record.opciones_mapeo,
    record.procedencia_archivo,
  ]);

  const originCandidates = imports.filter((item) => (
    item.id_importacion !== record.id_importacion
    && item.formato_detectado === 'kml'
    && item.fuente.trim().toLocaleLowerCase() === record.fuente.trim().toLocaleLowerCase()
  ));
  const provenanceReady = record.formato_detectado === 'kml'
    || provenance === 'original'
    || (provenance === 'conversion' && Boolean(originImportId));
  const confirmationBlockedByProvenance = record.formato_detectado === 'geojson'
    && !record.procedencia_archivo;

  const mappingReady = Boolean(
    mapping.nombre_nucleo
    && mapping.tipo_nucleo
    && (mapping.entidad || mapping.clave_entidad_inegi)
    && (mapping.municipio || mapping.clave_municipio_inegi || mapping.id_municipio_fuente)
    && provenanceReady
  );

  React.useEffect(() => {
    if (record.estado === 'subido' && mappingReady && !busy) {
      onProcess({
        mapeo: mapping,
        opciones: options,
        procedencia_archivo: record.formato_detectado === 'kml' ? 'original' : provenance,
        id_importacion_origen: provenance === 'conversion' ? Number(originImportId) : null,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record.estado, mappingReady, busy, mapping, options, provenance, originImportId]);

  const isAutoProcessing = record.estado === 'subido' && mappingReady;

  const mappingVisible = (
    (['subido', 'fallido'].includes(record.estado) && record.error_codigo !== 'CONFIRMACION_FALLIDA' && !isAutoProcessing)
  ) || (record.estado === 'listo_revision' && reconfigureOpen);
  return (
    <>
      <header className="geo-record-header">
        <div><h3>{record.nombre_original}</h3><span>SHA-256 {record.sha256}</span></div>
        <div className="geo-record-actions">
          <a className="geo-icon-button" href={`/api/importaciones-geoespaciales/${record.id_importacion}/reporte.csv`} title="Descargar reporte"><Download size={18} /></a>
          <button className="geo-icon-button" type="button" title="Actualizar" onClick={onRefresh} disabled={busy}><RefreshCw size={18} /></button>
          {!PROCESSING_STATES.has(record.estado) && !record.fecha_baja && (
            <button
              className="geo-icon-button geo-icon-archive"
              type="button"
              title="Archivar importación"
              onClick={onArchive}
              disabled={busy}
            >
              <Archive size={18} />
            </button>
          )}
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
      {record.estado === 'listo_revision' && confirmationBlockedByProvenance && (
        <div className="geo-notice warning"><AlertTriangle size={18} />Reconfigure la importación e indique si el GeoJSON es original o proviene de un KML antes de confirmarla.</div>
      )}
      {record.estado === 'completado' && record.advertencias > 0 && (
        <div className="geo-notice warning"><AlertTriangle size={18} />Quedaron {record.advertencias.toLocaleString()} features con advertencia sin importar. Puedes revisarlas y confirmar su importación sin duplicar los registros ya creados.</div>
      )}

      {isAutoProcessing && (
         <div className="geo-notice"><LoaderCircle className="geo-spin" size={18} /> Correspondencia detectada automáticamente. Procesando...</div>
      )}

      {mappingVisible && (
        <MappingPanel
          columns={record.columnas_detectadas}
          samples={record.muestras_columnas || {}}
          format={record.formato_detectado}
          originCandidates={originCandidates}
          profiles={profiles}
          source={record.fuente}
          mapping={mapping}
          options={options}
          provenance={provenance}
          originImportId={originImportId}
          onMapping={setMapping}
          onOptions={setOptions}
          onProvenance={(value) => {
            setProvenance(value);
            if (value !== 'conversion') setOriginImportId('');
          }}
          onOriginImportId={setOriginImportId}
          disabled={busy}
          ready={mappingReady}
          onProcess={(payload) => {
            setReconfigureOpen(false);
            onProcess({
              ...payload,
              procedencia_archivo: record.formato_detectado === 'kml' ? 'original' : provenance,
              id_importacion_origen: provenance === 'conversion' ? Number(originImportId) : null,
            });
          }}
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
            {(record.estado === 'listo_revision' || (record.estado === 'completado' && record.advertencias > 0)) && <div className="geo-feature-actions">
              {record.estado === 'listo_revision' && <button className="geo-button secondary" type="button" onClick={() => setReconfigureOpen((open) => !open)}><SlidersHorizontal size={17} />{reconfigureOpen ? 'Cerrar configuración' : 'Reconfigurar'}</button>}
              <button className="geo-button primary" type="button" disabled={record.estado === 'listo_revision' && (confirmationBlockedByProvenance || record.validos + record.advertencias === 0)} onClick={onConfirm}><CheckCircle2 size={17} />{record.estado === 'completado' ? 'Importar advertencias pendientes' : 'Confirmar importación'}</button>
            </div>}
          </div>
          <FeatureTable
            features={features.items}
            total={features.total}
            page={featurePage}
            pageSize={featurePageSize}
            editable={record.estado === 'listo_revision'}
            onEdit={onEdit}
            onPageChange={onFeaturePage}
          />
        </>
      )}
    </>
  );
}

function MappingPanel({
  columns,
  samples,
  format,
  originCandidates,
  profiles,
  source,
  mapping,
  options,
  provenance,
  originImportId,
  onMapping,
  onOptions,
  onProvenance,
  onOriginImportId,
  disabled,
  ready,
  onProcess,
}) {
  const [profileId, setProfileId] = React.useState('');
  const [saveProfile, setSaveProfile] = React.useState(false);
  const [profileName, setProfileName] = React.useState('');
  const setField = (target, source) => {
    const next = { ...mapping };
    if (source) next[target] = source;
    else delete next[target];
    onMapping(next);
  };
  const sourceFor = (targets) => targets.map((target) => mapping[target]).find(Boolean) || '';
  const setCoreField = (field, sourceColumn) => {
    const next = { ...mapping };
    const activeTarget = field.targets.find((target) => mapping[target]);
    field.targets.forEach((target) => delete next[target]);
    if (sourceColumn) next[activeTarget || field.defaultTarget] = sourceColumn;
    onMapping(next);
  };
  const optionLabel = (column) => {
    const values = samples[column] || [];
    return values.length ? `${column} · ${values.join(' / ')}` : column;
  };
  const mappedCoreFields = CORE_MAPPING_FIELDS.filter((field) => sourceFor(field.targets)).length;
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
      <header><h4>Correspondencia de datos</h4><span>{columns.length} columnas encontradas</span></header>
      <div className={`geo-mapping-status ${mappedCoreFields === CORE_MAPPING_FIELDS.length ? 'complete' : 'pending'}`}>
        {mappedCoreFields === CORE_MAPPING_FIELDS.length ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
        <strong>{mappedCoreFields} de {CORE_MAPPING_FIELDS.length} campos principales identificados</strong>
      </div>

      <div className="geo-file-origin">
        {format === 'geojson' && <label>Procedencia del GeoJSON
          <select value={provenance} onChange={(event) => onProvenance(event.target.value)}>
            <option value="">Seleccione la procedencia</option>
            <option value="original">Archivo GeoJSON original</option>
            <option value="conversion">Convertido desde un KML</option>
          </select>
        </label>}
        {format === 'geojson' && provenance === 'conversion' && <label>KML original de referencia
          <select value={originImportId} onChange={(event) => onOriginImportId(event.target.value)}>
            <option value="">Seleccione el archivo original</option>
            {originCandidates.map((item) => <option key={item.id_importacion} value={item.id_importacion}>{item.nombre_original} · {item.total_features} features</option>)}
          </select>
        </label>}
      </div>

      <div className="geo-core-mapping-grid">
        {CORE_MAPPING_FIELDS.map((field) => {
          const selectedSource = sourceFor(field.targets);
          return (
            <label key={field.defaultTarget}>{field.label}<b>*</b>
              <select value={selectedSource} onChange={(event) => setCoreField(field, event.target.value)}>
                <option value="">Seleccione una columna</option>
                {columns.map((column) => <option value={column} key={column}>{optionLabel(column)}</option>)}
              </select>
              {selectedSource && <span className="geo-mapping-match"><Check size={14} />Asignado</span>}
            </label>
          );
        })}
      </div>

      <details className="geo-advanced-mapping">
        <summary><SlidersHorizontal size={17} />Configuración avanzada</summary>
        <div className="geo-profile-row">
          <label>Perfil reutilizable
            <select value={profileId} onChange={(event) => applyProfile(event.target.value)}>
              <option value="">Sin perfil</option>
              {profiles.map((profile) => <option key={profile.id_perfil} value={profile.id_perfil}>{profile.nombre} · {profile.fuente}</option>)}
            </select>
          </label>
          <label className="geo-check"><input type="checkbox" checked={saveProfile} onChange={(event) => setSaveProfile(event.target.checked)} />Guardar configuración como perfil</label>
          {saveProfile && <label>Nombre del perfil<input maxLength="150" required value={profileName} onChange={(event) => setProfileName(event.target.value)} /></label>}
        </div>
        <div className="geo-mapping-grid">
          {ADVANCED_MAPPING_FIELDS.map(([target, label]) => (
            <label key={target}>{label}
              <select value={mapping[target] || ''} onChange={(event) => setField(target, event.target.value)}>
                <option value="">Sin asignar</option>
                {columns.map((column) => <option value={column} key={column}>{optionLabel(column)}</option>)}
              </select>
            </label>
          ))}
        </div>
        <div className="geo-policy-row">
          <label>Uso del ID municipal
            <select value={options.id_municipio_fuente_semantica || ''} onChange={(event) => onOptions({ ...options, id_municipio_fuente_semantica: event.target.value || undefined })}>
              <option value="">Sólo conservarlo como referencia</option>
              <option value="clave_inegi_completa">Es una clave INEGI completa</option>
              <option value="clave_municipal_inegi">Es una clave municipal INEGI</option>
            </select>
          </label>
          <label>Alcance del ID de núcleo
            <select value={options.alcance_id_nucleo_fuente || 'territorial'} onChange={(event) => onOptions({ ...options, alcance_id_nucleo_fuente: event.target.value })}>
              <option value="territorial">Se repite entre municipios</option>
              <option value="global">Es único en toda la fuente</option>
            </select>
          </label>
          <label className="geo-check"><input type="checkbox" checked={Boolean(options.unir_partes_mismo_id)} onChange={(event) => onOptions({ ...options, unir_partes_mismo_id: event.target.checked })} />Unir polígonos que tengan el mismo ID de núcleo</label>
        </div>
      </details>
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

function FeatureTable({ features, total, page, pageSize, editable, onEdit, onPageChange }) {
  const columns = React.useMemo(() => {
    const cols = [
      { header: 'Estado', render: (feature) => <StatusPill status={feature.estado} /> },
      { header: 'Núcleo', render: (feature) => {
          const attrs = feature.atributos_normalizados || {};
          return <><strong style={{ display: 'block' }}>{attrs.nombre_nucleo || 'Sin nombre'}</strong><span style={{ fontSize: '11px', color: '#66717d' }}>{feature.id_externo || ''}</span></>;
        }
      },
      { header: 'Entidad', render: (feature) => (feature.atributos_normalizados || {}).entidad || `ID ${feature.id_entidad_resuelta || '—'}` },
      { header: 'Municipio', render: (feature) => (feature.atributos_normalizados || {}).municipio || `ID ${feature.id_municipio_resuelto || '—'}` },
      { header: 'Geometría', render: (feature) => (feature.errores || []).some((item) => item.campo === 'geometria') ? 'Bloqueada' : 'Normalizada' },
      { header: 'Problema', className: 'geo-problem-cell', render: (feature) => {
          const problems = [...(feature.errores || []), ...(feature.advertencias || [])];
          return problems.length ? problems.map((item) => item.mensaje).join(' ') : 'Sin problemas';
        }
      }
    ];
    if (editable) {
      cols.push({
        header: <span className="sr-only">Acciones</span>,
        render: (feature) => <button className="geo-icon-button" type="button" title="Revisar feature" onClick={() => onEdit(feature)}><Pencil size={16} /></button>
      });
    }
    return cols;
  }, [editable, onEdit]);

  return (
    <PaginatedTable
      columns={columns}
      data={features}
      total={total}
      page={page}
      pageSize={pageSize}
      onPageChange={onPageChange}
      keyField="id_importacion_feature"
      emptyMessage="Sin registros en este filtro"
    />
  );
}

function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: String(status).replace('_', ' '), icon: LoaderCircle, tone: 'muted' };
  const Icon = meta.icon;
  return <span className={`geo-status ${meta.tone}`}><Icon size={14} />{meta.label}</span>;
}

function ConfirmDialog({ record, acceptWarnings, onAcceptWarnings, onClose, onConfirm }) {
  const resumingWarnings = record.estado === 'completado';
  return (
    <div className="geo-dialog-backdrop" role="presentation">
      <section className="geo-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-import-title">
        <header><h3 id="confirm-import-title">{resumingWarnings ? 'Importar advertencias pendientes' : 'Confirmar importación'}</h3><button className="geo-icon-button" type="button" title="Cerrar" onClick={onClose}><X size={18} /></button></header>
        <dl><div><dt>Registros válidos</dt><dd>{record.validos}</dd></div><div><dt>Advertencias</dt><dd>{record.advertencias}</dd></div><div><dt>Errores bloqueados</dt><dd>{record.errores}</dd></div></dl>
        {record.advertencias > 0 && <label className="geo-check"><input type="checkbox" checked={acceptWarnings} onChange={(event) => onAcceptWarnings(event.target.checked)} />Aceptar advertencias revisadas</label>}
        <footer><button className="geo-button secondary" type="button" onClick={onClose}>Cancelar</button><button className="geo-button primary" type="button" disabled={resumingWarnings && !acceptWarnings} onClick={onConfirm}><CheckCircle2 size={17} />{resumingWarnings ? 'Importar advertencias' : 'Confirmar importación'}</button></footer>
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
