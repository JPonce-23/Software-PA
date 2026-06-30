import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import './Login.css';

export default function Login() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    const result = await login(email, password);
    if (result.success) {
      navigate('/');
    } else {
      setErrorMsg(result.message);
    }
    setLoading(false);
  };

  return (
    <div className="login-body">
      <main>
        <div className="login-container">
          
          <header className="logo-pa">
            <img src="/images/LOGO PA.png" alt="Logo PA" />
          </header>

          <div className="formulario">
            <img src="/images/LOGO SSALFER.png" alt="Logo SSALFER" />
            <form onSubmit={handleLogin}>
              
              {errorMsg && (
                <div style={{ background: '#fee2e2', color: '#dc2626', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>
                  {errorMsg}
                </div>
              )}

              <label htmlFor="nombre">Correo Institucional</label>
              <input 
                type="text" 
                id="nombre" 
                placeholder="usuario@pa.gob.mx" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              
              <label htmlFor="password">Contraseña</label>
              <input 
                type="password" 
                id="password" 
                placeholder="Ingresa la contraseña" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <a href="#">¿Olvidaste tu contraseña?</a>

              <button type="submit" disabled={loading} className="boton">
                {loading ? 'Iniciando...' : 'Iniciar sesión'}
              </button>
            </form>
          </div>

        </div>
      </main>

      <footer className="login-footer">
        <p style={{ color: 'white' }}>Acceso exclusivo para personal autorizado</p>
        <p>&copy; 2026 Procuraduría Agraria. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
}
