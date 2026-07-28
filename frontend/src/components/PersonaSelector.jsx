import React, { useEffect, useId, useState } from 'react';
import { Search, UserPlus } from 'lucide-react';
import api from '../api/axios';
import { nombreCompleto } from '../utils/personas';
import { Campo } from './FormUI';
import { gridDos, inputStyle } from './formStyles';

const EMPTY_PERSON = {
  nombre: '',
  apellido_paterno: '',
  apellido_materno: '',
  curp: '',
  rfc: '',
  telefono: '',
  correo_electronico: '',
};

export default function PersonaSelector({
  value,
  onChange,
  allowCreate = true,
  label = 'Persona',
}) {
  const listId = useId();
  const [mode, setMode] = useState('search');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState(EMPTY_PERSON);

  useEffect(() => {
    if (mode !== 'search' || query.trim().length < 2 || value?.persona) {
      setResults([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await api.get('/personas', {
          params: { q: query.trim(), limit: 20 },
          signal: controller.signal,
        });
        setResults(response.data);
      } catch (error) {
        if (error.code !== 'ERR_CANCELED') setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [mode, query, value?.persona]);

  const chooseMode = (nextMode) => {
    setMode(nextMode);
    setQuery('');
    setResults([]);
    setDraft(EMPTY_PERSON);
    onChange(null);
  };

  const updateDraft = (field, nextValue) => {
    const nextDraft = { ...draft, [field]: nextValue };
    setDraft(nextDraft);
    onChange({ mode: 'new', data: nextDraft });
  };

  return (
    <div className="persona-selector">
      {allowCreate && (
        <div className="segmented-control" aria-label={`Modo de captura de ${label}`}>
          <button
            type="button"
            className={mode === 'search' ? 'active' : ''}
            aria-pressed={mode === 'search'}
            onClick={() => chooseMode('search')}
          >
            <Search size={15} /> Buscar existente
          </button>
          <button
            type="button"
            className={mode === 'new' ? 'active' : ''}
            aria-pressed={mode === 'new'}
            onClick={() => chooseMode('new')}
          >
            <UserPlus size={15} /> Registrar nueva
          </button>
        </div>
      )}

      {mode === 'search' ? (
        <div className="search-combobox">
          <Campo label={`${label} *`}>
            <div className="search-input-wrap">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                role="combobox"
                aria-expanded={results.length > 0}
                aria-controls={listId}
                aria-autocomplete="list"
                value={value?.persona ? nombreCompleto(value.persona) : query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  if (value?.persona) onChange(null);
                }}
                placeholder="Nombre, CURP o RFC"
                style={{ ...inputStyle, paddingLeft: '38px' }}
              />
            </div>
          </Campo>
          {loading && <p className="field-hint">Buscando personas…</p>}
          {results.length > 0 && (
            <div id={listId} role="listbox" className="selector-results">
              {results.map((persona) => (
                <button
                  type="button"
                  role="option"
                  aria-selected={value?.persona?.id_persona === persona.id_persona}
                  key={persona.id_persona}
                  onClick={() => {
                    onChange({ mode: 'existing', persona });
                    setResults([]);
                  }}
                >
                  <strong>{nombreCompleto(persona)}</strong>
                  <span>{persona.curp || 'Sin CURP'} · {persona.rfc || 'Sin RFC'}</span>
                </button>
              ))}
            </div>
          )}
          {value?.persona && (
            <div className="selection-card">
              <strong>{nombreCompleto(value.persona)}</strong>
              <span>{value.persona.curp || 'Identidad pendiente de completar'}</span>
              <button type="button" onClick={() => onChange(null)}>Cambiar</button>
            </div>
          )}
        </div>
      ) : (
        <div className="form-stack">
          <div style={gridDos}>
            <Campo label="Nombre(s) *">
              <input
                required
                value={draft.nombre}
                onChange={(event) => updateDraft('nombre', event.target.value)}
                style={inputStyle}
              />
            </Campo>
            <Campo label="Primer apellido">
              <input
                value={draft.apellido_paterno}
                onChange={(event) => updateDraft('apellido_paterno', event.target.value)}
                style={inputStyle}
              />
            </Campo>
            <Campo label="Segundo apellido">
              <input
                value={draft.apellido_materno}
                onChange={(event) => updateDraft('apellido_materno', event.target.value)}
                style={inputStyle}
              />
            </Campo>
            <Campo label="CURP">
              <input
                maxLength={18}
                value={draft.curp}
                onChange={(event) => updateDraft('curp', event.target.value.toUpperCase())}
                style={inputStyle}
              />
            </Campo>
            <Campo label="RFC">
              <input
                maxLength={13}
                value={draft.rfc}
                onChange={(event) => updateDraft('rfc', event.target.value.toUpperCase())}
                style={inputStyle}
              />
            </Campo>
            <Campo label="Teléfono">
              <input
                value={draft.telefono}
                onChange={(event) => updateDraft('telefono', event.target.value)}
                style={inputStyle}
              />
            </Campo>
          </div>
          <Campo label="Correo electrónico">
            <input
              type="email"
              value={draft.correo_electronico}
              onChange={(event) => updateDraft('correo_electronico', event.target.value)}
              style={inputStyle}
            />
          </Campo>
        </div>
      )}
    </div>
  );
}
