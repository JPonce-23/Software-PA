import React, { useId, useState } from 'react';
import { inputStyle } from './formStyles';
import { normalizePolygonWkt } from '../utils/geometry';

export default function AfectacionGeometryField({ value, onChange }) {
  const fieldId = useId();
  const [validationError, setValidationError] = useState('');

  const validate = () => {
    try {
      normalizePolygonWkt(value);
      setValidationError('');
    } catch (error) {
      setValidationError(error.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label htmlFor={fieldId} style={{ fontSize: '13px', color: '#475569', fontWeight: '500' }}>
        Geometría confirmada (WKT) *
      </label>
      <textarea
        id={fieldId}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          if (validationError) setValidationError('');
        }}
        onBlur={validate}
        placeholder="MULTIPOLYGON(((-90.1 20.1, -90.0 20.1, -90.0 20.0, -90.1 20.1)))"
        rows={4}
        required
        spellCheck={false}
        aria-invalid={Boolean(validationError)}
        aria-describedby={`${fieldId}-hint${validationError ? ` ${fieldId}-error` : ''}`}
        style={{
          ...inputStyle,
          resize: 'vertical',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          borderColor: validationError ? '#dc2626' : '#e2e8f0',
        }}
      />
      <p id={`${fieldId}-hint`} style={{ margin: 0, color: '#64748b', fontSize: '12px' }}>
        Capture el polígono confirmado después del caminamiento y análisis territorial.
        Se aceptan geometrías POLYGON o MULTIPOLYGON en coordenadas WGS84.
      </p>
      {validationError && (
        <p
          id={`${fieldId}-error`}
          role="alert"
          style={{ margin: 0, color: '#dc2626', fontSize: '12px' }}
        >
          {validationError}
        </p>
      )}
    </div>
  );
}
