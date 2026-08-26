import React from 'react';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../api/axios';
import { Empty, Field, Notice, PageHeader } from '../components/TargetUI';
import { apiMessage } from '../utils/target';

const COLORS = { trazo_proyecto: '#9f7928', nucleo_agrario: '#006341', parcela: '#7a3e87' };
function FitData({ data }) { const map = useMap(); React.useEffect(() => { if (!data?.features?.length) return; import('leaflet').then(({ default: L }) => { const layer = L.geoJSON(data); const bounds = layer.getBounds(); if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30] }); }); }, [data, map]); return null; }

export default function ProjectMap() {
  const [projects, setProjects] = React.useState([]); const [projectId, setProjectId] = React.useState(''); const [data, setData] = React.useState(null); const [error, setError] = React.useState('');
  React.useEffect(() => { api.get('/proyectos').then(({ data: records }) => { setProjects(records); if (records.length) setProjectId(String(records[0].id_proyecto)); }).catch((requestError) => setError(apiMessage(requestError))); }, []);
  React.useEffect(() => { if (!projectId) return; api.get(`/proyectos/${projectId}/mapa`).then(({ data: geojson }) => { setData(geojson); setError(''); }).catch((requestError) => setError(apiMessage(requestError))); }, [projectId]);
  return <section><PageHeader eyebrow="Soporte visual" title="Mapa por proyecto" description="Trazo del proyecto, núcleos y parcelas disponibles; la cartografía no condiciona el flujo administrativo." /><Notice error={error} /><div className="filter-bar"><Field label="Proyecto"><select aria-label="Proyecto" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">Selecciona</option>{projects.map((item) => <option key={item.id_proyecto} value={item.id_proyecto}>{item.nombre_proyecto}</option>)}</select></Field><div className="map-legend">{Object.entries(COLORS).map(([key, color]) => <span key={key}><i style={{ background: color }} />{key.replaceAll('_', ' ')}</span>)}</div></div>{data?.features?.length ? <div className="map-frame"><MapContainer center={[23.6, -102.5]} zoom={5} scrollWheelZoom><TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><GeoJSON key={JSON.stringify(data)} data={data} style={(feature) => ({ color: COLORS[feature.properties.tipo], weight: feature.properties.tipo === 'trazo_proyecto' ? 5 : 2, fillOpacity: .18 })} onEachFeature={(feature, layer) => layer.bindPopup(`<strong>${feature.properties.nombre}</strong><br>${feature.properties.tipo.replaceAll('_', ' ')}`)} /><FitData data={data} /></MapContainer></div> : <Empty title="Proyecto sin geometrías">Puede capturarse todo el expediente aun cuando no exista cartografía.</Empty>}</section>;
}
