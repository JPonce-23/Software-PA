import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Banknote, Loader2, Plus } from 'lucide-react';
import api from '../../api/axios';
import PersonaSelector from '../PersonaSelector';
import {
  Campo,
  ErrorBanner,
  ModalWrapper,
} from '../FormUI';
import { gridDos, inputStyle } from '../formStyles';

const money = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
});

export default function PagosPanel({ idTramoNucleo, canWrite }) {
  const [tramites, setTramites] = useState([]);
  const [convenios, setConvenios] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tramitesResponse, conveniosResponse] = await Promise.all([
        api.get('/fifonafe', { params: { id_tramo_nucleo: idTramoNucleo } }),
        api.get('/convenios', { params: { id_tramo_nucleo: idTramoNucleo } }),
      ]);
      const eligible = tramitesResponse.data.filter(
        (item) => item.tipo_tramite === 'indemnizacion' && item.id_convenio,
      );
      setTramites(eligible);
      setConvenios(conveniosResponse.data);
      const paymentResponses = await Promise.all(
        eligible.map((item) => api.get('/pagos-indemnizacion', {
          params: { id_tramite_fifonafe: item.id_tramite_fifonafe },
        })),
      );
      setPayments(paymentResponses.flatMap((response) => response.data));
    } finally {
      setLoading(false);
    }
  }, [idTramoNucleo]);

  useEffect(() => { load(); }, [load]);

  const convenioMap = useMemo(
    () => Object.fromEntries(convenios.map((item) => [item.id_convenio, item])),
    [convenios],
  );

  if (loading) return <div className="panel-loading"><Loader2 className="spin" /> Cargando pagos…</div>;

  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Pagos de indemnización</h3>
          <p>El límite incluye tierra más bienes distintos a la tierra.</p>
        </div>
        {canWrite && tramites.length > 0 && (
          <button type="button" className="button" onClick={() => setShowForm(true)}>
            <Plus size={16} /> Registrar pago
          </button>
        )}
      </header>

      {tramites.length === 0 ? (
        <div className="empty-state">
          <Banknote size={30} /> No hay trámites de indemnización con convenio.
        </div>
      ) : (
        <div className="record-list">
          {tramites.map((tramite) => {
            const convenio = convenioMap[tramite.id_convenio];
            const items = payments.filter(
              (payment) => payment.id_tramite_fifonafe === tramite.id_tramite_fifonafe,
            );
            const paid = items.reduce((sum, item) => sum + Number(item.monto_pagado), 0);
            const cap = Number(convenio?.monto_100 || 0) + Number(convenio?.monto_bdt || 0);
            return (
              <article className="record-card" key={tramite.id_tramite_fifonafe}>
                <header>
                  <div>
                    <strong>Trámite #{tramite.id_tramite_fifonafe}</strong>
                    <span>Convenio #{tramite.id_convenio} · {tramite.estatus}</span>
                  </div>
                  <span className="status success">{money.format(paid)} pagado</span>
                </header>
                <div className="money-summary">
                  <span>Tierra <strong>{money.format(convenio?.monto_100 || 0)}</strong></span>
                  <span>BDT <strong>{money.format(convenio?.monto_bdt || 0)}</strong></span>
                  <span>Disponible <strong>{money.format(Math.max(0, cap - paid))}</strong></span>
                </div>
                <div className="payment-list">
                  {items.map((payment) => (
                    <div key={payment.id_pago}>
                      <strong>{money.format(payment.monto_pagado)}</strong>
                      <span>{payment.fecha_pago} · {payment.tipo_pago}</span>
                      <small>{payment.beneficiario_externo || `Persona #${payment.id_persona_beneficiaria}`}</small>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {showForm && (
        <PaymentForm
          tramites={tramites}
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

function PaymentForm({ tramites, onClose, onSaved }) {
  const [mode, setMode] = useState('external');
  const [person, setPerson] = useState(null);
  const [form, setForm] = useState({
    id_tramite_fifonafe: String(tramites[0]?.id_tramite_fifonafe || ''),
    monto_pagado: '',
    fecha_pago: new Date().toISOString().slice(0, 10),
    tipo_pago: 'parcial',
    medio_pago: 'transferencia',
    banco_emisor: '',
    referencia_bancaria: '',
    beneficiario_externo: '',
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post('/pagos-indemnizacion', {
        ...form,
        id_tramite_fifonafe: Number(form.id_tramite_fifonafe),
        monto_pagado: form.monto_pagado,
        banco_emisor: form.banco_emisor || null,
        referencia_bancaria: form.referencia_bancaria || null,
        beneficiario_externo: mode === 'external' ? form.beneficiario_externo : null,
        id_persona_beneficiaria: mode === 'person' ? person?.persona?.id_persona : null,
      });
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible registrar el pago.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo="Registrar pago" color="#0284c7" onClose={onClose}>
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <Campo label="Trámite de indemnización *">
          <select
            required
            value={form.id_tramite_fifonafe}
            onChange={(event) => setForm({ ...form, id_tramite_fifonafe: event.target.value })}
            style={inputStyle}
          >
            {tramites.map((item) => (
              <option key={item.id_tramite_fifonafe} value={item.id_tramite_fifonafe}>
                Trámite #{item.id_tramite_fifonafe} · Convenio #{item.id_convenio}
              </option>
            ))}
          </select>
        </Campo>
        <div style={gridDos}>
          <Campo label="Monto pagado *">
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.monto_pagado}
              onChange={(event) => setForm({ ...form, monto_pagado: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Fecha de pago *">
            <input
              required
              type="date"
              value={form.fecha_pago}
              onChange={(event) => setForm({ ...form, fecha_pago: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Tipo de pago">
            <select
              value={form.tipo_pago}
              onChange={(event) => setForm({ ...form, tipo_pago: event.target.value })}
              style={inputStyle}
            >
              <option value="anticipo">Anticipo</option>
              <option value="parcial">Parcial</option>
              <option value="total">Total</option>
            </select>
          </Campo>
          <Campo label="Medio">
            <select
              value={form.medio_pago}
              onChange={(event) => setForm({ ...form, medio_pago: event.target.value })}
              style={inputStyle}
            >
              <option value="transferencia">Transferencia</option>
              <option value="cheque">Cheque</option>
              <option value="deposito">Depósito</option>
              <option value="otro">Otro</option>
            </select>
          </Campo>
          <Campo label="Banco emisor">
            <input
              value={form.banco_emisor}
              onChange={(event) => setForm({ ...form, banco_emisor: event.target.value })}
              style={inputStyle}
            />
          </Campo>
          <Campo label="Referencia bancaria">
            <input
              value={form.referencia_bancaria}
              onChange={(event) => setForm({ ...form, referencia_bancaria: event.target.value })}
              style={inputStyle}
            />
          </Campo>
        </div>
        <div className="segmented-control">
          <button type="button" className={mode === 'external' ? 'active' : ''} onClick={() => setMode('external')}>
            Beneficiario externo
          </button>
          <button type="button" className={mode === 'person' ? 'active' : ''} onClick={() => setMode('person')}>
            Persona registrada
          </button>
        </div>
        {mode === 'external' ? (
          <Campo label="Beneficiario *">
            <input
              required
              value={form.beneficiario_externo}
              onChange={(event) => setForm({ ...form, beneficiario_externo: event.target.value })}
              style={inputStyle}
            />
          </Campo>
        ) : (
          <PersonaSelector value={person} onChange={setPerson} allowCreate={false} label="Beneficiario" />
        )}
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />} Registrar pago
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}
