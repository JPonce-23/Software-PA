import React, { useContext, useState, useEffect, useMemo, useRef } from 'react';
import { Layers, CheckCircle, MapPin, ChevronUp, ChevronDown, ExternalLink, X } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON, LayersControl, useMap } from 'react-leaflet';
import { useSearchParams, useNavigate } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../api/axios';
import { parse } from 'wellknown';
import FranjaDerechoViaPanel from '../components/fase2/FranjaDerechoViaPanel';
import NucleosImportPanel from '../components/fase2/NucleosImportPanel';
import AuthContext from '../contexts/auth-context';

// Centro geográfico de México y zoom para vista general
const MEXICO_CENTER = [23.6345, -102.5528];
const MEXICO_ZOOM = 5;

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
          const tramoFeature = featuresToFit.find(f => f.properties?.id_tramo === selectedTramoId);
          if (tramoFeature) {
            featuresToFit = [tramoFeature];
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

    // Semáforo agrario
    let fillColor = "#94a3b8"; // Gris - En proceso
    if (n.estatus_simulado === 'liberado') fillColor = "#22c55e"; // Verde
    if (n.estatus_simulado === 'problema') fillColor = "#ef4444"; // Rojo

    return {
      type: "Feature",
      properties: {
        id_tramo: n.id_tramo || selectedTramoId,
        name: n.nombre_nucleo,
        tipo: n.tipo_nucleo,
        estatus: n.estatus_simulado,
        area_ha: n.area_ha,
        area_afectada_ha: n.area_afectada_ha,
        color: "#ffffff", // Borde blanco
        fillColor: fillColor,
        fillOpacity: 0.7
      },
      geometry: parse(n.geometria_wkt)
    };
  }).filter(Boolean);
  return { type: "FeatureCollection", features };
}

