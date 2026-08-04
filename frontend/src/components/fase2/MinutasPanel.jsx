import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ClipboardCheck, Loader2, Plus } from 'lucide-react';
import api from '../../api/axios';
import PersonaSelector from '../PersonaSelector';
import {
  Campo,
  ErrorBanner,
  ModalWrapper,
} from '../FormUI';
import { gridDos, inputStyle } from '../formStyles';
import { nombreCompleto } from '../../utils/personas';

export default function MinutasPanel({
  idTramoNucleo,
  idAfectacion = null,
  idCicloAfectacion = null,
  canWrite,
  title = 'Minutas y acuerdos',
  emptyText = 'No hay minutas registradas.',
}) {
  const [minutas, setMinutas] = useState([]);
  const [agreements, setAgreements] = useState({});
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/minutas', {
        params: {
          id_tramo_nucleo: idTramoNucleo,
          ...(idAfectacion
            ? { id_afectacion: idAfectacion }
            : { solo_compartidas: true }),
        },
      });
      setMinutas(data);
      const responses = await Promise.all(
        data.map((minute) => api.get(`/minutas/${minute.id_minuta}/acuerdos`)),
      );
      setAgreements(Object.fromEntries(
        data.map((minute, index) => [minute.id_minuta, responses[index].data]),
      ));
    } finally {
      setLoading(false);
    }
  }, [idAfectacion, idTramoNucleo]);

  useEffect(() => { load(); }, [load]);

  const markCompleted = async (agreement) => {
    await api.put(`/acuerdos/${agreement.id_acuerdo}`, {
      estatus: 'cumplido',
      fecha_cumplimiento: new Date().toISOString().slice(0, 10),
    });
    load();
  };

  if (loading) return <div className="panel-loading"><Loader2 className="spin" /> Cargando minutas…</div>;

  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>{title}</h3>
          <p>Compromisos trazables dentro del expediente.</p>
        </div>
        {canWrite && (!idAfectacion || idCicloAfectacion) && (
          <button type="button" className="button" onClick={() => setModal({ type: 'minute' })}>
            <Plus size={16} /> Nueva minuta
          </button>
        )}
      </header>

      {minutas.length === 0 ? (
        <div className="empty-state"><ClipboardCheck size={30} /> {emptyText}</div>
      ) : (
        <div className="record-list">
          {minutas.map((minute) => (
            <article className="record-card" key={minute.id_minuta}>
              <header>
                <div>
                  <strong>{minute.asunto}</strong>
                  <span>{minute.fecha_reunion} · {minute.lugar || 'Lugar no indicado'}</span>
                </div>
                {canWrite && (
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => setModal({ type: 'agreement', minute })}
                  >
                    <Plus size={14} /> Acuerdo
                  </button>
                )}
              </header>
              {minute.resumen && <p className="record-description">{minute.resumen}</p>}
              <div className="agreement-list">
                {(agreements[minute.id_minuta] || []).map((agreement) => (
                  <div key={agreement.id_acuerdo}>
                    <span className={`priority ${agreement.prioridad}`}>{agreement.prioridad}</span>
                    <div>
                      <strong>{agreement.descripcion}</strong>
                      <small>
                        {agreement.responsable_externo
                          || nombreCompleto(agreement.persona_responsable)
                          || `Responsable #${agreement.id_usuario_responsable || agreement.id_persona_responsable}`}
                        {' · '}{agreement.fecha_limite || 'Sin fecha límite'}
                      </small>
                    </div>
                    <span className={`status ${agreement.estatus === 'cumplido' ? 'success' : 'warning'}`}>
                      {agreement.estatus}
                    </span>
                    {canWrite && agreement.estatus !== 'cumplido' && (
                      <button
                        type="button"
                        className="icon-button"
                        title="Marcar como cumplido"
                        onClick={() => markCompleted(agreement)}
                      >
                        <CheckCircle2 size={17} />
                      </button>
                    )}
                  </div>
                ))}
                {(agreements[minute.id_minuta] || []).length === 0 && (
                  <p className="field-hint">La minuta todavía no tiene acuerdos.</p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {modal?.type === 'minute' && (
        <MinuteForm
          idTramoNucleo={idTramoNucleo}
          idAfectacion={idAfectacion}
          idCicloAfectacion={idCicloAfectacion}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
        />
      )}
      {modal?.type === 'agreement' && (
        <AgreementForm
          minute={modal.minute}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
        />
      )}
    </div>
  );
}

function MinuteForm({ idTramoNucleo, idAfectacion, idCicloAfectacion, onClose, onSaved }) {
  const [form, setForm] = useState({
    fecha_reunion: new Date().toISOString().slice(0, 10),
    asunto: '',
    lugar: '',
    resumen: '',
    folio: '',
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.post('/minutas', {
        id_tramo_nucleo: idTramoNucleo,
        id_afectacion: idAfectacion || null,
        id_ciclo_afectacion: idAfectacion ? idCicloAfectacion : null,
        ...form,
        lugar: form.lugar || null,
        resumen: form.resumen || null,
        folio: form.folio || null,
      });
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible guardar la minuta.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo="Nueva minuta" color="#7c3aed" onClose={onClose}>
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <div style={gridDos}>
          <Campo label="Fecha de reunión *">
            <input
              required
              type="date"
              value={form.fecha_reunion}
              onChange={(event) => setForm({ ...form, fecha_reunion: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Folio">
            <input
              value={form.folio}
              onChange={(event) => setForm({ ...form, folio: event.target.value })}
              style={inputStyle}
            />
          </Campo>
        </div>
        <Campo label="Asunto *">
          <input
            required
            value={form.asunto}
            onChange={(event) => setForm({ ...form, asunto: event.target.value })}
            style={inputStyle}
          />
        </Campo>
        <Campo label="Lugar">
          <input
            value={form.lugar}
            onChange={(event) => setForm({ ...form, lugar: event.target.value })}
            style={inputStyle}
          />
        </Campo>
        <Campo label="Resumen">
          <textarea
            rows={4}
            value={form.resumen}
            onChange={(event) => setForm({ ...form, resumen: event.target.value })}
            style={inputStyle}
          />
        </Campo>
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />} Guardar
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

function AgreementForm({ minute, onClose, onSaved }) {
  const [mode, setMode] = useState('external');
  const [person, setPerson] = useState(null);
  const [form, setForm] = useState({
    descripcion: '',
    fecha_limite: '',
    prioridad: 'media',
    responsable_externo: '',
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        descripcion: form.descripcion,
        fecha_limite: form.fecha_limite || null,
        prioridad: form.prioridad,
        ...(mode === 'external'
          ? { responsable_externo: form.responsable_externo }
          : { id_persona_responsable: person?.persona?.id_persona }),
      };
      await api.post(`/minutas/${minute.id_minuta}/acuerdos`, payload);
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible guardar el acuerdo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo="Nuevo acuerdo" subtitulo={minute.asunto} color="#7c3aed" onClose={onClose}>
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <Campo label="Descripción *">
          <textarea
            required
            rows={3}
            value={form.descripcion}
            onChange={(event) => setForm({ ...form, descripcion: event.target.value })}
            style={inputStyle}
          />
        </Campo>
        <div style={gridDos}>
          <Campo label="Fecha límite">
            <input
              type="date"
              value={form.fecha_limite}
              onChange={(event) => setForm({ ...form, fecha_limite: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Prioridad">
            <select
              value={form.prioridad}
              onChange={(event) => setForm({ ...form, prioridad: event.target.value })}
              style={inputStyle}
            >
              <option value="alta">Alta</option>
              <option value="media">Media</option>
              <option value="baja">Baja</option>
            </select>
          </Campo>
        </div>
        <div className="segmented-control">
          <button type="button" className={mode === 'external' ? 'active' : ''} onClick={() => setMode('external')}>
            Responsable externo
          </button>
          <button type="button" className={mode === 'person' ? 'active' : ''} onClick={() => setMode('person')}>
            Persona registrada
          </button>
        </div>
        {mode === 'external' ? (
          <Campo label="Nombre del responsable *">
            <input
              required
              value={form.responsable_externo}
              onChange={(event) => setForm({ ...form, responsable_externo: event.target.value })}
              style={inputStyle}
            />
          </Campo>
        ) : (
          <PersonaSelector value={person} onChange={setPerson} allowCreate={false} label="Responsable" />
        )}
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />} Guardar acuerdo
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}
