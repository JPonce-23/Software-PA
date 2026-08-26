import React from 'react';
import { Download, TrendingUp } from 'lucide-react';
import api from '../api/axios';
import { Empty, Field, Notice, PageHeader } from '../components/TargetUI';
import { apiMessage, formatNumber } from '../utils/target';

const LABELS = {
  nucleos: 'Núcleos', sensibilizacion: 'Sensibilización', caminamiento: 'Caminamiento', asambleas: 'Asambleas',
  ingreso_ran_acta: 'Ingreso RAN acta', inscripcion_ran_acta: 'Inscripción RAN acta', cop_colectivos: 'COP colectivos',
  cop_individuales: 'COP individuales', modificatorios: 'Modificatorios', superficies_adicionales: 'Superficies adicionales',
  obras_complementarias: 'Obras complementarias', ampliaciones: 'Ampliaciones', ampliaciones_remanentes: 'Ampliaciones remanentes',
  retiro_fondos: 'Retiro de fondos', expropiacion_directa: 'Expropiación directa', parcelas_afectadas: 'Parcelas afectadas',
  ingreso_ran_convenio: 'Ingreso RAN convenio', inscripcion_ran_convenio: 'Inscripción RAN convenio', fifonafe: 'FIFONAFE',
  no_conflictos: 'Sin conflictos', indemnizaciones: 'Indemnizaciones', pagos: 'Pagos',
  superficie_preliminar_administrativa: 'Superficie preliminar administrativa',
  superficie_afectada_administrativa: 'Superficie afectada administrativa',
};

export default function Dashboard() {
  const [projects, setProjects] = React.useState([]);
  const [rows, setRows] = React.useState([]);
  const [projectId, setProjectId] = React.useState('');
  const [year, setYear] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const params = {}; if (projectId) params.id_proyecto = projectId; if (year) params.anio = year;
      const [projectResponse, kpiResponse] = await Promise.all([api.get('/proyectos'), api.get('/dashboard/kpi', { params })]);
      setProjects(projectResponse.data); setRows(kpiResponse.data); setError('');
    } catch (requestError) { setError(apiMessage(requestError)); }
    finally { setLoading(false); }
  }, [projectId, year]);
  React.useEffect(() => { load(); }, [load]);
  const projectNames = Object.fromEntries(projects.map((item) => [item.id_proyecto, item.nombre_proyecto]));
  const years = [...new Set(rows.map((item) => item.anio))].sort((a, b) => b - a);
  const exportUrl = `/api/exportaciones/dashboard.csv?${new URLSearchParams({ ...(projectId ? { id_proyecto: projectId } : {}), ...(year ? { anio: year } : {}) })}`;
  return <section><PageHeader eyebrow="Indicadores derivados" title="Dashboard del modelo objetivo" description="Cada familia de hechos se agrega antes de combinarse; los vínculos N:M no multiplican indicadores." action={<a className="button secondary" href={exportUrl}><Download />Exportar CSV</a>} /><Notice error={error} /><div className="filter-bar"><Field label="Proyecto"><select aria-label="Proyecto" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">Todos los autorizados</option>{projects.map((item) => <option key={item.id_proyecto} value={item.id_proyecto}>{item.nombre_proyecto}</option>)}</select></Field><Field label="Año"><select aria-label="Año" value={year} onChange={(e) => setYear(e.target.value)}><option value="">Todos</option>{years.map((value) => <option key={value} value={value}>{value}</option>)}</select></Field></div>{loading ? <div className="card">Calculando indicadores…</div> : rows.length === 0 ? <Empty title="Sin hechos en el periodo">Los KPI se mostrarán al registrar actividades, convenios y hechos financieros.</Empty> : <div className="kpi-grid">{rows.map((row) => <article className="kpi-card" key={`${row.id_proyecto}-${row.anio}-${row.indicador}`}><header><span>{projectNames[row.id_proyecto] || `Proyecto #${row.id_proyecto}`}</span><b>{row.anio}</b></header><div><TrendingUp /><h3>{LABELS[row.indicador] || row.indicador.replaceAll('_', ' ')}</h3></div><strong>{row.indicador === 'pagos' ? formatNumber(row.monto, ' MXN') : row.indicador.startsWith('superficie_') ? formatNumber(row.superficie_ha, ' ha') : formatNumber(row.cantidad)}</strong>{(row.programado > 0 || row.realizado > 0) && <p>{row.programado} programado · {row.realizado} realizado</p>}</article>)}</div>}</section>;
}
