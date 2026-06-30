import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Captura from './pages/Captura';
import Mapa from './pages/Mapa';
import Login from './pages/Login';
import { AuthProvider } from './contexts/AuthContext';
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
          <h4>Tramos</h4>
          <ul>
            <li>AIFA - Pachuca</li>
            <li>México - Querétaro</li>
            <li>Saltillo - Nuevo Laredo</li>
            <li>Querétaro - Irapuato</li>
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

function App() {
  return (
    <AuthProvider>
      <Router>
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
      </Router>
    </AuthProvider>
  );
}

export default App;
