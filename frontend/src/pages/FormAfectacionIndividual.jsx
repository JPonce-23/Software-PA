import React, { useEffect, useState } from 'react';
import { FileText, Loader2, MapPinned, UserRound } from 'lucide-react';
import api from '../api/axios';
import AfectacionGeometryField from '../components/AfectacionGeometryField';
import PersonaSelector from '../components/PersonaSelector';
import { normalizePolygonWkt } from '../utils/geometry';
import { nombreCompleto } from '../utils/personas';
import {
  Campo,
  ErrorBanner,
  ExitoMsg,
  ModalWrapper,
  SeccionHeader,
} from '../components/FormUI';
import { gridDos, inputStyle } from '../components/formStyles';

const EMPTY_PARCELA = {
  tipo_parcela: 'individual',
  no_parcela_ppt: '',
  certificado_parcelario: '',
  folio_derechos: '',
  constancia_vigencia_fecha: '',
  documentacion_disponible: false,
  documentacion_faltante: '',
};

function nullable(value) {
  return typeof value === 'string' ? value.trim() || null : value;
}

export default function FormAfectacionIndividual({
  idNucleo,
  idTramoNucleo,
  initialData = null,
  onSuccess,
  onClose,
}) {
  const [personaSelection, setPersonaSelection] = useState(null);
  const [parcelas, setParcelas] = useState([]);
  const [idParcelaSeleccionada, setIdParcelaSeleccionada] = useState('');
  const [crearParcela, setCrearParcela] = useState(false);
  const [parcela, setParcela] = useState(EMPTY_PARCELA);
  const [copropietarios, setCopropietarios] = useState([]);
  const [afectacion, setAfectacion] = useState({
    tipo_tenencia: initialData?.tipo_tenencia || 'Parcelada',
    subtipo_tenencia: initialData?.subtipo_tenencia || '',
    superficie_afectada_ha: initialData?.superficie_afectada_ha || '',
    situacion_juridica: initialData?.situacion_juridica || '',
    geometria_wkt: initialData?.geometria_wkt || '',
    documentacion_disponible: initialData?.documentacion_disponible || false,
    documentacion_faltante: initialData?.documentacion_faltante || '',
  });
  const [loadingParcelas, setLoadingParcelas] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [exito, setExito] = useState(false);

  useEffect(() => {
    const idPersona = personaSelection?.persona?.id_persona;
    if (!idPersona || initialData) {
      setParcelas([]);
      return undefined;
    }
    let active = true;
    setLoadingParcelas(true);
    api.get('/parcelas', { params: { id_nucleo: idNucleo, id_persona: idPersona } })
      .then(({ data }) => {
        if (!active) return;
        setParcelas(data);
        if (data.length === 0) setCrearParcela(true);
      })
      .catch(() => {
        if (active) setParcelas([]);
      })
      .finally(() => {
        if (active) setLoadingParcelas(false);
      });
    return () => { active = false; };
  }, [idNucleo, initialData, personaSelection?.persona?.id_persona]);

  const updateParcela = (field, value) => {
    setParcela((current) => ({ ...current, [field]: value }));
  };
  const updateAfectacion = (field, value) => {
    setAfectacion((current) => ({ ...current, [field]: value }));
  };

  const createPersonaIfNeeded = async (selection) => {
    if (selection?.mode === 'existing') return selection.persona;
    const draft = selection?.data;
    if (!draft?.nombre?.trim()) {
      throw new Error('Captura el nombre de la persona titular.');
    }
    const response = await api.post('/personas', {
      ...draft,
      nombre: draft.nombre.trim(),
      apellido_paterno: nullable(draft.apellido_paterno),
      apellido_materno: nullable(draft.apellido_materno),
      curp: nullable(draft.curp),
      rfc: nullable(draft.rfc),
      telefono: nullable(draft.telefono),
      correo_electronico: nullable(draft.correo_electronico),
    });
    return response.data;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    let geometriaWkt;
    try {
      geometriaWkt = normalizePolygonWkt(afectacion.geometria_wkt);
    } catch (geometryError) {
      setError(geometryError.message);
      return;
    }

    setGuardando(true);
    try {
      const payload = {
        id_nucleo: idNucleo,
        id_tramo_nucleo: idTramoNucleo,
        tipo_afectacion: 'individual',
        tipo_tenencia: afectacion.tipo_tenencia || 'Parcelada',
        subtipo_tenencia: nullable(afectacion.subtipo_tenencia),
        superficie_afectada_ha: afectacion.superficie_afectada_ha
          ? Number(afectacion.superficie_afectada_ha)
          : null,
        situacion_juridica: nullable(afectacion.situacion_juridica),
        geometria_wkt: geometriaWkt,
        documentacion_disponible: afectacion.documentacion_disponible,
        documentacion_faltante: nullable(afectacion.documentacion_faltante),
        origen_registro: 'captura_sistema',
      };
      if (initialData) {
        await api.put(`/afectaciones/individuales/${initialData.id_afectacion}`, {
          tipo_tenencia: payload.tipo_tenencia,
          subtipo_tenencia: payload.subtipo_tenencia,
          superficie_afectada_ha: payload.superficie_afectada_ha,
          situacion_juridica: payload.situacion_juridica,
          geometria_wkt: payload.geometria_wkt,
          documentacion_disponible: payload.documentacion_disponible,
          documentacion_faltante: payload.documentacion_faltante,
        });
      } else {
        if (!personaSelection) throw new Error('Selecciona o registra a la persona titular.');
        if (crearParcela || personaSelection.mode === 'new') {
          const selecciones = [personaSelection, ...copropietarios];
          if (parcela.tipo_parcela === 'copropiedad' && selecciones.length < 2) {
            throw new Error('Una copropiedad requiere al menos dos titulares.');
          }
          const personas = await Promise.all(selecciones.map(createPersonaIfNeeded));
          payload.parcela = {
            modo: 'nueva',
            tipo_parcela: parcela.tipo_parcela,
            no_parcela_ppt: nullable(parcela.no_parcela_ppt),
            certificado_parcelario: nullable(parcela.certificado_parcelario),
            folio_derechos: nullable(parcela.folio_derechos),
            constancia_vigencia_fecha: nullable(parcela.constancia_vigencia_fecha),
            documentacion_disponible: parcela.documentacion_disponible,
            documentacion_faltante: nullable(parcela.documentacion_faltante),
            titulares: personas.map((persona, index) => ({
              id_persona: persona.id_persona,
              tipo_derecho: index === 0 ? 'titular' : 'cotitular',
            })),
          };
        } else {
          if (!idParcelaSeleccionada) throw new Error('Selecciona una parcela o registra una nueva.');
          payload.parcela = { modo: 'existente', id_parcela: Number(idParcelaSeleccionada) };
        }
        await api.post('/afectaciones/individuales', payload);
      }
      setExito(true);
      window.setTimeout(() => {
        onSuccess();
        onClose();
      }, 900);
    } catch (requestError) {
      const detail = requestError.response?.data?.detail || requestError.message;
      setError(detail || 'No fue posible guardar la afectación.');
    } finally {
      setGuardando(false);
    }
  };

  return (
    <ModalWrapper
      titulo={initialData ? 'Editar afectación individual' : 'Nueva afectación individual'}
      subtitulo="La persona y su titularidad se registran como relaciones normalizadas."
      onClose={onClose}
      color="#d97706"
      maxWidth="780px"
    >
      {exito ? <ExitoMsg mensaje="Afectación individual guardada" /> : (
        <form className="form-stack" onSubmit={handleSubmit}>
          <ErrorBanner mensaje={error} />

          <section className="form-section">
            <SeccionHeader icono={<UserRound size={16} />} titulo="Persona titular" />
            {initialData ? (
              <div className="selection-card">
                <strong>Parcela #{initialData.id_parcela}</strong>
                <span>La titularidad se administra desde la parcela.</span>
              </div>
            ) : (
              <PersonaSelector
                label="Titular"
                value={personaSelection}
                onChange={(nextValue) => {
                  setPersonaSelection(nextValue);
                  setIdParcelaSeleccionada('');
                  setCrearParcela(nextValue?.mode === 'new');
                }}
              />
            )}
          </section>

          {!initialData && personaSelection?.mode === 'existing' && (
            <section className="form-section">
              <SeccionHeader icono={<MapPinned size={16} />} titulo="Parcela del titular" />
              {loadingParcelas ? <p className="field-hint">Consultando parcelas…</p> : (
                <>
                  {parcelas.length > 0 && (
                    <Campo label="Parcela existente">
                      <select
                        value={idParcelaSeleccionada}
                        disabled={crearParcela}
                        onChange={(event) => setIdParcelaSeleccionada(event.target.value)}
                        style={inputStyle}
                      >
                        <option value="">Seleccione…</option>
                        {parcelas.map((item) => (
                          <option key={item.id_parcela} value={item.id_parcela}>
                            Parcela #{item.id_parcela} · PPT {item.no_parcela_ppt || 'sin dato'}
                          </option>
                        ))}
                      </select>
                    </Campo>
                  )}
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={crearParcela}
                      onChange={(event) => setCrearParcela(event.target.checked)}
                    />
                    Registrar una parcela nueva para {nombreCompleto(personaSelection.persona)}
                  </label>
                </>
              )}
            </section>
          )}

          {!initialData && (personaSelection?.mode === 'new' || crearParcela) && (
            <ParcelaFields value={parcela} onChange={updateParcela} />
          )}

          {!initialData && (personaSelection?.mode === 'new' || crearParcela) && parcela.tipo_parcela === 'copropiedad' && (
            <section className="form-section">
              <SeccionHeader icono={<UserRound size={16} />} titulo="Copropietarios" />
              <p className="field-hint">Registra al menos una persona adicional antes de crear la afectación.</p>
              {copropietarios.map((selection, index) => (
                <div key={index} style={{ display: 'flex', gap: '8px', alignItems: 'end', marginBottom: '10px' }}>
                  <div style={{ flex: 1 }}>
                    <PersonaSelector
                      label={`Copropietario ${index + 2}`}
                      value={selection}
                      onChange={(nextValue) => setCopropietarios((current) => current.map(
                        (item, itemIndex) => itemIndex === index ? nextValue : item
                      ))}
                    />
                  </div>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => setCopropietarios((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                  >Quitar</button>
                </div>
              ))}
              <button
                type="button"
                className="button secondary"
                onClick={() => setCopropietarios((current) => [...current, null])}
              >+ Agregar copropietario</button>
            </section>
          )}

          <section className="form-section">
            <SeccionHeader icono={<FileText size={16} />} titulo="Datos de la afectación" />
            <div style={gridDos}>
              <Campo label="Superficie afectada (ha)">
                <input
                  type="number"
                  min="0"
                  step="0.0001"
                  value={afectacion.superficie_afectada_ha}
                  onChange={(event) => updateAfectacion('superficie_afectada_ha', event.target.value)}
                  style={inputStyle}
                />
              </Campo>
            </div>
            <Campo label="Situación jurídica">
              <textarea
                rows={3}
                value={afectacion.situacion_juridica}
                onChange={(event) => updateAfectacion('situacion_juridica', event.target.value)}
                style={inputStyle}
              />
            </Campo>
            <AfectacionGeometryField
              value={afectacion.geometria_wkt}
              onChange={(value) => updateAfectacion('geometria_wkt', value)}
            />
            <label className="check-row">
              <input
                type="checkbox"
                checked={afectacion.documentacion_disponible}
                onChange={(event) => updateAfectacion('documentacion_disponible', event.target.checked)}
              />
              Documentación de la afectación disponible
            </label>
            {!afectacion.documentacion_disponible && (
              <Campo label="Documentación faltante">
                <textarea
                  rows={2}
                  value={afectacion.documentacion_faltante}
                  onChange={(event) => updateAfectacion('documentacion_faltante', event.target.value)}
                  style={inputStyle}
                />
              </Campo>
            )}
          </section>

          <div className="form-actions">
            <p>La afectación solo se crea después de confirmar persona y parcela.</p>
            <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="button warning" disabled={guardando}>
              {guardando && <Loader2 size={16} className="spin" />}
              {guardando ? 'Guardando…' : 'Guardar afectación'}
            </button>
          </div>
        </form>
      )}
    </ModalWrapper>
  );
}

function ParcelaFields({ value, onChange }) {
  return (
    <section className="form-section">
      <SeccionHeader icono={<MapPinned size={16} />} titulo="Nueva parcela" />
      <div style={gridDos}>
        <Campo label="Tipo de parcela">
          <select
            value={value.tipo_parcela}
            onChange={(event) => onChange('tipo_parcela', event.target.value)}
            style={inputStyle}
          >
            <option value="individual">Individual</option>
            <option value="copropiedad">Copropiedad</option>
          </select>
        </Campo>
        <Campo label="No. parcela PPT">
          <input
            value={value.no_parcela_ppt}
            onChange={(event) => onChange('no_parcela_ppt', event.target.value)}
            style={inputStyle}
          />
        </Campo>
        <Campo label="Certificado parcelario">
          <input
            value={value.certificado_parcelario}
            onChange={(event) => onChange('certificado_parcelario', event.target.value)}
            style={inputStyle}
          />
        </Campo>
        <Campo label="Folio de derechos">
          <input
            value={value.folio_derechos}
            onChange={(event) => onChange('folio_derechos', event.target.value)}
            style={inputStyle}
          />
        </Campo>
        <Campo label="Constancia de vigencia">
          <input
            type="date"
            value={value.constancia_vigencia_fecha}
            onChange={(event) => onChange('constancia_vigencia_fecha', event.target.value)}
            style={inputStyle}
          />
        </Campo>
      </div>
      <label className="check-row">
        <input
          type="checkbox"
          checked={value.documentacion_disponible}
          onChange={(event) => onChange('documentacion_disponible', event.target.checked)}
        />
        Documentación de la parcela disponible
      </label>
      {!value.documentacion_disponible && (
        <Campo label="Documentación faltante">
          <textarea
            rows={2}
            value={value.documentacion_faltante}
            onChange={(event) => onChange('documentacion_faltante', event.target.value)}
            style={inputStyle}
          />
        </Campo>
      )}
    </section>
  );
}
