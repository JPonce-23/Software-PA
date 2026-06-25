import React from 'react';
import { ArrowRight, Lock, Mail } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    // Simulate login and redirect to dashboard
    navigate('/');
  };

  return (
    <div className="login-container" style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #04734f 0%, #00422c 100%)',
      padding: '20px'
    }}>
      <div style={{
        background: 'white',
        padding: '50px 40px',
        borderRadius: '16px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
        width: '100%',
        maxWidth: '420px',
        textAlign: 'center'
      }}>
        <h1 style={{ color: '#04642d', marginBottom: '10px', fontSize: '24px' }}>Sistema de Liberación</h1>
        <p style={{ color: '#666', marginBottom: '40px', fontSize: '14px' }}>Procuraduría Agraria</p>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ position: 'relative' }}>
            <Mail size={20} color="#888" style={{ position: 'absolute', left: '15px', top: '14px' }} />
            <input 
              type="email" 
              placeholder="usuario@pa.gob.mx" 
              required
              style={{
                width: '100%',
                padding: '14px 15px 14px 45px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                fontSize: '15px',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
          </div>

          <div style={{ position: 'relative' }}>
            <Lock size={20} color="#888" style={{ position: 'absolute', left: '15px', top: '14px' }} />
            <input 
              type="password" 
              placeholder="Contraseña" 
              required
              style={{
                width: '100%',
                padding: '14px 15px 14px 45px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                fontSize: '15px',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
          </div>

          <a href="#" style={{ textAlign: 'right', fontSize: '13px', color: '#0bd18d', textDecoration: 'none' }}>¿Olvidaste tu contraseña?</a>

          <button type="submit" style={{
            background: '#04734f',
            color: 'white',
            padding: '15px',
            borderRadius: '8px',
            border: 'none',
            fontSize: '16px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            marginTop: '10px',
            transition: 'background 0.2s'
          }}>
            Iniciar Sesión <ArrowRight size={20} />
          </button>
        </form>

        <div style={{ marginTop: '30px', fontSize: '12px', color: '#999' }}>
          Acceso exclusivo para personal autorizado
        </div>
      </div>
    </div>
  );
}
