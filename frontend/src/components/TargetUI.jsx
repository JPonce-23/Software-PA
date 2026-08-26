import React from 'react';
import { AlertCircle, CheckCircle2, Plus, Trash2, X } from 'lucide-react';

export function PageHeader({ eyebrow, title, description, action }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</header>;
}

export function Notice({ error, success }) {
  if (!error && !success) return null;
  return <div className={`notice ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>{error ? <AlertCircle /> : <CheckCircle2 />}{error || success}</div>;
}

export function Empty({ title = 'Sin registros', children }) {
  return <div className="empty"><strong>{title}</strong>{children && <p>{children}</p>}</div>;
}

export function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-label={title}><header><h3>{title}</h3><button className="icon-button" type="button" aria-label="Cerrar" onClick={onClose}><X /></button></header>{children}</section></div>;
}

export function SubmitBar({ saving, onCancel, label = 'Guardar' }) {
  return <footer className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>Cancelar</button><button className="button" disabled={saving}>{saving ? 'Guardando…' : label}</button></footer>;
}

export function AddButton({ children, onClick }) {
  return <button className="button" type="button" onClick={onClick}><Plus />{children}</button>;
}

export function UnavailableBajaButton({ label = 'Dar de baja' }) {
  return <button className="icon-button danger" type="button" disabled title="Disponible después de la corrección de integridad de bajas lógicas" aria-label={`${label} (no disponible)`}><Trash2 /></button>;
}

export function Field({ label, children, hint }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
