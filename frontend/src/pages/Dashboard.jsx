import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ArrowUpRight, CheckCircle2, Clock, AlertTriangle, Calendar } from 'lucide-react';

function ProjectCard({ tramo }) {
  // Simulación para métricas visuales
  const avance = Math.floor(Math.random() * 60) + 20;
  const liberados = Math.floor(Math.random() * 200);
  const pendientes = Math.floor(Math.random() * 300);
  const problemas = Math.floor(Math.random() * 50);

  return (
    <article className="project-card">
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
  const [tramos, setTramos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('/api/tramos')
      .then(res => {
        setTramos(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error al conectar con la API, usando mock:', err);
        setTramos([
          { id_tramo: 1, nombre_tramo: 'AIFA - Pachuca' },
          { id_tramo: 2, nombre_tramo: 'México - Querétaro' },
          { id_tramo: 3, nombre_tramo: 'Saltillo - Nuevo Laredo' },
          { id_tramo: 4, nombre_tramo: 'Querétaro - Irapuato' }
        ]);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Cargando métricas...</div>;

  return (
    <section className="cards">
      {tramos.map(tramo => (
        <ProjectCard key={tramo.id_tramo} tramo={tramo} />
      ))}
    </section>
  );
}
