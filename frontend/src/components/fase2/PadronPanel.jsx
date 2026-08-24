import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Edit3, Loader2, Plus } from 'lucide-react';
import api from '../../api/axios';
import { Campo, ErrorBanner, ModalWrapper } from '../FormUI';
import { gridDos, inputStyle } from '../formStyles';

function detailText(error) {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'No fue posible guardar el padrón.';
}

export default function PadronPanel({ idNucleo, canWrite }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/padrones', { params: { id_nucleo: idNucleo } });
      setItems(data);
    } catch (requestError) {
      setError(detailText(requestError));
    } finally {
      setLoading(false);
    }
  }, [idNucleo]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="phase-panel">
      <ErrorBanner mensaje={error} />
      <header className="phase-panel-header">
        <div>
          <h3>Historial del padrón</h3>
          <p>Versiones disponibles para acreditar el quórum de las asambleas.</p>
        </div>
        {canWrite && (
          <button type="button" className="button" onClick={() => setEditing({})}>
            <Plus size={16} /> Registrar padrón
          </button>
        )}
      </header>
      {loading ? (
        <div className="panel-loading"><Loader2 className="spin" /> Cargando padrón…</div>
      ) : items.length === 0 ? (
        <div className="empty-state"><CalendarDays size={28} /> No hay versiones registradas.</div>
      ) : (
        <div className="record-list">
          {items.map((item) => (
            <article className="record-card" key={item.id_padron}>
              <header>
                <div>
                  <strong>Padrón del {item.fecha_padron}</strong>
                  <span>{item.numero_ejidatarios_comuneros} ejidatarios o comuneros</span>
                </div>
                {canWrite && (
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`Editar padrón del ${item.fecha_padron}`}
                    title="Editar padrón"
                    onClick={() => setEditing(item)}
                  >
                    <Edit3 size={15} />
                  </button>
                )}
              </header>
            </article>
          ))}
        </div>
      )}
      {editing && (
        <PadronForm
          idNucleo={idNucleo}
          item={editing.id_padron ? editing : null}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }}
        />
      )}
    </div>
  );
}

function PadronForm({ idNucleo, item, onClose, onSaved }) {
  const [form, setForm] = useState({
    fecha_padron: item?.fecha_padron || '',
    numero_ejidatarios_comuneros: item?.numero_ejidatarios_comuneros ?? '',
    observaciones: item?.observaciones || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const payload = {
      fecha_padron: form.fecha_padron,
      numero_ejidatarios_comuneros: Number(form.numero_ejidatarios_comuneros),
      observaciones: form.observaciones || null,
    };
    try {
      if (item) await api.put(`/padrones/${item.id_padron}`, payload);
      else await api.post('/padrones', { id_nucleo: idNucleo, ...payload });
      onSaved();
    } catch (requestError) {
      setError(detailText(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo={item ? 'Editar padrón' : 'Registrar padrón'} onClose={onClose} color="#006341">
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <div style={gridDos}>
          <Campo label="Fecha del padrón *">
            <input required type="date" style={inputStyle} value={form.fecha_padron} onChange={(event) => setForm({ ...form, fecha_padron: event.target.value })} />
          </Campo>
          <Campo label="Ejidatarios o comuneros *">
            <input required min="0" type="number" style={inputStyle} value={form.numero_ejidatarios_comuneros} onChange={(event) => setForm({ ...form, numero_ejidatarios_comuneros: event.target.value })} />
          </Campo>
        </div>
        <Campo label="Observaciones">
          <textarea rows={2} style={inputStyle} value={form.observaciones} onChange={(event) => setForm({ ...form, observaciones: event.target.value })} />
        </Campo>
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>{saving && <Loader2 size={15} className="spin" />} Guardar</button>
        </div>
      </form>
    </ModalWrapper>
  );
}
