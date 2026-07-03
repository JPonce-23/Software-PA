import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Captura from './pages/Captura';
import Mapa from './pages/Mapa';
import Login from './pages/Login';
import { AuthProvider, AuthContext } from './contexts/AuthContext';
import './index.css';

function Sidebar() {
  const location = useLocation();

  if (location.pathname === '/login') return null;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2 style={{ color: 'white', fontSize: '20px', letterSpacing: '1px' }}>SISTEMA<br/>LIBERACIÓN</h2>
      </div>

      <nav className="sidebar-menu">
        <Link className={`menu-item ${location.pathname === '/' ? 'active' : ''}`} to="/">Dashboard</Link>
        <Link className="captura" to="/captura">Capturar información</Link>

        <div className="menu-group" style={{ marginTop: '10px' }}>
          <h4>Proyectos</h4>
          <ul style={{ listStyle: 'none', paddingLeft: '10px', display: 'flex', flexDirection: 'column', gap: '8px', margin: '10px 0' }}>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/">Visión General (Todos)</Link></li>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/?proyecto=Tren%20Maya">Tren Maya</Link></li>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/?proyecto=AIFA%20-%20Pachuca">AIFA - Pachuca</Link></li>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/?proyecto=México%20-%20Querétaro">México - Querétaro</Link></li>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/?proyecto=Saltillo%20-%20Nuevo%20Laredo">Saltillo - Nuevo Laredo</Link></li>
            <li><Link className="menu-item" style={{padding: '5px', fontSize: '13px', background: 'transparent', color: '#cbd5e1'}} to="/?proyecto=Querétaro%20-%20Irapuato">Querétaro - Irapuato</Link></li>
          </ul>
        </div>

        <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <Link className={`menu-item ${location.pathname === '/mapa' ? 'active' : ''}`} to="/mapa">Mapa Geoespacial</Link>
          <Link className="menu-item" to="/config">Configuración</Link>
        </div>
        
        <Link className="menu-item logout" to="/login">Cerrar sesión</Link>
      </nav>
    </aside>
  );
}

function Topbar() {
  const location = useLocation();
  if (location.pathname === '/login') return null;

  return (
    <header className="topbar">
      <div>
        <h1>{location.pathname === '/captura' ? 'Captura de Información' : location.pathname === '/mapa' ? 'Visor de Mapas' : '¡Bienvenido Carlos!'}</h1>
        <p>Sistema Interno de Reportes para la Procuraduría Agraria</p>
      </div>
      <div className="user-box">
        <div className="user-info">
          <h3>Carlos Pérez Rojas</h3>
          <p>Administrador</p>
        </div>
      </div>
    </header>
  );
}

function AppContent() {
  const { user, loading } = React.useContext(AuthContext);
  const location = useLocation();

  if (loading) return <div>Cargando...</div>;

  if (!user && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-container">
      <Sidebar />
      <main className="content">
        <Topbar />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/captura" element={<Captura />} />
          <Route path="/mapa" element={<Mapa />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;
