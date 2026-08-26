import React from 'react';
import { Download, FileText, Upload } from 'lucide-react';
import api from '../api/axios';
import AuthContext from '../contexts/auth-context';
import { Empty, Field, Notice } from './TargetUI';
import { apiMessage } from '../utils/target';

export default function DocumentsPanel({ targetType, targetId }) {
  const { user } = React.useContext(AuthContext);
  const writable = ['admin', 'operador'].includes(user?.rol);
  const [documents, setDocuments] = React.useState([]);
  const [versions, setVersions] = React.useState({});
  const [error, setError] = React.useState('');
  const [form, setForm] = React.useState({ tipo_documento: 'soporte', estado: 'disponible', titulo: '' });
  const load = React.useCallback(async () => {
    try { setDocuments((await api.get(`/documentos/objetivos/${targetType}/${targetId}`)).data); setError(''); }
    catch (requestError) { setError(apiMessage(requestError)); }
  }, [targetId, targetType]);
  React.useEffect(() => { load(); }, [load]);
  const loadVersions = async (id) => {
    try {
      const response = await api.get(`/documentos/${id}/versiones`);
      setVersions((current) => ({ ...current, [id]: response.data }));
    }
    catch (requestError) { setError(apiMessage(requestError)); }
  };
  const create = async (event) => {
    event.preventDefault();
    try { await api.post(`/documentos/objetivos/${targetType}/${targetId}`, form); setForm({ tipo_documento: 'soporte', estado: 'disponible', titulo: '' }); await load(); }
    catch (requestError) { setError(apiMessage(requestError)); }
  };
  const upload = async (id, file) => {
    if (!file) return;
    const data = new FormData(); data.append('archivo', file);
    try { await api.post(`/documentos/${id}/versiones`, data); await loadVersions(id); }
    catch (requestError) { setError(apiMessage(requestError)); }
  };
  return <section className="subsection"><div className="section-heading"><div><h3>Documentos</h3><p>Metadatos y versiones inmutables con hash SHA-256.</p></div></div><Notice error={error} />
    {writable && <form className="inline-form" onSubmit={create}><Field label="Tipo"><input required value={form.tipo_documento} onChange={(e) => setForm({ ...form, tipo_documento: e.target.value })} /></Field><Field label="Título"><input value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} /></Field><button className="button" type="submit"><FileText />Registrar</button></form>}
    {documents.length === 0 ? <Empty title="Sin documentos">La captura puede continuar; el soporte se agrega cuando esté disponible.</Empty> : <div className="record-list">{documents.map((document) => <article className="record" key={document.id_documento}><div><strong>{document.titulo || document.tipo_documento}</strong><span>{document.estado} · {document.tipo_documento}</span></div><div className="record-actions"><button className="link-button" type="button" onClick={() => loadVersions(document.id_documento)}>Ver versiones</button>{writable && <label className="link-button upload-control"><Upload />Nueva versión<input type="file" onChange={(e) => upload(document.id_documento, e.target.files?.[0])} /></label>}</div>{versions[document.id_documento]?.map((version) => <a className="version" key={version.id_documento_version} href={`/api/documentos/versiones/${version.id_documento_version}/descarga`}><Download />v{version.numero_version} · {version.nombre_original}<small>{version.hash_sha256.slice(0, 12)}…</small></a>)}</article>)}</div>}
  </section>;
}
