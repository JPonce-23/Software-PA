import React from 'react';
import { Upload } from 'lucide-react';
import { useNavigate } from 'react-router-dom';


export default function NucleosImportPanel() {
  const navigate = useNavigate();
  return (
    <button
      className="map-import-button"
      type="button"
      onClick={() => navigate('/administracion/importaciones-geoespaciales')}
      title="Importar núcleos agrarios"
    >
      <Upload size={18} />
      Importar núcleos
    </button>
  );
}
