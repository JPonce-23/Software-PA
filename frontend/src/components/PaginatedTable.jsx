import React, { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import './PaginatedTable.css';

export default function PaginatedTable({
  columns,
  data,
  loading,
  emptyMessage = "No hay registros disponibles.",
  keyField,
  rowClassName,
  total,
  page: remotePage,
  pageSize: remotePageSize,
  onPageChange,
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const remote = typeof onPageChange === 'function' && Number.isFinite(total);

  // Reset page when data changes (e.g., after filtering)
  React.useEffect(() => {
    setPage(1);
  }, [data]);

  const effectivePageSize = remote ? remotePageSize : pageSize;
  const itemTotal = remote ? total : data.length;
  const totalPages = Math.ceil(itemTotal / effectivePageSize) || 1;
  const safePage = remote ? Math.min(remotePage, totalPages) : Math.min(page, totalPages);
  
  const paginatedData = useMemo(() => {
    if (remote) return data;
    const start = (safePage - 1) * effectivePageSize;
    return data.slice(start, start + effectivePageSize);
  }, [data, effectivePageSize, remote, safePage]);

  const changePage = (nextPage) => {
    const bounded = Math.max(1, Math.min(totalPages, nextPage));
    if (remote) onPageChange(bounded);
    else setPage(bounded);
  };

  return (
    <div className="admin-table-container">
      <div className="admin-table-wrap">
        {loading ? (
          <p className="admin-empty">Cargando registros...</p>
        ) : data.length === 0 ? (
          <p className="admin-empty">{emptyMessage}</p>
        ) : (
          <table className="admin-table sticky-header">
            <thead>
              <tr>
                {columns.map((col, idx) => (
                  <th key={`col-${idx}`} className={col.className || ''}>
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((item) => (
                <tr key={item[keyField]} className={rowClassName ? rowClassName(item) : ''}>
                  {columns.map((col, idx) => (
                    <td key={`cell-${item[keyField]}-${idx}`} data-label={col.label || col.header} className={col.className || ''}>
                      {col.render(item)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      
      {data.length > 0 && !loading && (
        <div className="admin-pagination">
          <div className="admin-pagination-info">
            Mostrando {((safePage - 1) * effectivePageSize) + 1} - {Math.min(safePage * effectivePageSize, itemTotal)} de {itemTotal}
          </div>
          <div className="admin-pagination-controls">
            {!remote && <label>
              Filas por página:
              <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>}
            <button 
              type="button" 
              className="admin-icon-button" 
              disabled={safePage === 1} 
              onClick={() => changePage(safePage - 1)}
              title="Página anterior"
            >
              <ChevronLeft size={16} />
            </button>
            <span>Página {safePage} de {totalPages}</span>
            <button 
              type="button" 
              className="admin-icon-button" 
              disabled={safePage === totalPages} 
              onClick={() => changePage(safePage + 1)}
              title="Página siguiente"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
