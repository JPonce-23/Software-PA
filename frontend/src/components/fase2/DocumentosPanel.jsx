import React, { useCallback, useEffect, useState } from 'react';
import { Download, FileClock, FileUp, Loader2, Plus } from 'lucide-react';
import api from '../../api/axios';
import {
  Campo,
  ErrorBanner,
  ModalWrapper,
} from '../FormUI';
import { gridDos, inputStyle } from '../formStyles';

export default function DocumentosPanel({ idTramoNucleo, canWrite }) {
  const [documents, setDocuments] = useState([]);
  const [versions, setVersions] = useState({});
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/documentacion', {
        params: {
          entidad_tipo: 'tramo_nucleo',
          entidad_id: idTramoNucleo,
        },
      });
      setDocuments(data);
      const responses = await Promise.all(
        data.map((document) => api.get(`/documentacion/${document.id_documento}/versiones`)),
      );
      setVersions(Object.fromEntries(
        data.map((document, index) => [document.id_documento, responses[index].data]),
      ));
    } finally {
      setLoading(false);
    }
  }, [idTramoNucleo]);

  useEffect(() => { load(); }, [load]);

  const download = async (document, version) => {
    const response = await api.get(
      `/documentacion/${document.id_documento}/versiones/${version.numero_version}/archivo`,
      { responseType: 'blob' },
    );
    const url = URL.createObjectURL(response.data);
    const anchor = window.document.createElement('a');
    anchor.href = url;
    anchor.download = version.nombre_archivo_original;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="panel-loading"><Loader2 className="spin" /> Cargando documentos…</div>;

  return (
    <div className="phase-panel">
      <header className="phase-panel-header">
        <div>
          <h3>Documentación y versiones</h3>
          <p>Cada carga conserva hash SHA-256, tamaño y versión.</p>
        </div>
        {canWrite && (
          <button type="button" className="button" onClick={() => setModal({ type: 'document' })}>
            <Plus size={16} /> Nuevo documento
          </button>
        )}
      </header>

      {documents.length === 0 ? (
        <div className="empty-state"><FileClock size={30} /> No hay documentos del expediente.</div>
      ) : (
        <div className="record-list">
          {documents.map((document) => (
            <article className="record-card" key={document.id_documento}>
              <header>
                <div>
                  <strong>{document.tipo_documento}</strong>
                  <span>{document.categoria} {document.es_critico ? '· Crítico' : ''}</span>
                </div>
                {canWrite && (
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => setModal({ type: 'upload', document })}
                  >
                    <FileUp size={15} /> Subir versión
                  </button>
                )}
              </header>
              <div className="version-list">
                {(versions[document.id_documento] || []).map((version) => (
                  <div key={version.id_documento_version}>
                    <span className="version-number">v{version.numero_version}</span>
                    <div>
                      <strong>{version.nombre_archivo_original}</strong>
                      <small>
                        {(version.tamano_bytes / 1024).toFixed(1)} KB ·{' '}
                        {new Date(version.fecha_carga).toLocaleString('es-MX')}
                      </small>
                      <code title={version.hash_sha256}>{version.hash_sha256.slice(0, 16)}…</code>
                    </div>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Descargar ${version.nombre_archivo_original}`}
                      onClick={() => download(document, version)}
                    >
                      <Download size={16} />
                    </button>
                  </div>
                ))}
                {(versions[document.id_documento] || []).length === 0 && (
                  <p className="field-hint">Aún no se ha cargado ningún archivo.</p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {modal?.type === 'document' && (
        <DocumentForm
          idTramoNucleo={idTramoNucleo}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
        />
      )}
      {modal?.type === 'upload' && (
        <UploadForm
          document={modal.document}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
        />
      )}
    </div>
  );
}

function DocumentForm({ idTramoNucleo, onClose, onSaved }) {
  const [form, setForm] = useState({
    tipo_documento: '',
    categoria: 'disponible',
    es_critico: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.post('/documentacion', {
        entidad_relacionada_id: idTramoNucleo,
        entidad_relacionada_tipo: 'tramo_nucleo',
        ...form,
      });
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible crear el documento.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo="Nuevo documento" color="#0f766e" onClose={onClose}>
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <Campo label="Tipo de documento *">
          <input
            required
            value={form.tipo_documento}
            onChange={(event) => setForm({ ...form, tipo_documento: event.target.value })}
            style={inputStyle}
          />
        </Campo>
        <div style={gridDos}>
          <Campo label="Categoría">
            <select
              value={form.categoria}
              onChange={(event) => setForm({ ...form, categoria: event.target.value })}
              style={inputStyle}
            >
              <option value="disponible">Disponible</option>
              <option value="faltante">Faltante</option>
            </select>
          </Campo>
          <label className="check-row">
            <input
              type="checkbox"
              checked={form.es_critico}
              onChange={(event) => setForm({ ...form, es_critico: event.target.checked })}
            />
            Documento crítico
          </label>
        </div>
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving}>
            {saving && <Loader2 size={16} className="spin" />} Crear
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

function UploadForm({ document, onClose, onSaved }) {
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event.preventDefault();
    if (!file) return;
    setSaving(true);
    setError(null);
    try {
      const body = new FormData();
      body.append('file', file);
      await api.post(`/documentacion/${document.id_documento}/archivo`, body);
      onSaved();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar el archivo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalWrapper titulo="Subir nueva versión" subtitulo={document.tipo_documento} color="#0f766e" onClose={onClose}>
      <form className="form-stack" onSubmit={submit}>
        <ErrorBanner mensaje={error} />
        <Campo label="Archivo *">
          <input
            required
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.docx"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            style={inputStyle}
          />
        </Campo>
        <p className="field-hint">Formatos: PDF, JPG, PNG o DOCX. Tamaño máximo configurado por el servidor.</p>
        <div className="form-actions">
          <span />
          <button type="button" className="button secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" className="button" disabled={saving || !file}>
            {saving && <Loader2 size={16} className="spin" />} Subir versión
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}
