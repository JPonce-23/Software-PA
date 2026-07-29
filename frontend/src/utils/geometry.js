import { parse } from 'wellknown';

const POLYGON_TYPES = new Set(['Polygon', 'MultiPolygon']);

export function normalizePolygonWkt(value) {
  const normalized = value?.trim();
  if (!normalized) {
    throw new Error('Captura la geometría confirmada de la afectación.');
  }

  let geometry;
  try {
    geometry = parse(normalized);
  } catch {
    throw new Error('La geometría no tiene un formato WKT válido.');
  }

  if (!geometry || !POLYGON_TYPES.has(geometry.type)) {
    throw new Error('La geometría debe ser un POLYGON o MULTIPOLYGON.');
  }

  return normalized;
}
