import React from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { BarChart3, FileText, FolderTree, LogOut, Map, Upload, Users } from 'lucide-react';

import api from './api/axios';
import { AuthProvider } from './contexts/AuthContext';
import AuthContext from './contexts/auth-context';
import Login from './pages/Login';
import './index.css';

const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const ProjectNavigator = React.lazy(() => import('./pages/ProjectNavigator'));
const ProjectNucleus = React.lazy(() => import('./pages/ProjectNucleus'));
const AffectationDetail = React.lazy(() => import('./pages/AffectationDetail'));
const ProjectMap = React.lazy(() => import('./pages/Mapa'));
const GeospatialImports = React.lazy(() => import('./pages/ImportacionesGeoespaciales'));
const UserAdministration = React.lazy(() => import('./pages/AdministracionUsuarios'));

const ROLE_LABELS = { admin: 'Administrador', operador: 'Operador', visualizador: 'Visualizador', geografo: 'Geógrafo' };

function Sidebar() {
  const { logout, user } = React.useContext(AuthContext);
  const location = useLocation();
  const [projects, setProjects] = React.useState([]);
  React.useEffect(() => {
    if (location.pathname === '/login') return;
    api.get('/proyectos').then(({ data }) => setProjects(data)).catch(() => setProjects([]));
  }, [location.pathname]);
  if (location.pathname === '/login') return null;
  const active = (path) => location.pathname === path || location.pathname.startsWith(`${path}/`);
  return <aside className="sidebar">
    <Link className="brand" to="/"><span>PA</span><strong>SSALFER</strong><small>Liberación de derecho de vía</small></Link>
    <nav aria-label="Navegación principal">
      <Link className={active('/dashboard') || location.pathname === '/' ? 'active' : ''} to="/dashboard"><BarChart3 />Dashboard</Link>
      <Link className={active('/proyectos') || active('/proyecto-nucleo') || active('/afectaciones') ? 'active' : ''} to="/proyectos"><FolderTree />Proyectos y núcleos</Link>
      <Link className={active('/mapa') ? 'active' : ''} to="/mapa"><Map />Mapa por proyecto</Link>
      {['admin', 'geografo'].includes(user?.rol) && <Link className={active('/importaciones') ? 'active' : ''} to="/importaciones"><Upload />Importaciones GIS</Link>}
      {user?.rol === 'admin' && <Link className={active('/administracion/usuarios') ? 'active' : ''} to="/administracion/usuarios"><Users />Usuarios y accesos</Link>}
    </nav>
    <div className="sidebar-projects"><h3>Proyectos autorizados</h3>{projects.length === 0 && <p>Sin proyectos disponibles</p>}{projects.map((project) => <Link key={project.id_proyecto} to={`/proyectos?id_proyecto=${project.id_proyecto}`}><FileText />{project.nombre_proyecto}</Link>)}</div>
    <button className="logout" type="button" onClick={logout}><LogOut />Cerrar sesión</button>
  </aside>;
}

function Topbar() {
  const { user } = React.useContext(AuthContext);
  const location = useLocation();
  if (location.pathname === '/login') return null;
  return <header className="topbar"><div><p className="eyebrow">Propiedad social · seguimiento administrativo</p><h1>Sistema de Liberación</h1></div><div className="identity"><strong>{user?.nombre || user?.correo}</strong><span>{ROLE_LABELS[user?.rol] || user?.rol}</span></div></header>;
}

function ProtectedApp() {
  const { user, loading } = React.useContext(AuthContext);
  const location = useLocation();
  if (loading) return <div className="app-loading">Restaurando sesión…</div>;
  if (!user && location.pathname !== '/login') return <Navigate to="/login" replace />;
  if (user && location.pathname === '/login') return <Navigate to="/dashboard" replace />;
  if (!user) return <Login />;
  const only = (roles, element) => roles.includes(user?.rol) ? element : <Navigate to="/dashboard" replace />;
  return <div className="app-shell"><Sidebar /><main className="main-content"><Topbar /><React.Suspense fallback={<div className="card">Cargando módulo…</div>}><Routes>
    <Route path="/" element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} />
    <Route path="/proyectos" element={<ProjectNavigator />} /><Route path="/proyecto-nucleo/:idProyectoNucleo" element={<ProjectNucleus />} /><Route path="/afectaciones/:idAfectacion" element={<AffectationDetail />} />
    <Route path="/mapa" element={<ProjectMap />} /><Route path="/importaciones" element={only(['admin', 'geografo'], <GeospatialImports />)} /><Route path="/administracion/usuarios" element={only(['admin'], <UserAdministration />)} />
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes></React.Suspense></main></div>;
}

export default function App() { return <AuthProvider><BrowserRouter><ProtectedApp /></BrowserRouter></AuthProvider>; }
