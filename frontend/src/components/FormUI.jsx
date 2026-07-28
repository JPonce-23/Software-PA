/**
 * components/FormUI.jsx
 *
 * Componentes de UI reutilizables para todos los formularios modales del sistema.
 * Centralizar aquí evita duplicación y garantiza consistencia visual en toda la aplicación.
 *
 * Componentes exportados:
 *   - ModalWrapper   → Contenedor modal con overlay, cabecera coloreada y scroll interno.
 *   - SeccionHeader  → Separador visual de secciones dentro de un formulario.
 *   - Campo          → Envoltura accesible de label + input/select/textarea.
 *   - ModoBtn        → Botón de selección de modo (activo/inactivo con estilo toggle).
 *   - ErrorBanner    → Alerta de error inline estandarizada.
 *   - ExitoMsg       → Mensaje de éxito con ícono centrado, post-guardado.
 *   - BotonesAccion  → Fila de botones Cancelar / Guardar al pie del formulario.
 *
 */

import React, { useEffect, useId, useRef } from 'react';
import { X, Loader2, CheckCircle2 } from 'lucide-react';

// ─── ModalWrapper ─────────────────────────────────────────────────────────────
/**
 * @param {string}    titulo     - Título principal del modal.
 * @param {string}    subtitulo  - Descripción corta debajo del título.
 * @param {function}  onClose    - Callback al cerrar el modal.
 * @param {string}    color      - Color del acento lateral izquierdo (ej. '#006341').
 * @param {ReactNode} children   - Contenido del modal.
 * @param {string}    [maxWidth] - Ancho máximo del panel (default '680px').
 */
export function ModalWrapper({ titulo, subtitulo, onClose, color, children, maxWidth = '680px' }) {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const titleId = useId();

  useEffect(() => {
    closeRef.current?.focus();
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = panelRef.current?.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href]',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9000,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{
          background: 'white', borderRadius: '16px', width: '100%', maxWidth,
          maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
          boxShadow: '0 25px 60px rgba(0,0,0,0.2)',
        }}
      >
        {/* Cabecera con acento de color */}
        <div style={{
          padding: '24px 28px', borderBottom: '1px solid #f1f5f9',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderLeft: `5px solid ${color}`,
        }}>
          <div>
            <h2 id={titleId} style={{ fontSize: '18px', color: '#0f172a', fontWeight: '700', margin: 0 }}>{titulo}</h2>
            {subtitulo && (
              <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0 0' }}>{subtitulo}</p>
            )}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: '6px' }}
          >
            <X size={20} />
          </button>
        </div>
        {/* Contenido scrollable */}
        <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
          {children}
        </div>
      </div>
    </div>
  );
}

// ─── SeccionHeader ────────────────────────────────────────────────────────────
/**
 * Separador de sección con ícono y título en mayúsculas.
 * @param {ReactNode} icono  - Componente de ícono (Lucide).
 * @param {string}    titulo - Texto del encabezado de sección.
 */
export function SeccionHeader({ icono, titulo }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '8px',
      paddingBottom: '6px', borderBottom: '1px solid #e2e8f0',
      color: '#475569', fontSize: '13px', fontWeight: '600',
      textTransform: 'uppercase', letterSpacing: '0.5px',
    }}>
      {icono} {titulo}
    </div>
  );
}

// ─── Campo ────────────────────────────────────────────────────────────────────
/**
 * Envoltura accesible de label + control de formulario.
 * @param {string}    label    - Texto del label.
 * @param {ReactNode} children - El input, select o textarea.
 */
export function Campo({ label, children }) {
  const generatedId = useId();
  const controlId = children?.props?.id || generatedId;
  const control = React.isValidElement(children)
    ? React.cloneElement(children, { id: controlId })
    : children;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label htmlFor={controlId} style={{ fontSize: '13px', color: '#475569', fontWeight: '500' }}>{label}</label>
      {control}
    </div>
  );
}

// ─── ModoBtn ──────────────────────────────────────────────────────────────────
/**
 * Botón de selección de modo con efecto toggle (activo/inactivo).
 * @param {boolean}   activo  - Si el botón está en estado activo.
 * @param {ReactNode} icono   - Ícono del botón.
 * @param {string}    label   - Texto del botón.
 * @param {function}  onClick - Callback al hacer clic.
 */
export function ModoBtn({ activo, icono, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1, padding: '10px', borderRadius: '8px', cursor: 'pointer',
        fontSize: '13px', fontWeight: activo ? '600' : '400',
        display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'center',
        background: activo ? '#006341' : 'white',
        color: activo ? 'white' : '#64748b',
        border: `1px solid ${activo ? '#006341' : '#e2e8f0'}`,
        transition: 'all 0.2s',
      }}
    >
      {icono} {label}
    </button>
  );
}

// ─── ErrorBanner ──────────────────────────────────────────────────────────────
/**
 * Alerta de error inline estandarizada.
 * @param {string} mensaje - Texto del error a mostrar.
 */
export function ErrorBanner({ mensaje }) {
  if (!mensaje) return null;
  return (
    <div style={{
      background: '#fef2f2', border: '1px solid #fecaca',
      color: '#dc2626', padding: '12px 16px',
      borderRadius: '8px', fontSize: '14px',
    }}>
      {mensaje}
    </div>
  );
}

// ─── ExitoMsg ─────────────────────────────────────────────────────────────────
/**
 * Mensaje de éxito post-guardado con ícono centrado.
 * @param {string} mensaje - Texto a mostrar tras guardar exitosamente.
 */
export function ExitoMsg({ mensaje }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
      <CheckCircle2 size={48} color="#16a34a" style={{ display: 'block', margin: '0 auto 12px auto' }} />
      <p style={{ fontSize: '16px', color: '#16a34a', fontWeight: '600' }}>{mensaje}</p>
    </div>
  );
}

// ─── BotonesAccion ────────────────────────────────────────────────────────────
/**
 * Fila de botones al pie del formulario: Cancelar + Guardar.
 * @param {function} onClose      - Callback del botón Cancelar.
 * @param {boolean}  guardando    - Si true, deshabilita botones y muestra spinner.
 * @param {string}   labelGuardar - Texto del botón de acción primaria.
 * @param {string}   [color]      - Color de fondo del botón primario (default '#006341').
 */
export function BotonesAccion({ onClose, guardando, labelGuardar, color = '#006341' }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-end', gap: '12px',
      paddingTop: '10px', borderTop: '1px solid #f1f5f9', marginTop: '8px',
    }}>
      <button
        type="button"
        onClick={onClose}
        disabled={guardando}
        style={btnSecundario}
      >
        Cancelar
      </button>
      <button
        type="submit"
        disabled={guardando}
        style={{ ...btnPrimario, background: color }}
      >
        {guardando
          ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Guardando...</>
          : labelGuardar
        }
      </button>
    </div>
  );
}

// Estilos de botones (usados internamente en BotonesAccion)
const btnPrimario = {
  color: 'white', border: 'none', padding: '11px 24px',
  borderRadius: '8px', cursor: 'pointer', fontWeight: '600', fontSize: '14px',
  display: 'flex', alignItems: 'center', gap: '8px',
};

const btnSecundario = {
  background: 'white', color: '#64748b', border: '1px solid #e2e8f0',
  padding: '11px 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: '500', fontSize: '14px',
};
