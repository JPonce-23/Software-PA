import React, { useContext, useState, useEffect, useMemo, useRef } from 'react';
import { Layers, CheckCircle, MapPin, ChevronUp, ChevronDown, ExternalLink, X } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON, LayersControl, useMap, FeatureGroup } from 'react-leaflet';
import { useSearchParams, useNavigate } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../api/axios';
import { parse } from 'wellknown';
import FranjaDerechoViaPanel from '../components/fase2/FranjaDerechoViaPanel';
import AuthContext from '../contexts/auth-context';

// Centro geográfico de México y zoom para vista general
const MEXICO_CENTER = [23.6345, -102.5528];
const MEXICO_ZOOM = 5;
const NUCLEOS_MODE_INTERSECTADOS = 'intersectados';
const NUCLEOS_MODE_TODOS = 'todos';
const TRAMO_STYLES = [
  { color: '#1d4ed8', fillColor: '#60a5fa', dashArray: null },
  { color: '#7c3aed', fillColor: '#a78bfa', dashArray: '8 4' },
  { color: '#047857', fillColor: '#34d399', dashArray: '2 6' },
  { color: '#be123c', fillColor: '#fb7185', dashArray: '10 5 2 5' },
  { color: '#a16207', fillColor: '#facc15', dashArray: '1 5' },
];

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  }[character]));
}

// Componente para auto-ajustar el zoom al polígono
function MapFitter({ geojsonData, selectedTramoId }) {
  const map = useMap();
  const didFitTramo = useRef(null);

  useEffect(() => {
    if (geojsonData && geojsonData.features.length > 0) {
      try {
        let featuresToFit = geojsonData.features;
        // Si hay un tramo seleccionado y acabamos de cambiar a él, enfocar
        if (selectedTramoId && didFitTramo.current !== selectedTramoId) {
          const intersectedFeatures = featuresToFit.filter(f => f.properties?.intersecta_trazo);
          if (intersectedFeatures.length > 0) {
            featuresToFit = intersectedFeatures;
            didFitTramo.current = selectedTramoId;
          }
        } else if (!selectedTramoId) {
          didFitTramo.current = null;
        }

        const layer = L.geoJSON({ type: "FeatureCollection", features: featuresToFit });
        map.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 11 });
      } catch (e) {
        console.error("Error ajustando límites", e);
      }
    }
  }, [geojsonData, selectedTramoId, map]);
  return null;
}

function buildNucleosGeoJSON(data, selectedTramoId = null) {
  const features = data.map(n => {
    if (!n.geometria_wkt) return null;

    const intersectsTrace = Boolean(n.intersecta_trazo);

    return {
      type: "Feature",
      properties: {
        id_tramo: n.id_tramo || selectedTramoId,
        id_nucleo: n.id_nucleo,
        name: n.nombre_nucleo,
        tipo: n.tipo_nucleo,
        estatus: n.estatus_simulado,
        area_ha: n.area_ha,
        area_afectada_ha: n.area_afectada_ha,
        expedientes: Array.isArray(n.expedientes) ? n.expedientes : [],
        intersecta_trazo: intersectsTrace,
        color: intersectsTrace ? "#7c2d12" : "#475569",
        fillColor: intersectsTrace ? "#f97316" : "#cbd5e1",
        fillOpacity: intersectsTrace ? 0.55 : 0.18,
        weight: intersectsTrace ? 3 : 1,
        dashArray: intersectsTrace ? null : "4 4",
      },
      geometry: parse(n.geometria_wkt)
    };
  }).filter(Boolean);
  return { type: "FeatureCollection", features };
}

