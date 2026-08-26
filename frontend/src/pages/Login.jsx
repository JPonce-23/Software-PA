import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthContext from '../contexts/auth-context';
import './Login.css';

export default function Login() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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
      <main className="login-main">
        <div className="login-container">
          <header className="logo-pa">
            <img src="/images/LOGO PA.png" alt="Logo PA" />
            <p>Seguimiento administrativo de liberación de derecho de vía</p>
          </header>

          <div className="formulario">
            <section className="login-card" aria-labelledby="login-title">
              <img src="/images/LOGO SSALFER.png" alt="SSALFER" />
              <h1 id="login-title">Acceso al sistema</h1>
              <p className="login-intro">Ingresa con tu cuenta institucional.</p>
              <form onSubmit={handleLogin}>
                {errorMsg && (
                  <div className="login-error" role="alert">
                    {errorMsg}
                  </div>
                )}

                <label htmlFor="correo">Correo institucional</label>
                <input
                  type="email"
                  id="correo"
                  name="correo"
                  autoComplete="username"
                  placeholder="usuario@pa.gob.mx"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />

                <label htmlFor="password">Contraseña</label>
                <div className="password-control">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    name="password"
                    autoComplete="current-password"
                    placeholder="Ingresa la contraseña"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
                    {showPassword ? 'Ocultar' : 'Mostrar'}
                  </button>
                </div>

                <button type="submit" disabled={loading} className="boton">
                  {loading ? 'Iniciando sesión…' : 'Iniciar sesión'}
                </button>
              </form>
            </section>
          </div>
        </div>
      </main>

      <footer className="login-footer">
        <p>Acceso exclusivo para personal autorizado</p>
        <p>&copy; 2026 Procuraduría Agraria. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
}
