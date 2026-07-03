import React, { useState, useEffect } from 'react';
import { Map as MapIcon, Layers } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../api/axios';
import { parse } from 'wellknown';

const coloresPorTramo = {
  "Tren Maya tramo 1": "#E63946", // Rojo
  "Tren Maya tramo 2": "#F4A261", // Naranja
  "Tren Maya tramo 3": "#E9C46A", // Amarillo
  "Tren Maya tramo 4": "#2A9D8F", // Verde esmeralda
  "Tren Maya tramo 5": "#219EBC", // Azul claro
  "Tren Maya tramo 6": "#023047", // Azul marino
  "Tren Maya tramo 7": "#8338EC"  // Morado
};

export default function Mapa() {
  const [tramosGeoJSON, setTramosGeoJSON] = useState(null);
  const [nucleosGeoJSON, setNucleosGeoJSON] = useState(null);
  const centerPosition = [19.25, -90.25]; // Coordenadas aproximadas del Sureste / Selva

  useEffect(() => {
    // Cargar Tramos
    api.get('/tramos').then(res => {
      const features = res.data.map(t => {
        if (!t.geometria_wkt) return null;
        return {
          type: "Feature",
          properties: { 
            name: t.nombre_tramo, 
            color: coloresPorTramo[t.nombre_tramo] || "#333333", 
            weight: 5 
          },
          geometry: parse(t.geometria_wkt)
        };
      }).filter(Boolean);

      setTramosGeoJSON({ type: "FeatureCollection", features });
    }).catch(console.error);

    // Cargar Núcleos
    api.get('/nucleos').then(res => {
      const features = res.data.map(n => {
        if (!n.geometria_wkt) return null;
        return {
          type: "Feature",
          properties: { name: n.nombre_nucleo, color: "#0ea5e9", fillColor: "#38bdf8", fillOpacity: 0.4 },
          geometry: parse(n.geometria_wkt)
        };
      }).filter(Boolean);

      setNucleosGeoJSON({ type: "FeatureCollection", features });
    }).catch(console.error);
  }, []);

  const onEachFeature = (feature, layer) => {
    if (feature.properties && feature.properties.name) {
      // Mantiene la ventanita emergente al hacer clic
      layer.bindPopup(`<b>${feature.properties.name}</b>`);

      // Si es un Tramo del Tren Maya, mostramos su nombre siempre visible en el mapa
      if (feature.properties.name.includes("Tren Maya")) {
        layer.bindTooltip(feature.properties.name, {
          permanent: true,       // Esto hace que el nombre se vea siempre
          direction: 'center',   // Centrado en el trazo
          className: 'etiqueta-tramo'
        });
      }
    }
  };

  const styleFeature = (feature) => {
    return {
      color: feature.properties.color,
      weight: feature.properties.weight || 2,
      fillColor: feature.properties.fillColor || feature.properties.color,
      fillOpacity: feature.properties.fillOpacity || 0.2
    };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'white', padding: '15px 25px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#04642d', fontWeight: '600' }}>
          <MapIcon size={20} /> Visor Geoespacial (Datos en Vivo)
        </div>
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <button style={{ background: '#f4f7f6', color: '#333', border: '1px solid #ddd', padding: '8px 15px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
            <Layers size={16} /> Capas
          </button>
        </div>
      </div>

      <div style={{ flex: '1', background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', minHeight: '600px' }}>
        <MapContainer center={centerPosition} zoom={8} style={{ height: '100%', width: '100%' }}>
          <LayersControl position="topright">
            
            {/* Capas Base (Mapas de fondo) */}
            <LayersControl.BaseLayer checked name="Mapa Base (OSM)">
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>
            
            <LayersControl.BaseLayer name="Satélite">
              <TileLayer
                attribution='&copy; Esri'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />
            </LayersControl.BaseLayer>

            {/* Capas Superpuestas (Datos de la BD) */}
            {nucleosGeoJSON && (
              <LayersControl.Overlay checked name="Núcleos Agrarios">
                <GeoJSON 
                  data={nucleosGeoJSON} 
                  style={styleFeature} 
                  onEachFeature={onEachFeature} 
                />
              </LayersControl.Overlay>
            )}

            {tramosGeoJSON && (
              <LayersControl.Overlay checked name="Tramos Ferroviarios">
                <GeoJSON 
                  data={tramosGeoJSON} 
                  style={styleFeature} 
                  onEachFeature={onEachFeature} 
                />
              </LayersControl.Overlay>
            )}

          </LayersControl>
        </MapContainer>
      </div>
    </div>
  );
}
