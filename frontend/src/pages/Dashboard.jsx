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

function ProjectCard({ tramo, nucleosTramo }) {
  const navigate = useNavigate();
  
  // Agregamos métricas reales de los tramos-núcleos
  const nucleosTotales = nucleosTramo.length;
  const conveniosTotales = nucleosTramo.reduce((acc, curr) => acc + (curr.total_convenios_formalizados_ran || 0), 0);
  const superficieLiberada = nucleosTramo.reduce((acc, curr) => acc + parseFloat(curr.superficie_liberada_ha || 0), 0).toFixed(2);

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

        {/* Requerimiento 10.2 / 10.1 consolidado */}
        <div className="metric">
          <div className="icon blue"><Files size={20} /></div>
          <div>
            <small>Convenios Formalizados</small>
            <strong style={{color: '#0284c7'}}>{conveniosTotales}</strong>
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
  const [metricsData, setMetricsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const proyectoFiltro = searchParams.get('proyecto');

  useEffect(() => {
    Promise.all([
      api.get('/tramos'),
      api.get('/dashboard')
    ])
      .then(([resTramos, resMetrics]) => {
        setTramosData(resTramos.data);
        setMetricsData(resMetrics.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error al conectar con la API:', err);
        setTramosData([]);
        setMetricsData([]);
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
          {tramosFiltrados.map(tramo => {
            const metricsForTramo = metricsData.filter(m => m.id_tramo === tramo.id_tramo);
            return <ProjectCard key={tramo.id_tramo} tramo={tramo} nucleosTramo={metricsForTramo} />;
          })}
        </section>
      )}
    </div>
  );
}