function buildTramosGeoJSON(secciones, tramos) {
  const tramosById = new Map(tramos.map((tramo, index) => [tramo.id_tramo, { ...tramo, index }]));
  const features = secciones.map((seccion) => {
    if (!seccion.geometria_wkt) return null;
    const tramo = tramosById.get(seccion.id_tramo);
    const style = TRAMO_STYLES[(tramo?.index ?? 0) % TRAMO_STYLES.length];
    return {
      type: 'Feature',
      properties: {
        id_tramo: seccion.id_tramo,
        id_seccion: seccion.id_seccion,
        id_proyecto: tramo?.id_proyecto,
        clave_tramo: tramo?.clave_tramo || `Tramo ${seccion.id_tramo}`,
        nombre_tramo: tramo?.nombre_tramo || `Tramo ${seccion.id_tramo}`,
        color: style.color,
        fillColor: style.fillColor,
        fillOpacity: 0.28,
        weight: 4,
        dashArray: style.dashArray,
      },
      geometry: parse(seccion.geometria_wkt),
    };
  }).filter(Boolean);
  return { type: 'FeatureCollection', features };
}

function MapLegend({ tramos, proyectos, nucleosMode }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const legendRef = useRef(null);
  const proyectosById = useMemo(
    () => new Map(proyectos.map((proyecto) => [proyecto.id_proyecto, proyecto])),
    [proyectos],
  );
  const groupedTramos = useMemo(() => {
    const groups = new Map();
    tramos.forEach((tramo, index) => {
      const projectLabel = proyectosById.get(tramo.id_proyecto)?.nombre_proyecto || 'Proyecto no disponible';
      if (!groups.has(projectLabel)) groups.set(projectLabel, []);
      groups.get(projectLabel).push({ ...tramo, index });
    });
    return Array.from(groups.entries()).map(([projectName, items]) => ({ projectName, items }));
  }, [proyectosById, tramos]);

  useEffect(() => {
    if (!legendRef.current) return;
    L.DomEvent.disableClickPropagation(legendRef.current);
    L.DomEvent.disableScrollPropagation(legendRef.current);
  }, []);

  return (
    <section ref={legendRef} className={`mapa-intersection-legend ${isExpanded ? 'expanded' : 'collapsed'}`} aria-label="Simbología del mapa">
      <header className="mapa-legend-header" onClick={() => setIsExpanded(!isExpanded)} style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Layers size={16} /> {isExpanded ? 'Ocultar Leyenda' : 'Leyenda'}</span>
        {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </header>
      {isExpanded && (
        <div className="mapa-legend-scroll" style={{ maxHeight: '250px', overflowY: 'auto' }}>
          {groupedTramos.map((group, groupIndex) => (
            <div key={group.projectName} className="mapa-legend-project">
              {groupIndex > 0 && <div className="mapa-legend-separator" />}
              <h4>{group.projectName}</h4>
              <div className="mapa-legend-items">
                {group.items.map((tramo) => {
                  const style = TRAMO_STYLES[tramo.index % TRAMO_STYLES.length];
                  return (
                    <div key={tramo.id_tramo} className="mapa-legend-row">
                      <span
                        className="mapa-legend-line"
                        style={{
                          borderColor: style.color,
                          borderTopStyle: style.dashArray ? 'dashed' : 'solid',
                        }}
                      />
                      <span>{tramo.clave_tramo} · {tramo.nombre_tramo}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          <div className="mapa-legend-separator" />
          <div className="mapa-legend-project">
            <h4>Núcleos Agrarios</h4>
            <div className="mapa-legend-items">
              <div className="mapa-legend-row"><span className="mapa-legend-symbol intersected" /> Núcleo intersectado</div>
              {nucleosMode === NUCLEOS_MODE_TODOS && (
                <div className="mapa-legend-row"><span className="mapa-legend-symbol normal" /> Núcleo sin intersección</div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default function Mapa() {
  const { user } = useContext(AuthContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Fuente única de verdad: URL Query Params
  const idProyectoParam = searchParams.get('id_proyecto');
  const selectedProjectId = idProyectoParam === 'all' || !idProyectoParam ? 'all' : (Number(idProyectoParam) || 'all');

  const idTramoParam = searchParams.get('seleccionar_tramo');
  const selectedTramoId = Number(idTramoParam) || null;
  const nucleosModeParam = searchParams.get('nucleos');
  const nucleosMode = nucleosModeParam === NUCLEOS_MODE_TODOS
    ? NUCLEOS_MODE_TODOS
    : NUCLEOS_MODE_INTERSECTADOS;

  // Lista de proyectos
  const [proyectos, setProyectos] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);

  // Capas GeoJSON
  const [tramos, setTramos] = useState([]);
  const [tramosGeoJSON, setTramosGeoJSON] = useState(null);
  const [nucleosGeoJSON, setNucleosGeoJSON] = useState(null);

  // Panel de detalles del tramo
  const [tramoDetalle, setTramoDetalle] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Revisión para forzar recarga tras importación de derecho de vía
  const [franjasRevision, setFranjasRevision] = useState(0);

  // Estado de carga y error
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 1. Cargar lista de proyectos al montar
  useEffect(() => {
    api.get('/proyectos')
      .then(res => setProyectos(res.data))
      .catch(() => {
        setProyectos([]);
        setError('No fue posible cargar los proyectos disponibles.');
      })
      .finally(() => setProjectsLoading(false));
  }, []);

  // 2. Cargar datos geoespaciales según el proyecto seleccionado con AbortController
  useEffect(() => {
    // Limpiar geometrías y detalle inmediatamente al cambiar de proyecto (Fase 6)
    setTramos([]);
    setTramosGeoJSON(null);
    setNucleosGeoJSON(null);
    setTramoDetalle(null);
    setError(null);

    const abortController = new AbortController();
    setLoading(true);

    async function loadMapData() {
      const isAll = selectedProjectId === 'all';
      const tramosUrl = isAll ? '/tramos' : `/tramos?id_proyecto=${selectedProjectId}`;
      const nucleosParams = new URLSearchParams();
      if (!isAll) nucleosParams.set('id_proyecto', selectedProjectId);
      if (selectedTramoId) nucleosParams.set('id_tramo', selectedTramoId);
      if (nucleosMode === NUCLEOS_MODE_TODOS) nucleosParams.set('contexto_estatal', 'true');
      else nucleosParams.set('solo_intersectados', 'true');
      const nucleosUrl = `/nucleos?${nucleosParams.toString()}`;

      const [resTramos, resNucleos] = await Promise.all([
        api.get(tramosUrl, { signal: abortController.signal }),
        api.get(nucleosUrl, { signal: abortController.signal }),
      ]);

      if (selectedTramoId && !resTramos.data.some((tramo) => tramo.id_tramo === selectedTramoId)) {
        setSearchParams((currentParams) => {
          const nextParams = new URLSearchParams(currentParams);
          nextParams.delete('seleccionar_tramo');
          return nextParams;
        }, { replace: true });
        return;
      }

      const visibleTramos = selectedTramoId
        ? resTramos.data.filter((tramo) => tramo.id_tramo === selectedTramoId)
        : resTramos.data;
      const seccionesResponses = await Promise.all(
        visibleTramos.map((tramo) => api.get(`/tramos/${tramo.id_tramo}/secciones-derecho-via`, {
          signal: abortController.signal,
        }))
      );
      const secciones = seccionesResponses.flatMap((response) => response.data);

      setTramos(resTramos.data);
      setTramosGeoJSON(buildTramosGeoJSON(secciones, resTramos.data));
      setNucleosGeoJSON(buildNucleosGeoJSON(resNucleos.data, selectedTramoId));
    }

    loadMapData().catch(err => {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      console.error('Error al cargar capas:', err);
      setError('Error al cargar datos geoespaciales.');
    }).finally(() => {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    });

    return () => abortController.abort(); // Cancelar petición si el componente se desmonta o cambia el proyecto (Fase 7)
  }, [selectedProjectId, selectedTramoId, nucleosMode, franjasRevision, setSearchParams]);

  // 3. Cargar detalle de tramo seleccionado
  useEffect(() => {
    if (!selectedTramoId) {
      setTramoDetalle(null);
      return;
    }
    const abortController = new AbortController();
    api.get(`/tramo-detalles?id_tramo=${selectedTramoId}`, { signal: abortController.signal })
      .then(res => {
        setTramoDetalle(res.data);
        setIsPanelOpen(false); // Fase 9: Panel inicialmente contraído
      })
      .catch(err => {
        if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') console.error(err);
      });
    return () => abortController.abort();
  }, [selectedTramoId]);

  const onEachNucleo = (feature, layer) => {
    if (feature.properties && feature.properties.name) {
      const estatusText = {
        'liberado': 'Liberado',
        'en_proceso': 'En Proceso',
        'problema': 'Con Problemas'
      }[feature.properties.estatus] || 'Pendiente';
      const expedientes = feature.properties.expedientes || [];
      const expedienteAction = expedientes.length === 1
        ? `<button type="button" class="mapa-popup-action" data-expediente-id="${escapeHtml(expedientes[0].id_tramo_nucleo)}">Ver expediente</button>`
        : expedientes.length > 1
          ? `<button type="button" class="mapa-popup-action" data-nucleo-id="${escapeHtml(feature.properties.id_nucleo)}">Ver expedientes (${expedientes.length})</button>`
          : '<p style="margin:8px 0 0; color:#64748b; font-size:12px;">Sin expediente en este contexto.</p>';

      layer.bindPopup(`
        <div style="font-family: Inter, sans-serif;">
          <h3 style="margin:0 0 5px 0; color: #1e293b;">${escapeHtml(feature.properties.name)}</h3>
          <p style="margin:0; font-size: 12px; color: #64748b; text-transform: capitalize;">${escapeHtml(feature.properties.tipo)}</p>
          <hr style="margin: 8px 0; border: 0; border-top: 1px solid #e2e8f0;" />
          <p style="margin:4px 0;"><strong>Estatus:</strong> ${estatusText}</p>
          <p style="margin:4px 0;"><strong>Intersección con derecho de vía:</strong> ${feature.properties.intersecta_trazo ? 'Sí' : 'No'}</p>
          <p style="margin:4px 0;"><strong>Superficie del núcleo:</strong> ${escapeHtml(feature.properties.area_ha)} hectáreas</p>
          <p style="margin:4px 0;"><strong>Superficie en derecho de vía:</strong> ${escapeHtml(feature.properties.area_afectada_ha)} hectáreas</p>
          ${expedienteAction}
        </div>
      `);
      layer.on('popupopen', (event) => {
        setIsPanelOpen(false);
        const button = event.popup.getElement()?.querySelector('.mapa-popup-action');
        if (!button) return;
        button.addEventListener('click', () => {
          const expedienteId = button.getAttribute('data-expediente-id');
          if (expedienteId) {
            navigate(`/expedientes/${expedienteId}`);
            return;
          }
          const nucleoId = button.getAttribute('data-nucleo-id');
          const nextParams = new URLSearchParams();
          if (nucleoId) nextParams.set('id_nucleo', nucleoId);
          if (selectedTramoId) nextParams.set('id_tramo', String(selectedTramoId));
          else if (typeof selectedProjectId === 'number') nextParams.set('id_proyecto', String(selectedProjectId));
          navigate(`/expedientes?${nextParams.toString()}`);
        }, { once: true });
      });
    }
  };

  const onEachTramo = (feature, layer) => {
    const props = feature.properties || {};
    const label = `${props.clave_tramo || 'Tramo'} · ${props.nombre_tramo || ''}`;
    layer.bindTooltip(label, { sticky: true });
    layer.on('click', () => {
      layer._map?.closePopup();
      handleSelectTramo(props.id_tramo);
      setIsPanelOpen(false);
    });
  };

  const handleSelectTramo = (id_tramo) => {
    const nextParams = new URLSearchParams(searchParams);
    if (id_tramo) {
      nextParams.set('seleccionar_tramo', id_tramo);
    } else {
      nextParams.delete('seleccionar_tramo');
    }
    setSearchParams(nextParams);
  };

  const handleNucleosModeChange = (mode) => {
    const nextParams = new URLSearchParams(searchParams);
    if (mode === NUCLEOS_MODE_TODOS) nextParams.set('nucleos', NUCLEOS_MODE_TODOS);
    else nextParams.delete('nucleos');
    setSearchParams(nextParams);
  };

  const styleFeature = (feature) => {
    return {
      color: feature.properties.color,
      weight: feature.properties.weight || 1.5,
      opacity: 1.0,
      fillColor: feature.properties.fillColor || feature.properties.color,
      fillOpacity: feature.properties.fillOpacity || 0.2,
      dashArray: feature.properties.dashArray || null,
    };
  };

  const tramosVisibles = useMemo(() => {
    if (!tramosGeoJSON) return null;
    return tramosGeoJSON;
  }, [tramosGeoJSON]);

  const nucleosVisibles = useMemo(() => {
    if (!nucleosGeoJSON) return null;
    return nucleosGeoJSON;
  }, [nucleosGeoJSON]);

  const totalNucleos = nucleosVisibles ? nucleosVisibles.features.length : 0;
  const areaTotal = nucleosVisibles
    ? nucleosVisibles.features.reduce(
      (acc, feature) => acc + (Number(
        selectedTramoId ? feature.properties.area_afectada_ha : feature.properties.area_ha,
      ) || 0),
      0,
    )
    : 0;
  const liberados = nucleosVisibles ? nucleosVisibles.features.filter(f => f.properties.estatus === 'liberado').length : 0;
  const nucleosIntersectados = nucleosVisibles ? nucleosVisibles.features.filter(f => f.properties.intersecta_trazo).length : 0;

  // Determinar datos para fitBounds
  const boundsData = tramosVisibles?.features.length
    ? tramosVisibles
    : nucleosVisibles?.features.length
      ? nucleosVisibles
      : null;

  // Proyecto actualmente seleccionado (para título del panel)
  const proyectoSeleccionado = typeof selectedProjectId === 'number'
    ? proyectos.find(p => p.id_proyecto === selectedProjectId)
    : null;

  const handleProjectChange = (e) => {
    const val = e.target.value;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('seleccionar_tramo');
    if (val === '') nextParams.delete('id_proyecto');
    else nextParams.set('id_proyecto', val);
    setSearchParams(nextParams);
  };

  const noProjectsAssigned = proyectos.length === 0;
  const hasData = tramosGeoJSON?.features.length > 0
    || nucleosGeoJSON?.features.length > 0;

  // Keys para forzar re-render de GeoJSON cuando cambian los datos
  const layerKey = `proj-${selectedProjectId}-nucleos-${nucleosMode}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px' }}>
      <div className="mapa-map-shell">

        {/* ────── SELECTOR DE PROYECTO ────── */}
        <div className="mapa-project-selector">
          <MapPin size={16} style={{ color: '#64748b', flexShrink: 0 }} />
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155', whiteSpace: 'nowrap' }}>
            Proyecto:
          </label>
          <select
            value={selectedProjectId}
            onChange={handleProjectChange}
            className="mapa-project-select"
          >
            <option value="all">Todos los proyectos</option>
            {proyectos.map(p => (
              <option key={p.id_proyecto} value={p.id_proyecto}>
                {p.nombre_proyecto}
              </option>
            ))}
          </select>
          {typeof selectedProjectId === 'number' && (
            <select
              value={selectedTramoId || ''}
              onChange={(event) => handleSelectTramo(event.target.value)}
              className="mapa-project-select"
              aria-label="Tramo"
            >
              <option value="">Todos los tramos</option>
              {tramos.map((tramo) => <option key={tramo.id_tramo} value={tramo.id_tramo}>{tramo.clave_tramo} · {tramo.nombre_tramo}</option>)}
            </select>
          )}
          <select
            value={nucleosMode}
            onChange={(event) => handleNucleosModeChange(event.target.value)}
            className="mapa-project-select"
            aria-label="Visualización de núcleos"
          >
            <option value={NUCLEOS_MODE_INTERSECTADOS}>Sólo núcleos intersectados</option>
            <option value={NUCLEOS_MODE_TODOS}>Todos los núcleos</option>
          </select>
          {(loading || projectsLoading) && <div className="mapa-spinner" />}
        </div>

        {/* ────── MENSAJE SIN PROYECTOS ────── */}
        {noProjectsAssigned && !loading && !projectsLoading && !error && (
          <div className="mapa-overlay-message">
            <>
              <p style={{ margin: 0, fontSize: '15px', color: '#64748b' }}>
                No tienes proyectos asignados.
              </p>
              <p style={{ margin: '8px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                Contacta al administrador para obtener acceso.
              </p>
            </>
          </div>
        )}

        {/* ────── MENSAJE SIN GEOMETRÍAS ────── */}
        {!noProjectsAssigned && !loading && !error && !hasData && (
          <div className="mapa-overlay-message">
            <p style={{ margin: 0, fontSize: '15px', color: '#64748b' }}>
              Este proyecto no tiene geometrías registradas.
            </p>
          </div>
        )}

        {/* ────── ERROR ────── */}
        {error && (
          <div style={{
            position: 'absolute', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
            zIndex: 1000,
            background: '#fef2f2', border: '1px solid #fecaca',
            padding: '10px 20px', borderRadius: '10px',
            fontSize: '13px', color: '#dc2626',
            fontFamily: 'Inter, sans-serif',
          }}>
            {error}
          </div>
        )}

        {/* ────── PANEL TÉCNICO GLASSMORPHISM (modo tramo) ────── */}
        {selectedTramoId && tramoDetalle && (
          <div className="mapa-tramo-panel">
            <header
              onClick={() => setIsPanelOpen(!isPanelOpen)}
              style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '15px 20px', cursor: 'pointer', background: 'rgba(255, 255, 255, 0.5)',
                borderBottom: isPanelOpen ? '1px solid rgba(0,0,0,0.05)' : 'none',
                flexShrink: 0
              }}
            >
              <div>
                <h2 style={{ margin: '0 0 2px 0', fontSize: '16px', color: '#0f172a' }}>{tramoDetalle.nombre_tramo}</h2>
                <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>{isPanelOpen ? 'Análisis Geoespacial' : 'Ver información del tramo'}</p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b', display: 'flex' }}
                  title={isPanelOpen ? "Ocultar panel" : "Mostrar panel"}
                >
                  {isPanelOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleSelectTramo(null); }}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#ef4444', display: 'flex' }}
                  title="Cerrar panel y deseleccionar tramo"
                >
                  <X size={20} />
                </button>
              </div>
            </header>

            {isPanelOpen && (
              <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ background: '#fef3c7', padding: '8px', borderRadius: '8px', color: '#d97706' }}><Layers size={18} /></div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>Superficie Afectada</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>{areaTotal.toLocaleString(undefined, {maximumFractionDigits:2})} ha</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ background: '#e0f2fe', padding: '8px', borderRadius: '8px', color: '#0284c7' }}><MapPin size={18} /></div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>Longitud del tramo</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>{tramoDetalle.longitud_km > 0 ? `${tramoDetalle.longitud_km.toLocaleString(undefined, {maximumFractionDigits:2})} km` : 'N/A'}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ background: '#dcfce7', padding: '8px', borderRadius: '8px', color: '#16a34a' }}><CheckCircle size={18} /></div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>Estatus de Liberación</div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>{liberados} de {totalNucleos} núcleos</div>
                      {totalNucleos > 0 && (
                        <div style={{ width: '100%', background: '#e2e8f0', height: '6px', borderRadius: '3px', marginTop: '5px' }}>
                          <div style={{ width: `${(liberados/totalNucleos)*100}%`, background: '#22c55e', height: '100%', borderRadius: '3px' }}></div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: '20px', paddingTop: '15px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
                  <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '10px', height: '10px', background: '#22c55e', borderRadius: '50%'}}></span> Liberado</span>
                  <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '10px', height: '10px', background: '#94a3b8', borderRadius: '50%'}}></span> Proceso</span>
                  <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '10px', height: '10px', background: '#ef4444', borderRadius: '50%'}}></span> Problema</span>
                </div>

                <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <button
                    onClick={() => navigate(`/expedientes?id_tramo=${selectedTramoId}`)}
                    style={{ width: '100%', padding: '10px', background: '#006341', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                  >
                    <ExternalLink size={16} />
                    Ver expedientes
                  </button>

                  {['admin', 'geografo'].includes(user?.rol) && (
                    <FranjaDerechoViaPanel
                      idProyecto={typeof selectedProjectId === 'number' ? selectedProjectId : null}
                      onImportSuccess={() => setFranjasRevision((revision) => revision + 1)}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ────── PANEL RESUMEN (modo proyecto) ────── */}
        {!noProjectsAssigned && !loading && totalNucleos > 0 && (
          <div className="mapa-summary-panel">
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a' }}>
              {proyectoSeleccionado ? proyectoSeleccionado.nombre_proyecto : 'Todos los proyectos'}
            </h3>
            <p style={{ margin: '0 0 10px', fontSize: '11px', color: '#64748b' }}>
              {nucleosMode === NUCLEOS_MODE_TODOS ? 'Mostrando todos los núcleos del alcance' : 'Mostrando sólo núcleos intersectados'}
            </p>
            <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#475569' }}>
              <div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e293b' }}>{totalNucleos}</div>
                <div>Núcleos</div>
              </div>
              <div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e293b' }}>{areaTotal.toLocaleString(undefined, {maximumFractionDigits:2})}</div>
                <div>{selectedTramoId ? 'ha afectadas' : 'ha de núcleos'}</div>
              </div>
              <div>
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#c2410c' }}>{nucleosIntersectados}</div>
                <div>Intersectados</div>
              </div>
            </div>

          </div>
        )}

        {!noProjectsAssigned && !loading && (tramos.length > 0 || totalNucleos > 0) && (
          <MapLegend tramos={tramos} proyectos={proyectos} nucleosMode={nucleosMode} />
        )}

        <MapContainer
          center={MEXICO_CENTER}
          zoom={MEXICO_ZOOM}
          style={{ height: '100%', width: '100%' }}
        >
          {/* Zoom Inteligente hacia los polígonos */}
          {boundsData && !noProjectsAssigned && (
            <MapFitter geojsonData={boundsData} selectedTramoId={selectedTramoId} />
          )}

          <LayersControl position="topright">
            {/* 1. Capa Satelital (Ideal para ver terrenos reales) */}
            <LayersControl.BaseLayer name="Satélite (Esri)">
              <TileLayer
                attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>

            {/* 2. Capa Clara / Escala de Grises (Ideal para resaltar los polígonos) */}
            <LayersControl.BaseLayer checked name="Minimalista Claro (CartoDB)">
              <TileLayer
                attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              />
            </LayersControl.BaseLayer>

            {/* 3. Capa Oscura (Modo Noche, hace brillar los colores neon) */}
            <LayersControl.BaseLayer name="Modo Oscuro (CartoDB)">
              <TileLayer
                attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />
            </LayersControl.BaseLayer>

            {/* 4. Capa Topográfica (Para ver relieves y curvas de nivel) */}
            <LayersControl.BaseLayer name="Topográfico (Esri)">
              <TileLayer
                attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>

            {/* 5. Capa Callejero Estándar */}
            <LayersControl.BaseLayer name="Callejero (OSM)">
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>

            {nucleosVisibles?.features.length > 0 && (
              <LayersControl.Overlay checked name="Núcleos Agrarios">
                <FeatureGroup>
                  <GeoJSON
                    key={`${layerKey}-nucleos-sel-${selectedTramoId}`}
                    data={nucleosVisibles}
                    style={styleFeature}
                    onEachFeature={onEachNucleo}
                  />
                </FeatureGroup>
              </LayersControl.Overlay>
            )}

            {tramosVisibles?.features.length > 0 && (
              <LayersControl.Overlay checked name="Tramos / derecho de vía">
                <FeatureGroup>
                  <GeoJSON
                    key={`${layerKey}-franja-${franjasRevision}-sel-${selectedTramoId}`}
                    data={tramosVisibles}
                    style={styleFeature}
                    onEachFeature={onEachTramo}
                  />
                </FeatureGroup>
              </LayersControl.Overlay>
            )}

          </LayersControl>
        </MapContainer>
      </div>
    </div>
  );
}
