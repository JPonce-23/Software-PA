import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, FolderOpen, MapPin, ChevronRight, ChevronDown, Loader2, X, Filter } from 'lucide-react';
import api from '../api/axios';

export default function ExpedientesList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const idTramoFiltro = searchParams.get('id_tramo') ? Number(searchParams.get('id_tramo')) : null;
  const idNucleoFiltro = searchParams.get('id_nucleo') ? Number(searchParams.get('id_nucleo')) : null;
  const idProyectoFiltro = searchParams.get('id_proyecto') ? Number(searchParams.get('id_proyecto')) : null;
  const busqueda = searchParams.get('q') || '';
  const estatusFiltro = searchParams.get('estatus') || 'todos';

  const [tramosNucleos, setTramosNucleos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [expandedProjects, setExpandedProjects] = useState({});
  const [expandedTramos, setExpandedTramos] = useState({});

  useEffect(() => {
    const cargarDatos = async () => {
      try {
        const params = new URLSearchParams();
        if (idTramoFiltro) params.set('id_tramo', String(idTramoFiltro));
        if (idNucleoFiltro) params.set('id_nucleo', String(idNucleoFiltro));
        if (idProyectoFiltro) params.set('id_proyecto', String(idProyectoFiltro));
        const tramosRes = await api.get(`/tramos-nucleos${params.toString() ? `?${params.toString()}` : ''}`);
        setTramosNucleos(tramosRes.data);
      } catch (err) {
        setError('No se pudo cargar la lista de expedientes. Verifique la conexión con el servidor.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    cargarDatos();
  }, [idTramoFiltro, idNucleoFiltro, idProyectoFiltro]);

  const filtrados = useMemo(() => {
    return tramosNucleos.filter(tn => {
      if (estatusFiltro === 'activos' && !tn.activo) return false;
      if (estatusFiltro === 'inactivos' && tn.activo) return false;

      if (!busqueda) return true;
      const termino = busqueda.toLowerCase();
      
      const nombre = tn.nombre_nucleo || '';
      const tramo = String(tn.nombre_tramo || '');
      const consec = String(tn.consecutivo || '');
      const proyecto = `${tn.clave_proyecto || ''} ${tn.nombre_proyecto || ''}`;
      const municipio = `${tn.municipio_nombre || ''} ${tn.entidad_nombre || ''}`;
      
      return (
        nombre.toLowerCase().includes(termino) ||
        tramo.toLowerCase().includes(termino) ||
        proyecto.toLowerCase().includes(termino) ||
        municipio.toLowerCase().includes(termino) ||
        consec.toLowerCase().includes(termino) ||
        String(tn.id_tramo_nucleo).includes(termino)
      );
    });
  }, [tramosNucleos, busqueda, estatusFiltro]);

  const jerarquia = useMemo(() => {
    const projects = {};
    filtrados.forEach(tn => {
      const pId = tn.id_proyecto;
      if (!projects[pId]) {
        projects[pId] = {
          id: pId,
          clave: tn.clave_proyecto,
          nombre: tn.nombre_proyecto,
          tramos: {},
          totalExpedientes: 0
        };
      }
      
      const tId = tn.id_tramo;
      if (!projects[pId].tramos[tId]) {
        projects[pId].tramos[tId] = {
          id: tId,
          nombre: tn.nombre_tramo || `Tramo ${tn.numero_tramo}`,
          expedientes: []
        };
      }
      
      projects[pId].tramos[tId].expedientes.push(tn);
      projects[pId].totalExpedientes++;
    });
    return Object.values(projects);
  }, [filtrados]);

  // Si hay búsqueda, expandir todo automáticamente
  const isSearching = busqueda.trim().length > 0;

  const toggleProject = (pId) => {
    if (isSearching) return;
    setExpandedProjects(prev => ({ ...prev, [pId]: !prev[pId] }));
  };

  const toggleTramo = (tId) => {
    if (isSearching) return;
    setExpandedTramos(prev => ({ ...prev, [tId]: !prev[tId] }));
  };

  const handleSearch = (val) => {
    const nextParams = new URLSearchParams(searchParams);
    if (val) nextParams.set('q', val);
    else nextParams.delete('q');
    setSearchParams(nextParams);
  };

  const handleStatusChange = (val) => {
    const nextParams = new URLSearchParams(searchParams);
    if (val === 'todos') nextParams.delete('estatus');
    else nextParams.set('estatus', val);
    setSearchParams(nextParams);
  };

  const handleLimpiarFiltros = () => {
    setSearchParams(new URLSearchParams());
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', gap: '12px', color: '#64748b' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <span>Cargando expedientes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', background: '#fef2f2', borderRadius: '12px', color: '#dc2626', border: '1px solid #fecaca' }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header & Controls */}
      <div style={{ background: 'white', padding: '20px 24px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#006341', fontWeight: '600', fontSize: '18px' }}>
            <FolderOpen size={24} />
            Expedientes por proyecto, tramo y núcleo
            <span style={{ background: '#e0f0eb', color: '#006341', borderRadius: '20px', padding: '2px 10px', fontSize: '13px', marginLeft: '8px' }}>
              {filtrados.length} expedientes
            </span>
          </div>

          {(idTramoFiltro || idNucleoFiltro || idProyectoFiltro || busqueda || estatusFiltro !== 'todos') && (
            <button
              type="button"
              style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#fef3c7', color: '#d97706', borderRadius: '20px', padding: '4px 12px', fontSize: '13px', border: '1px solid #fde68a', cursor: 'pointer', fontWeight: '500' }}
              onClick={handleLimpiarFiltros}
            >
              Filtros activos <X size={14} />
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1', minWidth: '280px' }}>
            <Search size={18} color="#94a3b8" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Buscar por ejido, tramo, municipio, consecutivo..."
              value={busqueda}
              onChange={e => handleSearch(e.target.value)}
              style={{ width: '100%', padding: '12px 14px 12px 42px', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', fontSize: '14px', transition: 'border-color 0.2s' }}
              onFocus={e => e.target.style.borderColor = '#006341'}
              onBlur={e => e.target.style.borderColor = '#cbd5e1'}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#f8fafc', padding: '4px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <Filter size={16} color="#64748b" style={{ margin: '0 4px' }} />
            {['todos', 'activos', 'inactivos'].map(status => (
              <button
                key={status}
                onClick={() => handleStatusChange(status)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  background: estatusFiltro === status ? '#006341' : 'transparent',
                  color: estatusFiltro === status ? 'white' : '#64748b',
                  fontSize: '13px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'all 0.2s'
                }}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Accordion List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {jerarquia.length === 0 ? (
          <div style={{ background: 'white', padding: '60px', textAlign: 'center', color: '#94a3b8', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
            <FolderOpen size={48} style={{ marginBottom: '16px', opacity: 0.3, display: 'block', margin: '0 auto 16px auto' }} />
            <p style={{ fontSize: '18px', fontWeight: '500', color: '#475569' }}>No se encontraron expedientes</p>
            <p style={{ fontSize: '14px', marginTop: '8px' }}>
              {busqueda ? 'Intenta con otro término de búsqueda.' : 'No hay expedientes registrados aún.'}
            </p>
          </div>
        ) : (
          jerarquia.map(proj => {
            const isProjExpanded = isSearching || expandedProjects[proj.id];
            const tramosList = Object.values(proj.tramos);
            
            return (
              <div key={proj.id} style={{ background: 'white', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
                {/* Project Header */}
                <div 
                  onClick={() => toggleProject(proj.id)}
                  style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: isSearching ? 'default' : 'pointer', background: isProjExpanded ? '#f8fafc' : 'white', borderBottom: isProjExpanded ? '1px solid #e2e8f0' : 'none', transition: 'background 0.2s' }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontWeight: '700', fontSize: '16px', color: '#1e293b' }}>{proj.nombre || 'Proyecto sin nombre'}</span>
                      <span style={{ fontSize: '12px', background: '#e2e8f0', color: '#475569', padding: '2px 8px', borderRadius: '12px', fontWeight: '600' }}>{proj.clave || 'S/C'}</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#64748b' }}>
                      {proj.totalExpedientes} expedientes en {tramosList.length} tramos
                    </div>
                  </div>
                  {!isSearching && (
                    <div style={{ color: '#94a3b8' }}>
                      {isProjExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                    </div>
                  )}
                </div>

                {/* Tramos List */}
                {isProjExpanded && (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {tramosList.map((tramo, tIdx) => {
                      const isTramoExpanded = isSearching || expandedTramos[tramo.id];
                      
                      return (
                        <div key={tramo.id} style={{ borderTop: tIdx > 0 ? '1px solid #f1f5f9' : 'none' }}>
                          <div 
                            onClick={() => toggleTramo(tramo.id)}
                            style={{ padding: '12px 24px 12px 48px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: isSearching ? 'default' : 'pointer', background: isTramoExpanded ? '#fcfcfc' : 'white', transition: 'background 0.2s' }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              {!isSearching && (
                                <span style={{ color: '#94a3b8' }}>{isTramoExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</span>
                              )}
                              <span style={{ fontWeight: '600', color: '#334155', fontSize: '14px' }}>{tramo.nombre}</span>
                              <span style={{ fontSize: '12px', color: '#94a3b8' }}>({tramo.expedientes.length} núcleos)</span>
                            </div>
                          </div>

                          {/* Expedientes Table */}
                          {isTramoExpanded && (
                            <div style={{ padding: '0 24px 16px 48px' }}>
                              <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                  <thead>
                                    <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                                      <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '600' }}>Núcleo Agrario</th>
                                      <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '600' }}>Municipio</th>
                                      <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '600' }}>Consecutivo</th>
                                      <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '600' }}>Longitud</th>
                                      <th style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: '600' }}>Estatus</th>
                                      <th style={{ padding: '10px 16px', textAlign: 'right' }}></th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {tramo.expedientes.map((exp, eIdx) => (
                                      <tr 
                                        key={exp.id_tramo_nucleo} 
                                        onClick={() => navigate(`/expedientes/${exp.id_tramo_nucleo}`)}
                                        style={{ borderTop: eIdx > 0 ? '1px solid #f1f5f9' : 'none', cursor: 'pointer', transition: 'background 0.15s' }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = '#f0fdf4'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                                      >
                                        <td style={{ padding: '12px 16px', fontWeight: '500', color: '#1e293b' }}>
                                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <MapPin size={14} color="#006341" />
                                            {exp.nombre_nucleo || `Núcleo #${exp.id_nucleo}`}
                                          </div>
                                        </td>
                                        <td style={{ padding: '12px 16px', color: '#475569' }}>
                                          {exp.municipio_nombre || '—'}
                                        </td>
                                        <td style={{ padding: '12px 16px', color: '#475569' }}>
                                          {exp.consecutivo || '—'}
                                        </td>
                                        <td style={{ padding: '12px 16px', color: '#475569' }}>
                                          {exp.longitud_m ? `${Number(exp.longitud_m).toLocaleString()} m` : '—'}
                                        </td>
                                        <td style={{ padding: '12px 16px' }}>
                                          <span style={{ background: exp.activo ? '#dcfce7' : '#fee2e2', color: exp.activo ? '#16a34a' : '#dc2626', borderRadius: '20px', padding: '2px 8px', fontSize: '11px', fontWeight: '600' }}>
                                            {exp.activo ? 'Activo' : 'Inactivo'}
                                          </span>
                                        </td>
                                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end', color: '#006341', fontWeight: '600', fontSize: '12px' }}>
                                            Abrir
                                            <ChevronRight size={14} />
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
