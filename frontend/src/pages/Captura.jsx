import React from 'react';
import { Users, Search, Plus, FileText, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

export default function Captura() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '25px', height: '100%' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'white', padding: '15px 25px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#04642d', fontWeight: '600' }}>
          <Users size={20} /> Colectivos
        </div>
        
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={18} color="#888" style={{ position: 'absolute', left: '15px', top: '10px' }} />
          <input 
            type="text" 
            placeholder="Buscar núcleo agrario..." 
            style={{ width: '100%', padding: '10px 15px 10px 40px', borderRadius: '20px', border: '1px solid #ddd', outline: 'none' }}
          />
        </div>

        <button style={{ background: '#04734f', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '500' }}>
          <Plus size={18} /> Nuevo registro
        </button>
      </div>

      <div style={{ display: 'flex', gap: '25px', flex: '1' }}>
        
        {/* Sidebar Secciones */}
        <aside style={{ width: '250px', background: 'white', borderRadius: '12px', padding: '25px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)', alignSelf: 'flex-start' }}>
          <h3 style={{ fontSize: '12px', color: '#888', marginBottom: '20px', letterSpacing: '1px' }}>SECCIONES DEL PROCESO</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#04734f', fontWeight: '600', fontSize: '14px' }}>
              <CheckCircle2 size={16} /> Datos Generales
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#d97706', fontSize: '14px' }}>
              <Clock size={16} /> Identificación del tramo
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#d97706', fontSize: '14px' }}>
              <Clock size={16} /> Sensibilización
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#aaa', fontSize: '14px' }}>
              <AlertCircle size={16} /> Caminamiento
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#aaa', fontSize: '14px' }}>
              <AlertCircle size={16} /> Asamblea de anuencia
            </div>
          </div>
        </aside>

        {/* Formulario Central */}
        <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ background: 'white', borderRadius: '12px', padding: '30px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '25px', borderBottom: '1px solid #eee', paddingBottom: '15px' }}>
              <div style={{ background: '#e6f4ea', color: '#04734f', padding: '10px', borderRadius: '10px' }}><FileText size={24} /></div>
              <div>
                <h2 style={{ color: '#04642d', fontSize: '18px' }}>1. Datos Generales</h2>
                <p style={{ color: '#777', fontSize: '13px' }}>Ingrese la información general del núcleo agrario</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '13px', color: '#555', fontWeight: '500' }}>Entidad *</label>
                <select style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd', outline: 'none' }}>
                  <option>Seleccione una entidad</option>
                </select>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '13px', color: '#555', fontWeight: '500' }}>Municipio *</label>
                <select style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd', outline: 'none' }}>
                  <option>Seleccione un municipio</option>
                </select>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', gridColumn: '1 / -1' }}>
                <label style={{ fontSize: '13px', color: '#555', fontWeight: '500' }}>Núcleo Agrario *</label>
                <input type="text" placeholder="Nombre del núcleo agrario" style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd', outline: 'none' }} />
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '30px' }}>
              <button style={{ background: '#0bd18d', color: '#00422c', border: 'none', padding: '12px 25px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Guardar y Continuar</button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