export default function Mapa() {
  const { user } = useContext(AuthContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Fuente única de verdad: URL Query Params
  const idProyectoParam = searchParams.get('id_proyecto');
  const selectedProjectId = idProyectoParam === 'all' ? 'all' : (Number(idProyectoParam) || null);

  const idTramoParam = searchParams.get('seleccionar_tramo');
  const selectedTramoId = Number(idTramoParam) || null;

  // Lista de proyectos
  const [proyectos, setProyectos] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);

  // Capas GeoJSON
  const [tramos, setTramos] = useState([]);
  const [franjasGeoJSON, setFranjasGeoJSON] = useState(null);
  const [nucleosGeoJSON, setNucleosGeoJSON] = useState(null);

  // Panel de detalles del tramo
  const [tramoDetalle, setTramoDetalle] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Revisión para forzar recarga tras importación
  const [nucleosRevision, setNucleosRevision] = useState(0);
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
    setFranjasGeoJSON(null);
    setNucleosGeoJSON(null);
    setTramoDetalle(null);
    setError(null);

    if (selectedProjectId === null) {
      setLoading(false);
      return;
    }

    const abortController = new AbortController();
    setLoading(true);

    const isAll = selectedProjectId === 'all';
    const tramosUrl = isAll ? '/tramos' : `/tramos?id_proyecto=${selectedProjectId}`;
    const franjasUrl = isAll ? '/franjas/activas' : `/franjas/activas?id_proyecto=${selectedProjectId}`;
    const nucleosUrl = selectedTramoId
      ? `/nucleos?id_tramo=${selectedTramoId}`
      : isAll ? '/nucleos' : `/nucleos?id_proyecto=${selectedProjectId}`;

    Promise.all([
      api.get(tramosUrl, { signal: abortController.signal }),
      api.get(franjasUrl, { signal: abortController.signal }),
      api.get(nucleosUrl, { signal: abortController.signal }),
    ]).then(([resTramos, resFranjas, resNucleos]) => {
      if (selectedTramoId && !resTramos.data.some((tramo) => tramo.id_tramo === selectedTramoId)) {
        setSearchParams((currentParams) => {
          const nextParams = new URLSearchParams(currentParams);
          nextParams.delete('seleccionar_tramo');
          return nextParams;
        }, { replace: true });
        return;
      }

      // El tramo es una división administrativa; su representación espacial es
      // la sección de derecho de vía, no una línea independiente.
      setTramos(resTramos.data);

      // Franjas
      const franjaFeatures = resFranjas.data
        .filter(f => f.activo && f.geometria_wkt)
        .map(franja => ({
          type: 'Feature',
          properties: {
            id_proyecto: franja.id_proyecto,
            color: '#ca8a04',
            fillColor: '#facc15',
            fillOpacity: 0.35,
            weight: 1.5,
          },
          geometry: parse(franja.geometria_wkt),
        }));
      setFranjasGeoJSON({ type: 'FeatureCollection', features: franjaFeatures });

      // Núcleos
      setNucleosGeoJSON(buildNucleosGeoJSON(resNucleos.data, selectedTramoId));
    }).catch(err => {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      console.error('Error al cargar capas:', err);
      setError('Error al cargar datos geoespaciales.');
    }).finally(() => {
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    });

    return () => abortController.abort(); // Cancelar petición si el componente se desmonta o cambia el proyecto (Fase 7)
  }, [selectedProjectId, selectedTramoId, nucleosRevision, franjasRevision, setSearchParams]);

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

      layer.bindPopup(`
        <div style="font-family: Inter, sans-serif;">
          <h3 style="margin:0 0 5px 0; color: #1e293b;">${escapeHtml(feature.properties.name)}</h3>
          <p style="margin:0; font-size: 12px; color: #64748b; text-transform: capitalize;">${escapeHtml(feature.properties.tipo)}</p>
          <hr style="margin: 8px 0; border: 0; border-top: 1px solid #e2e8f0;" />
          <p style="margin:4px 0;"><strong>Estatus:</strong> ${estatusText}</p>
          <p style="margin:4px 0;"><strong>Superficie del núcleo:</strong> ${escapeHtml(feature.properties.area_ha)} hectáreas</p>
          <p style="margin:4px 0;"><strong>Superficie en derecho de vía:</strong> ${escapeHtml(feature.properties.area_afectada_ha)} hectáreas</p>
        </div>
      `);
    }
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

  const styleFeature = (feature) => {
    return {
      color: feature.properties.color,
      weight: feature.properties.weight || 1.5,
      opacity: 1.0, // Ya no atenuamos porque filtramos las no seleccionadas
      fillColor: feature.properties.fillColor || feature.properties.color,
      fillOpacity: feature.properties.fillOpacity || 0.2
    };
  };

  const franjasVisibles = useMemo(() => {
    if (!franjasGeoJSON) return null;
    return franjasGeoJSON;
  }, [franjasGeoJSON]);

  const nucleosVisibles = useMemo(() => {
    if (!nucleosGeoJSON) return null;
    if (!selectedTramoId) return nucleosGeoJSON;
    return { ...nucleosGeoJSON, features: nucleosGeoJSON.features.filter(f => f.properties.id_tramo === selectedTramoId) };
  }, [nucleosGeoJSON, selectedTramoId]);

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

  // Determinar datos para fitBounds
  const boundsData = nucleosVisibles?.features.length
    ? nucleosVisibles
    : franjasVisibles?.features.length
      ? franjasVisibles
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
  const hasData = franjasGeoJSON?.features.length > 0
    || nucleosGeoJSON?.features.length > 0;

  // Keys para forzar re-render de GeoJSON cuando cambian los datos
  const layerKey = `proj-${selectedProjectId}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px' }}>
      <div style={{ flex: '1', position: 'relative', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', minHeight: '600px' }}>

        {/* ────── SELECTOR DE PROYECTO ────── */}
        <div className="mapa-project-selector">
          <MapPin size={16} style={{ color: '#64748b', flexShrink: 0 }} />
          <label style={{ fontSize: '13px', fontWeight: 600, color: '#334155', whiteSpace: 'nowrap' }}>
            Proyecto:
          </label>
          <select
            value={selectedProjectId === null ? '' : selectedProjectId}
            onChange={handleProjectChange}
            className="mapa-project-select"
          >
            <option value="">Seleccionar proyecto…</option>
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
          {(loading || projectsLoading) && <div className="mapa-spinner" />}
        </div>

        {/* ────── MENSAJE SIN SELECCIÓN ────── */}
        {selectedProjectId === null && !loading && !projectsLoading && !error && (
          <div className="mapa-overlay-message">
            {noProjectsAssigned ? (
              <>
                <p style={{ margin: 0, fontSize: '15px', color: '#64748b' }}>
                  No tienes proyectos asignados.
                </p>
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Contacta al administrador para obtener acceso.
                </p>
              </>
            ) : (
              <>
                <p style={{ margin: 0, fontSize: '15px', color: '#64748b' }}>
                  Selecciona un proyecto para visualizar sus datos geoespaciales.
                </p>
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Usa el selector en la esquina superior izquierda.
                </p>
              </>
            )}
          </div>
        )}

        {/* ────── MENSAJE SIN GEOMETRÍAS ────── */}
        {selectedProjectId !== null && !loading && !error && !hasData && (
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

        {/* ────── IMPORTACIÓN DE NÚCLEOS ────── */}
        {['admin', 'geografo'].includes(user?.rol) && (
          <NucleosImportPanel
            role={user.rol}
            onImportSuccess={() => setNucleosRevision((revision) => revision + 1)}
          />
        )}

        {/* ────── PANEL TÉCNICO GLASSMORPHISM (modo tramo) ────── */}
        {selectedTramoId && tramoDetalle && (
          <div className="mapa-tramo-panel" style={{
            position: 'absolute', top: '130px', left: '60px', zIndex: 1000, // Fase 8: Evitar superposición moviéndolo debajo de Selector y Importar
            background: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(12px)',
            borderRadius: '16px', width: '320px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.8)',
            fontFamily: 'Inter, sans-serif',
            overflow: 'hidden',
            maxHeight: 'calc(100% - 150px)',
            display: 'flex',
            flexDirection: 'column'
          }}>
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
        {selectedProjectId !== null && !loading && totalNucleos > 0 && (
          <div className="mapa-summary-panel">
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a' }}>
              {proyectoSeleccionado ? proyectoSeleccionado.nombre_proyecto : 'Todos los proyectos'}
            </h3>
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
                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#22c55e' }}>{liberados}</div>
                <div>Liberados</div>
              </div>
            </div>

            <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
              <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '8px', height: '8px', background: '#22c55e', borderRadius: '50%'}}></span> Liberado</span>
              <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '8px', height: '8px', background: '#94a3b8', borderRadius: '50%'}}></span> Proceso</span>
              <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><span style={{width: '8px', height: '8px', background: '#ef4444', borderRadius: '50%'}}></span> Problema</span>
            </div>

          </div>
        )}

        <MapContainer
          center={MEXICO_CENTER}
          zoom={MEXICO_ZOOM}
          style={{ height: '100%', width: '100%' }}
        >
          {/* Zoom Inteligente hacia los polígonos */}
          {boundsData && selectedProjectId !== null && (
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
                <GeoJSON
                  key={`${layerKey}-nucleos-${nucleosRevision}-sel-${selectedTramoId}`}
                  data={nucleosVisibles}
                  style={styleFeature}
                  onEachFeature={onEachNucleo}
                />
              </LayersControl.Overlay>
            )}

            {franjasVisibles?.features.length > 0 && (
              <LayersControl.Overlay checked name="Derecho de vía">
                <GeoJSON
                  key={`${layerKey}-franja-${franjasRevision}-sel-${selectedTramoId}`}
                  data={franjasVisibles}
                  style={styleFeature}
                />
              </LayersControl.Overlay>
            )}

          </LayersControl>
        </MapContainer>
      </div>
    </div>
  );
}
