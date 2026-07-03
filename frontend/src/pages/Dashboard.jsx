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

function ProjectCard({ tramo }) {
  // Simulación para métricas visuales
  const avance = Math.floor(Math.random() * 60) + 20;
  const liberados = Math.floor(Math.random() * 200);
  const pendientes = Math.floor(Math.random() * 300);
  const problemas = Math.floor(Math.random() * 50);

  const proyecto = getProyectoMaestro(tramo.nombre_tramo);

  return (
    <article className="project-card">
      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#0ea5e9', fontWeight: 'bold', marginBottom: '8px', letterSpacing: '1px' }}>
        {proyecto}
      </div>
      <h2>{tramo.nombre_tramo}</h2>
      <div className="metrics">
        
        <div className="metric">
          <div className="icon green"><ArrowUpRight size={20} /></div>
          <div>
            <small>Avance general del proyecto</small>
            <strong>{avance}%</strong>
            <span>avance global</span>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: `${avance}%` }}></div>
            </div>
          </div>
        </div>

        <div className="metric">
          <div className="icon green"><CheckCircle2 size={20} /></div>
          <div>
            <small>Núcleos liberados</small>
            <strong>{liberados}</strong>
            <span>Sin problemas legales</span>
          </div>
        </div>

        <div className="metric">
          <div className="icon yellow"><Clock size={20} /></div>
          <div>
            <small>Núcleos pendientes</small>
            <strong className="yellow-text">{pendientes}</strong>
            <span>En gestión</span>
          </div>
        </div>

        <div className="metric">
          <div className="icon red"><AlertTriangle size={20} /></div>
          <div>
            <small>Núcleos con problema</small>
            <strong className="red-text">{problemas}</strong>
            <span>Requieren atención</span>
          </div>
        </div>

      </div>
    </article>
  );
}

export default function Dashboard() {
  const [tramosData, setTramosData] = useState([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div>
      <h2 style={{marginBottom: '20px'}}>Sectores y Frentes Activos</h2>
      <section className="cards">
        {tramosData.map(tramo => (
          <ProjectCard key={tramo.id_tramo} tramo={tramo} />
        ))}
      </section>
    </div>
  );
}
