import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { ArrowUpRight, CheckCircle2, Clock, AlertTriangle, Calendar } from 'lucide-react';

const PROYECTOS_MAESTROS = [
  "Tren Maya", 
  "AIFA - Pachuca", 
  "México - Querétaro", 
  "Saltillo - Nuevo Laredo", 
  "Querétaro - Irapuato"
];

function getProyectoMaestro(nombreTramo) {
  for (const proyecto of PROYECTOS_MAESTROS) {
    if (nombreTramo.includes(proyecto)) return proyecto;
  }
  return "Proyecto General";
}

import { useNavigate, useSearchParams } from 'react-router-dom';
import { Map, Files, FileText, Layers } from 'lucide-react';

function ProjectCard({ tramo }) {
  const navigate = useNavigate();
  // Simulación de las métricas exigidas por Requerimientos 10 y 11
  const nucleosTotales = Math.floor(Math.random() * 50) + 10;
  const conveniosColectivos = Math.floor(Math.random() * 15);
  const conveniosIndividuales = Math.floor(Math.random() * 100);
  const superficieLiberada = (Math.random() * 500 + 100).toFixed(2);

  const proyecto = getProyectoMaestro(tramo.nombre_tramo);

  return (
    <article 
      className="project-card" 
      onClick={() => navigate(`/mapa?tramo=${encodeURIComponent(tramo.nombre_tramo)}`)}
      style={{ cursor: 'pointer', transition: 'transform 0.2s', '&:hover': { transform: 'translateY(-5px)' } }}
    >
      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: 'bold', marginBottom: '8px', letterSpacing: '1px' }}>
        {proyecto}
      </div>
      <h2>{tramo.nombre_tramo}</h2>
      
      <div className="metrics">
        
        {/* Requerimiento 10.3 */}
        <div className="metric">
          <div className="icon dark"><Map size={20} /></div>
          <div>
            <small>Total Núcleos Afectados</small>
            <strong>{nucleosTotales}</strong>
            <span>Ejidos y Comunidades</span>
          </div>
        </div>

        {/* Requerimiento 10.2 */}
        <div className="metric">
          <div className="icon blue"><Files size={20} /></div>
          <div>
            <small>Conv. Colectivos Formalizados</small>
            <strong style={{color: '#0284c7'}}>{conveniosColectivos}</strong>
            <span>Inscritos en RAN</span>
          </div>
        </div>

        {/* Requerimiento 10.1 */}
        <div className="metric">
          <div className="icon yellow"><FileText size={20} /></div>
          <div>
            <small>Conv. Individuales Formalizados</small>
            <strong className="yellow-text">{conveniosIndividuales}</strong>
            <span>Inscritos en RAN</span>
          </div>
        </div>

        {/* Requerimiento 11.1 y 11.2 */}
        <div className="metric">
          <div className="icon green"><Layers size={20} /></div>
          <div>
            <small>Superficie Total Liberada</small>
            <strong style={{color: '#006341'}}>{superficieLiberada}</strong>
            <span>Hectáreas liberadas</span>
          </div>
        </div>

      </div>
    </article>
  );
}

export default function Dashboard() {
  const [tramosData, setTramosData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const proyectoFiltro = searchParams.get('proyecto');

  useEffect(() => {
    api.get('/tramos')
      .then(res => {
        setTramosData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error al conectar con la API:', err);
        setTramosData([]); // Si falla, que inicie vacío
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Cargando métricas...</div>;

  // Filtramos la lista de tarjetas si existe un parámetro en la URL
  const tramosFiltrados = proyectoFiltro 
    ? tramosData.filter(tramo => getProyectoMaestro(tramo.nombre_tramo) === proyectoFiltro)
    : tramosData;

  const titulo = proyectoFiltro 
    ? `Sectores y Frentes Activos: ${proyectoFiltro}`
    : `Sectores y Frentes Activos (Visión General)`;

  return (
    <div>
      <h2 style={{marginBottom: '20px', color: '#1e293b'}}>{titulo}</h2>
      
      {tramosFiltrados.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: 'white', borderRadius: '12px', color: '#64748b' }}>
          No hay tramos registrados para este proyecto todavía.
        </div>
      ) : (
        <section className="cards">
          {tramosFiltrados.map(tramo => (
            <ProjectCard key={tramo.id_tramo} tramo={tramo} />
          ))}
        </section>
      )}
    </div>
  );
}
