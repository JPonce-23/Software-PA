import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, Check, Loader2 } from 'lucide-react';
import api from '../api/axios';

export default function AlertCenter() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  const refreshCount = useCallback(async () => {
    try {
      const { data } = await api.get('/alertas/no-vistas/count');
      setCount(data.total);
    } catch {
      setCount(0);
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/alertas/no-vistas');
      setAlerts(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCount();
    const timer = window.setInterval(refreshCount, 60_000);
    return () => window.clearInterval(timer);
  }, [refreshCount]);

  useEffect(() => {
    if (open) loadAlerts();
  }, [loadAlerts, open]);

  useEffect(() => {
    const closeOnOutsideClick = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutsideClick);
    return () => document.removeEventListener('mousedown', closeOnOutsideClick);
  }, []);

  const markRead = async (idAlerta) => {
    await api.post(`/alertas/${idAlerta}/marcar-leida`);
    setAlerts((current) => current.filter((item) => item.id_alerta !== idAlerta));
    setCount((current) => Math.max(0, current - 1));
  };

  return (
    <div className="alert-center" ref={containerRef}>
      <button
        type="button"
        className="alert-trigger"
        aria-label={`${count} alertas no vistas`}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <Bell size={19} />
        {count > 0 && <span>{count > 99 ? '99+' : count}</span>}
      </button>
      {open && (
        <section className="alert-popover" aria-label="Alertas no vistas">
          <header>
            <strong>Alertas</strong>
            <span>{count} sin leer</span>
          </header>
          {loading ? (
            <div className="popover-empty"><Loader2 className="spin" size={20} /> Cargando…</div>
          ) : alerts.length === 0 ? (
            <div className="popover-empty">No tienes alertas pendientes.</div>
          ) : (
            <div className="alert-list">
              {alerts.map((alert) => (
                <article key={alert.id_alerta}>
                  <div>
                    <strong>{alert.titulo}</strong>
                    <p>{alert.descripcion || 'Sin descripción'}</p>
                    <small>{alert.fecha_evento || 'Sin fecha de evento'}</small>
                  </div>
                  <button
                    type="button"
                    title="Marcar como leída"
                    aria-label={`Marcar como leída: ${alert.titulo}`}
                    onClick={() => markRead(alert.id_alerta)}
                  >
                    <Check size={16} />
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
