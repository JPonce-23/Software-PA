import React, { useState, useEffect } from 'react';
import { Map as MapIcon, Layers, Maximize, CheckCircle } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON, LayersControl, useMap } from 'react-leaflet';
import { useSearchParams } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../api/axios';
import { parse } from 'wellknown';

const coloresPorTramo = {
  "Tren Maya tramo 1": "#E63946",
  "Tren Maya tramo 2": "#F4A261",
  "Tren Maya tramo 3": "#E9C46A",
  "Tren Maya tramo 4": "#2A9D8F",
  "Tren Maya tramo 5": "#219EBC",
  "Tren Maya tramo 6": "#023047",
  "Tren Maya tramo 7": "#9B2247" // Guinda Institucional (reemplaza al morado)
};

// Componente para auto-ajustar el zoom al polígono del tramo
function MapFitter({ geojsonData }) {
  const map = useMap();
  useEffect(() => {
    if (geojsonData && geojsonData.features.length > 0) {
      try {
        const layer = L.geoJSON(geojsonData);
        map.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 11 });
      } catch (e) {
        console.error("Error ajustando límites", e);
      }
    }
  }, [geojsonData, map]);
  return null;
}

export default function Mapa() {
  const [searchParams] = useSearchParams();
  const tramoParam = searchParams.get('tramo');
  
  const [tramosGeoJSON, setTramosGeoJSON] = useState(null);
  const [nucleosGeoJSON, setNucleosGeoJSON] = useState(null);
  const [tramoDetalle, setTramoDetalle] = useState(null);
  const centerPosition = [19.25, -90.25];

  useEffect(() => {
    // 1. Cargar el Tramo principal (o todos si no hay param)
    if (tramoParam) {
      api.get(`/tramo-detalles?tramo=${encodeURIComponent(tramoParam)}`).then(res => {
        setTramoDetalle(res.data);
        if (res.data.geometria_wkt) {
          setTramosGeoJSON({
            type: "FeatureCollection",
            features: [{
              type: "Feature",
              properties: { name: res.data.nombre_tramo, color: coloresPorTramo[res.data.nombre_tramo] || "#ff0000", weight: 6 },
              geometry: parse(res.data.geometria_wkt)
            }]
          });
        }
      }).catch(console.error);
    } else {
      api.get('/tramos').then(res => {
        const features = res.data.map(t => {
          if (!t.geometria_wkt) return null;
          return {
            type: "Feature",
            properties: { name: t.nombre_tramo, color: coloresPorTramo[t.nombre_tramo] || "#333333", weight: 5 },
            geometry: parse(t.geometria_wkt)
          };
        }).filter(Boolean);
        setTramosGeoJSON({ type: "FeatureCollection", features });
      }).catch(console.error);
    }

    // 2. Cargar Núcleos Agrarios (filtrados por tramo)
    const urlNucleos = tramoParam ? `/nucleos?tramo=${encodeURIComponent(tramoParam)}` : '/nucleos';
    api.get(urlNucleos).then(res => {
      const features = res.data.map(n => {
        if (!n.geometria_wkt) return null;
        
        // Semáforo agrario
        let fillColor = "#94a3b8"; // Gris - En proceso
        if (n.estatus_simulado === 'liberado') fillColor = "#22c55e"; // Verde
        if (n.estatus_simulado === 'problema') fillColor = "#ef4444"; // Rojo

        return {
          type: "Feature",
          properties: { 
            name: n.nombre_nucleo, 
            tipo: n.tipo_nucleo,
            estatus: n.estatus_simulado,
            area_ha: n.area_ha,
            color: "#ffffff", // Borde blanco
            fillColor: fillColor, 
            fillOpacity: 0.7 
          },
          geometry: parse(n.geometria_wkt)
        };
      }).filter(Boolean);

      setNucleosGeoJSON({ type: "FeatureCollection", features });
    }).catch(console.error);
  }, [tramoParam]);

  const onEachNucleo = (feature, layer) => {
    if (feature.properties && feature.properties.name) {
      const estatusText = {
        'liberado': 'Liberado',
        'en_proceso': 'En Proceso',
        'problema': 'Con Problemas'
      }[feature.properties.estatus] || 'Pendiente';

      layer.bindPopup(`
        <div style="font-family: Inter, sans-serif;">
          <h3 style="margin:0 0 5px 0; color: #1e293b;">${feature.properties.name}</h3>
          <p style="margin:0; font-size: 12px; color: #64748b; text-transform: capitalize;">${feature.properties.tipo}</p>
          <hr style="margin: 8px 0; border: 0; border-top: 1px solid #e2e8f0;" />
          <p style="margin:4px 0;"><strong>Estatus:</strong> ${estatusText}</p>
          <p style="margin:4px 0;"><strong>Superficie Afectada:</strong> ${feature.properties.area_ha} hectáreas</p>
        </div>
      `);
    }
  };

  const styleFeature = (feature) => ({
    color: feature.properties.color,
    weight: feature.properties.weight || 1.5,
    fillColor: feature.properties.fillColor || feature.properties.color,
    fillOpacity: feature.properties.fillOpacity || 0.2
  });

  const totalNucleos = nucleosGeoJSON ? nucleosGeoJSON.features.length : 0;
  const areaTotal = nucleosGeoJSON ? nucleosGeoJSON.features.reduce((acc, f) => acc + (f.properties.area_ha || 0), 0) : 0;
  const liberados = nucleosGeoJSON ? nucleosGeoJSON.features.filter(f => f.properties.estatus === 'liberado').length : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px' }}>
      <div style={{ flex: '1', position: 'relative', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', minHeight: '600px' }}>
        
        {/* PANEL TÉCNICO GLASSMORPHISM */}
        {tramoParam && tramoDetalle && (
          <div style={{
            position: 'absolute', top: '20px', left: '60px', zIndex: 1000,
            background: 'rgba(255, 255, 255, 0.85)', backdropFilter: 'blur(12px)',
            padding: '20px', borderRadius: '16px', width: '320px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.8)',
            fontFamily: 'Inter, sans-serif'
          }}>
            <h2 style={{ margin: '0 0 5px 0', fontSize: '20px', color: '#0f172a' }}>{tramoParam}</h2>
            <p style={{ margin: '0 0 20px 0', fontSize: '13px', color: '#64748b' }}>Análisis Geoespacial en Vivo</p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ background: '#e0f2fe', padding: '8px', borderRadius: '8px', color: '#0ea5e9' }}><Maximize size={18} /></div>
                <div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>Longitud del Trazo</div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>{tramoDetalle.longitud_km} km</div>
                </div>
              </div>

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
          </div>
        )}

        <MapContainer center={centerPosition} zoom={8} style={{ height: '100%', width: '100%' }}>
          {/* Zoom Inteligente hacia los poligonos */}
          {nucleosGeoJSON && <MapFitter geojsonData={nucleosGeoJSON} />}

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

            {nucleosGeoJSON && (
              <LayersControl.Overlay checked name="Núcleos Agrarios">
                <GeoJSON 
                  key={tramoParam ? tramoParam + "-nucleos" : "all-nucleos"} 
                  data={nucleosGeoJSON} 
                  style={styleFeature} 
                  onEachFeature={onEachNucleo} 
                />
              </LayersControl.Overlay>
            )}

            {tramosGeoJSON && (
              <LayersControl.Overlay checked name="Trazo Ferroviario">
                <GeoJSON 
                  key={tramoParam ? tramoParam + "-tramo" : "all-tramos"}
                  data={tramosGeoJSON} 
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
