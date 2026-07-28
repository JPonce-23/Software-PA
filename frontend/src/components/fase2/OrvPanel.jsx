import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, ShieldCheck, Trash2, Users } from 'lucide-react';
import api from '../../api/axios';
import PersonaSelector from '../PersonaSelector';
import {
  Campo,
  ErrorBanner,
  ModalWrapper,
} from '../FormUI';
import { gridDos, inputStyle } from '../formStyles';
import { nombreCompleto } from '../../utils/personas';

const CARGOS = [
  ['comisariado_presidente', 'Presidencia del comisariado'],
  ['comisariado_secretario', 'Secretaría del comisariado'],
  ['comisariado_tesorero', 'Tesorería del comisariado'],
  ['consejo_vigilancia_presidente', 'Presidencia de vigilancia'],
  ['consejo_vigilancia_secretario1', 'Primera secretaría de vigilancia'],
  ['consejo_vigilancia_secretario2', 'Segunda secretaría de vigilancia'],
];
const CARGO_LABELS = Object.fromEntries(CARGOS);

export default function OrvPanel({ idNucleo, canWrite }) {
  const [orvs, setOrvs] = useState([]);
  const [integrantes, setIntegrantes] = useState({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/orvs', { params: { id_nucleo: idNucleo } });
      setOrvs(data);
      const memberResponses = await Promise.all(
        data.map((orv) => api.get(`/orvs/${orv.id_orv}/integrantes`)),
      );
      setIntegrantes(Object.fromEntries(
        data.map((orv, index) => [orv.id_orv, memberResponses[index].data]),
      ));
    } finally {
      setLoading(false);
    }
  }, [idNucleo]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="panel-loading"><Loader2 className="spin" /> Cargando ORV…</div>;

  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Órganos de representación y vigilancia</h3>
          <p>Integrantes vinculados a identidades normalizadas.</p>
        </div>
        {canWrite && (
          <button type="button" className="button" onClick={() => setShowForm(true)}>
            <Plus size={16} /> Registrar ORV
          </button>
        )}
      </header>

      {orvs.length === 0 ? (
        <div className="empty-state"><ShieldCheck size={30} /> No hay ORV registrados.</div>
      ) : (
        <div className="record-grid">
          {orvs.map((orv) => (
            <article className="record-card" key={orv.id_orv}>
              <header>
                <div>
                  <strong>ORV #{orv.id_orv}</strong>
                  <span>{orv.inicio_vigencia} — {orv.fin_vigencia}</span>
                </div>
                <span className={new Date(orv.fin_vigencia) < new Date() ? 'status danger' : 'status success'}>
                  {new Date(orv.fin_vigencia) < new Date() ? 'Vencido' : 'Vigente'}
                </span>
              </header>
              <div className="member-list">
                {(integrantes[orv.id_orv] || []).map((item) => (
                  <div key={item.id_orv_integrante}>
                    <Users size={15} />
                    <span>
                      <strong>{nombreCompleto(item.persona)}</strong>
                      <small>{CARGO_LABELS[item.cargo] || item.cargo}</small>
                    </span>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}

      {showForm && (
        <OrvForm
          idNucleo={idNucleo}
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function OrvForm({ idNucleo, onClose, onSaved }) {
  const [dates, setDates] = useState({ inicio_vigencia: '', fin_vigencia: '' });
  const [members, setMembers] = useState([
    { key: crypto.randomUUID(), cargo: CARGOS[0][0], selection: null },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const updateMember = (key, patch) => {
    setMembers((current) => current.map(
      (member) => member.key === key ? { ...member, ...patch } : member,
    ));
  };

  const createPersona = async (selection) => {
    if (selection?.mode === 'existing') return selection.persona;
    if (!selection?.data?.nombre?.trim()) throw new Error('Cada cargo requiere una persona.');
    const { data } = await api.post('/personas', {
      ...selection.data,
      nombre: selection.data.nombre.trim(),
      apellido_paterno: selection.data.apellido_paterno || null,
      apellido_materno: selection.data.apellido_materno || null,
      curp: selection.data.curp || null,
      rfc: selection.data.rfc || null,
      telefono: selection.data.telefono || null,
      correo_electronico: selection.data.correo_electronico || null,
    });
    return data;
  };

  const submit = async (event) => {
    event.preventDefault();
    setError(null);
    if (new Set(members.map((member) => member.cargo)).size !== members.length) {
      setError('No se puede repetir un cargo.');
      return;
    }
    setSaving(true);
    try {
      const people = await Promise.all(members.map((member) => createPersona(member.selection)));
      await api.post('/orvs/con-integrantes', {
        orv: { id_nucleo: idNucleo, ...dates },
        integrantes: members.map((member, index) => ({
          id_persona: people[index].id_persona,
          cargo: member.cargo,
          calidad_agraria: 'representante',
        })),
      });
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper
      titulo="Registrar ORV"
      subtitulo="Vigencia e integrantes del núcleo agrario"
      color="#006341"
      maxWidth="820px"
      onClose={onClose}
    >
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <div style={gridDos}>
          <Campo label="Inicio de vigencia *">
            <input
              required
              type="date"
              value={dates.inicio_vigencia}
              onChange={(event) => setDates({ ...dates, inicio_vigencia: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Fin de vigencia *">
            <input
              required
              type="date"
              min={dates.inicio_vigencia}
              value={dates.fin_vigencia}
              onChange={(event) => setDates({ ...dates, fin_vigencia: event.target.value })}
              style={inputStyle}
            />
          </Campo>
        </div>
        {members.map((member, index) => (
          <section className="form-section" key={member.key}>
            <div className="inline-heading">
              <strong>Integrante {index + 1}</strong>
              {members.length > 1 && (
                <button
                  type="button"
                  className="icon-button danger"
                  aria-label={`Quitar integrante ${index + 1}`}
                  onClick={() => setMembers((current) => current.filter((item) => item.key !== member.key))}
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
            <Campo label="Cargo *">
              <select
                value={member.cargo}
                onChange={(event) => updateMember(member.key, { cargo: event.target.value })}
                style={inputStyle}
              >
                {CARGOS.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </Campo>
            <PersonaSelector
              label="Integrante"
              value={member.selection}
              onChange={(selection) => updateMember(member.key, { selection })}
            />
          </section>
        ))}
        {members.length < CARGOS.length && (
          <button
            type="button"
            className="button secondary align-self-start"
            onClick={() => setMembers((current) => [
              ...current,
              {
                key: crypto.randomUUID(),
                cargo: CARGOS.find(([cargo]) => !current.some((item) => item.cargo === cargo))?.[0]
                  || CARGOS[0][0],
                selection: null,
              },
            ])}
          >
            <Plus size={15} /> Agregar integrante
          </button>
        )}
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />} Guardar ORV
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}
