import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Files, FolderKanban, Layers, Map } from 'lucide-react';

function ProjectCard({ tramo, proyecto, nucleosTramo }) {
  const navigate = useNavigate();

  // Agregamos métricas reales de los tramos-núcleos
  const nucleosTotales = nucleosTramo.length;
  const conveniosTotales = nucleosTramo.reduce((acc, curr) => acc + (curr.total_convenios_formalizados_ran || 0), 0);
  const superficieLiberada = nucleosTramo.reduce((acc, curr) => acc + parseFloat(curr.superficie_liberada_ha || 0), 0).toFixed(2);

  return (
    <article
      className="project-card"
      onClick={() => navigate(`/mapa?id_proyecto=${tramo.id_proyecto}&seleccionar_tramo=${tramo.id_tramo}`)}
      style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
    >
      <div className="project-card-badge">
        <FolderKanban size={14} />
        <span>{proyecto?.clave_proyecto || 'S/P'}</span>
        <strong>{proyecto?.nombre_proyecto || 'Proyecto sin asignar'}</strong>
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
  const navigate = useNavigate();
  const [tramosData, setTramosData] = useState([]);
  const [proyectosData, setProyectosData] = useState([]);
  const [metricsData, setMetricsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const proyectoFiltro = Number(searchParams.get('id_proyecto')) || null;

  useEffect(() => {
    const urlDashboard = proyectoFiltro ? `/dashboard?id_proyecto=${proyectoFiltro}` : `/dashboard`;
    Promise.all([
      api.get('/tramos'),
      api.get('/proyectos'),
      api.get(urlDashboard)
    ])
      .then(([resTramos, resProyectos, resMetrics]) => {
        setTramosData(resTramos.data);
        setProyectosData(resProyectos.data);
        setMetricsData(resMetrics.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error al conectar con la API:', err);
        setTramosData([]);
        setProyectosData([]);
        setMetricsData([]);
        setLoading(false);
      });
  }, [proyectoFiltro]);

  if (loading) return <div>Cargando métricas...</div>;

  // Filtramos la lista de tarjetas si existe un parámetro en la URL
  const handleProjectChange = (e) => {
    const value = e.target.value;
    if (value) {
      searchParams.set('id_proyecto', value);
    } else {
      searchParams.delete('id_proyecto');
    }
    setSearchParams(searchParams);
  };

  const proyectoSeleccionado = proyectosData.find((proyecto) => proyecto.id_proyecto === proyectoFiltro);
  const tramosFiltrados = proyectoFiltro
    ? tramosData.filter((tramo) => tramo.id_proyecto === proyectoFiltro)
    : tramosData;

  const titulo = proyectoSeleccionado
    ? `Tramos activos: ${proyectoSeleccionado.nombre_proyecto}`
    : 'Tramos activos (visión general)';

  // Agregados por proyecto (suma de todos los tramos filtrados)
  const totalConvenios = tramosFiltrados.reduce((acc, tramo) => {
    const mt = metricsData.filter(m => m.id_tramo === tramo.id_tramo);
    return acc + mt.reduce((a, c) => a + (c.total_convenios_formalizados_ran || 0), 0);
  }, 0);
  const totalColectivos = tramosFiltrados.reduce((acc, tramo) => {
    const mt = metricsData.filter(m => m.id_tramo === tramo.id_tramo);
    return acc + mt.reduce((a, c) => a + (c.total_convenios_colectivos_formalizados_ran || 0), 0);
  }, 0);
  const totalIndividuales = tramosFiltrados.reduce((acc, tramo) => {
    const mt = metricsData.filter(m => m.id_tramo === tramo.id_tramo);
    return acc + mt.reduce((a, c) => a + (c.total_convenios_individuales_formalizados_ran || 0), 0);
  }, 0);

  return (
    <div>
      <div className="dashboard-header">
        <h2 style={{color: '#1e293b', margin: 0}}>{titulo}</h2>
        <div className="dashboard-map-actions">
          <label className="project-filter">
            <span>Proyecto</span>
            <select value={proyectoFiltro || ''} onChange={handleProjectChange}>
              <option value="">Todos</option>
              {proyectosData.map(p => (
                <option key={p.id_proyecto} value={p.id_proyecto}>{p.nombre_proyecto}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="dashboard-map-button"
            onClick={() => navigate(proyectoFiltro ? `/mapa?id_proyecto=${proyectoFiltro}` : `/mapa?id_proyecto=all`)}
          >
            <Map size={16} />
            Ver Mapa
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', flex: 1, border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: 0, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>Convenios (Total)</h4>
          <p style={{ margin: '5px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#0f172a' }}>{totalConvenios}</p>
        </div>
        <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', flex: 1, border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: 0, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>Colectivos</h4>
          <p style={{ margin: '5px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#0f172a' }}>{totalColectivos}</p>
        </div>
        <div style={{ background: '#f8fafc', padding: '15px', borderRadius: '8px', flex: 1, border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: 0, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>Individuales</h4>
          <p style={{ margin: '5px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#0f172a' }}>{totalIndividuales}</p>
        </div>
      </div>

      {tramosFiltrados.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: 'white', borderRadius: '12px', color: '#64748b' }}>
          No hay tramos registrados para este proyecto todavía.
        </div>
      ) : (
        <section className="cards">
          {tramosFiltrados.map(tramo => {
            const metricsForTramo = metricsData.filter(m => m.id_tramo === tramo.id_tramo);
            const proyecto = proyectosData.find((item) => item.id_proyecto === tramo.id_proyecto);
            return <ProjectCard key={tramo.id_tramo} tramo={tramo} proyecto={proyecto} nucleosTramo={metricsForTramo} />;
          })}
        </section>
      )}
    </div>
  );
}
