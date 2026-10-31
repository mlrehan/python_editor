import React, { useState, useMemo, useCallback } from 'react';
import {
  Table as TableIcon,
  Search,
  X,
  Copy,
  Check,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
} from 'lucide-react';
import { parseDataFrameHtml, isMissingValue } from '../utils/dataframeHtml';
import { OutputFrame } from './OutputFrame';

interface DataTableViewProps {
  html: string;
  title?: string;
}

// Height of one header row (MultiIndex levels stack as sticky rows)
const HEADER_ROW_HEIGHT = 33;

// RFC 4180 CSV escaping
function escapeCSVField(val: string): string {
  if (val.includes(',') || val.includes('"') || val.includes('\n') || val.includes('\r')) {
    return `"${val.replace(/"/g, '""')}"`;
  }
  return val;
}

export const DataTableView: React.FC<DataTableViewProps> = ({ html }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState<{ colIndex: number; direction: 'asc' | 'desc' } | null>(null);
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [copied, setCopied] = useState(false);

  // Parse the pandas HTML (column names, index names, MultiIndex levels, real shape)
  const parsedData = useMemo(() => {
    try {
      return parseDataFrameHtml(html);
    } catch {
      return null;
    }
  }, [html]);

  // Handle Search Filtering
  const filteredRows = useMemo(() => {
    if (!parsedData) return [];
    const { rows } = parsedData;
    if (!searchTerm.trim()) return rows;

    const term = searchTerm.toLowerCase();
    return rows.filter((row) =>
      row.some((cell) => cell.text.toLowerCase().includes(term))
    );
  }, [parsedData, searchTerm]);

  // Handle Column Sorting
  const sortedRows = useMemo(() => {
    if (!sortConfig || !parsedData) return filteredRows;
    const { colIndex, direction } = sortConfig;
    const colMeta = parsedData.columns[colIndex];
    const isNum = colMeta?.type === 'number';

    return [...filteredRows].sort((rowA, rowB) => {
      const valA = rowA[colIndex]?.text || '';
      const valB = rowB[colIndex]?.text || '';

      // Keep missing values sorted to bottom
      const isMissingA = isMissingValue(valA) || !valA;
      const isMissingB = isMissingValue(valB) || !valB;
      if (isMissingA && !isMissingB) return 1;
      if (!isMissingA && isMissingB) return -1;
      if (isMissingA && isMissingB) return 0;

      if (isNum) {
        const numA = parseFloat(valA.replace(/[\$,%]/g, '')) || 0;
        const numB = parseFloat(valB.replace(/[\$,%]/g, '')) || 0;
        return direction === 'asc' ? numA - numB : numB - numA;
      }

      const cmp = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' });
      return direction === 'asc' ? cmp : -cmp;
    });
  }, [filteredRows, sortConfig, parsedData]);

  // Handle Pagination
  const totalPages = pageSize === 0 ? 1 : Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const paginatedRows = useMemo(() => {
    if (pageSize === 0) return sortedRows;
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, currentPage, pageSize]);

  // Sort Toggle Handler
  const handleSort = (colIdx: number) => {
    setSortConfig((prev) => {
      if (!prev || prev.colIndex !== colIdx) {
        return { colIndex: colIdx, direction: 'asc' };
      }
      if (prev.direction === 'asc') {
        return { colIndex: colIdx, direction: 'desc' };
      }
      return null;
    });
  };

  // Copy to Clipboard (TSV format for direct Excel/Sheets paste)
  const handleCopyClipboard = useCallback(() => {
    if (!parsedData) return;
    const { columns } = parsedData;
    const headers = columns.map((c) => c.fullLabel).join('\t');
    const rowsText = sortedRows
      .map((row) => row.map((cell) => cell.text).join('\t'))
      .join('\n');
    const fullText = `${headers}\n${rowsText}`;

    navigator.clipboard.writeText(fullText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [parsedData, sortedRows]);

  // Export CSV File
  const handleExportCSV = useCallback(() => {
    if (!parsedData) return;
    const { columns } = parsedData;
    const headers = columns.map((c) => escapeCSVField(c.fullLabel)).join(',');
    const rowsText = sortedRows
      .map((row) => row.map((cell) => escapeCSVField(cell.text)).join(','))
      .join('\r\n');
    const csvContent = `${headers}\r\n${rowsText}`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `dataframe_${Date.now().toString().slice(-6)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [parsedData, sortedRows]);

  // Not a recognisable table: render the HTML as-is, isolated in the sandboxed output frame
  if (!parsedData || parsedData.columns.length === 0 || parsedData.rows.length === 0) {
    return <OutputFrame mime="text/html" data={html} />;
  }

  const { columns, rows, headerBands, indexCount, hasIndexNames, shape } = parsedData;
  const dataColumnCount = columns.length - indexCount;
  const isFiltered = searchTerm.trim().length > 0;

  return (
    <div
      data-testid="interactive-data-table"
      style={{
        margin: '10px 0',
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-main)',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 1. Header Toolbar */}
      <div
        style={{
          padding: '8px 12px',
          backgroundColor: 'var(--bg-cell-header)',
          borderBottom: '1px solid var(--border-main)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
        }}
      >
        {/* Dataset Summary Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              backgroundColor: 'var(--bg-hover)',
              borderRadius: '5px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--text-main)',
            }}
          >
            <TableIcon size={14} style={{ color: 'var(--border-accent)' }} />
            <span>
              {isFiltered ? (
                <>
                  <strong style={{ color: 'var(--border-accent)' }}>{filteredRows.length}</strong> of {rows.length} rows
                </>
              ) : (
                <>
                  <strong>{(shape?.rows ?? rows.length).toLocaleString()}</strong> rows ×{' '}
                  <strong>{(shape?.columns ?? dataColumnCount).toLocaleString()}</strong> columns
                  {shape && shape.rows > rows.length && (
                    <span style={{ color: 'var(--text-muted)' }}> (showing {rows.length})</span>
                  )}
                </>
              )}
            </span>
          </div>
        </div>

        {/* Search, Page Size, Copy & CSV Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Quick Search Input */}
          <div
            style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Search
              size={13}
              style={{
                position: 'absolute',
                left: '8px',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              placeholder="Filter table..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                height: '28px',
                width: '140px',
                paddingLeft: '26px',
                paddingRight: searchTerm ? '24px' : '8px',
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-secondary)',
                borderRadius: '5px',
                fontSize: '12px',
                color: 'var(--text-main)',
                outline: 'none',
              }}
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                style={{
                  position: 'absolute',
                  right: '6px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: 0,
                }}
                title="Clear filter"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Rows per page selector */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            style={{
              height: '28px',
              padding: '0 6px',
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-secondary)',
              borderRadius: '5px',
              fontSize: '12px',
              color: 'var(--text-main)',
              cursor: 'pointer',
              outline: 'none',
            }}
            title="Rows per page"
          >
            <option value={10}>10 rows</option>
            <option value={25}>25 rows</option>
            <option value={50}>50 rows</option>
            <option value={100}>100 rows</option>
            <option value={0}>All rows</option>
          </select>

          {/* Copy TSV button */}
          <button
            onClick={handleCopyClipboard}
            style={{
              height: '28px',
              padding: '0 8px',
              backgroundColor: copied ? 'var(--dropdown-item-selected)' : 'var(--btn-secondary-bg)',
              border: '1px solid var(--btn-secondary-border)',
              borderRadius: '5px',
              fontSize: '12px',
              fontWeight: 500,
              color: copied ? 'var(--dropdown-item-selected-text)' : 'var(--btn-secondary-text)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease',
            }}
            title="Copy table to clipboard"
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Export CSV button */}
          <button
            onClick={handleExportCSV}
            style={{
              height: '28px',
              padding: '0 8px',
              backgroundColor: 'var(--btn-secondary-bg)',
              border: '1px solid var(--btn-secondary-border)',
              borderRadius: '5px',
              fontSize: '12px',
              fontWeight: 500,
              color: 'var(--btn-secondary-text)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Download CSV"
          >
            <Download size={13} />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* 2. Interactive Scrollable Table */}
      <div
        style={{
          maxHeight: '420px',
          overflowX: 'auto',
          overflowY: 'auto',
          position: 'relative',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: 0,
            fontSize: '12.5px',
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            textAlign: 'left',
          }}
        >
          {/* Table Header with Sorting */}
          <thead>
            {headerBands.map((band, bandIdx) => (
              <tr key={`band-${bandIdx}`} data-testid="dataframe-header-band">
                {band.map((cell, cellIdx) => (
                  <th
                    key={cellIdx}
                    colSpan={cell.span}
                    style={{
                      position: 'sticky',
                      top: `${bandIdx * HEADER_ROW_HEIGHT}px`,
                      zIndex: 3,
                      height: `${HEADER_ROW_HEIGHT}px`,
                      boxSizing: 'border-box',
                      backgroundColor: 'var(--bg-cell-header)',
                      borderBottom: '1px solid var(--border-main)',
                      borderRight: '1px solid var(--border-main)',
                      padding: '0 12px',
                      fontWeight: 600,
                      fontSize: '12px',
                      color: cell.isIndex ? 'var(--text-muted)' : 'var(--text-main)',
                      textAlign: 'center',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {cell.text}
                  </th>
                ))}
              </tr>
            ))}
            <tr>
              {columns.map((col, colIdx) => {
                const isSorted = sortConfig?.colIndex === colIdx;
                const sortDir = isSorted ? sortConfig.direction : null;
                const isNumeric = col.type === 'number';

                return (
                  <th
                    key={colIdx}
                    onClick={() => handleSort(colIdx)}
                    data-testid="dataframe-column-header"
                    scope="col"
                    className={col.isIndex ? `df-index-corner${colIdx === indexCount - 1 ? ' df-index-last' : ''}` : undefined}
                    style={{
                      position: 'sticky',
                      top: `${headerBands.length * HEADER_ROW_HEIGHT}px`,
                      left: col.isIndex && colIdx === 0 ? 0 : undefined,
                      zIndex: col.isIndex && colIdx === 0 ? 5 : 3,
                      height: `${HEADER_ROW_HEIGHT}px`,
                      boxSizing: 'border-box',
                      backgroundColor: 'var(--bg-cell-header)',
                      borderBottom: hasIndexNames ? '1px solid var(--border-main)' : '2px solid var(--border-secondary)',
                      borderRight: '1px solid var(--border-main)',
                      padding: '0 12px',
                      fontWeight: 600,
                      fontSize: '12px',
                      color: isSorted ? 'var(--border-accent)' : 'var(--text-main)',
                      textAlign: isNumeric ? 'right' : 'left',
                      cursor: 'pointer',
                      userSelect: 'none',
                      whiteSpace: 'nowrap',
                      transition: 'background-color 0.1s ease',
                    }}
                    title={col.isIndex ? `Sort by index${col.indexName ? ` (${col.indexName})` : ''}${col.label ? ` · columns: ${col.label}` : ''}` : `Click to sort by ${col.fullLabel || 'this column'}`}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: isNumeric ? 'flex-end' : 'flex-start',
                        gap: '6px',
                      }}
                    >
                      {/* Column Type Icon (data columns) */}
                      <span style={{ opacity: 0.5, display: col.isIndex ? 'none' : undefined }}>
                        {col.type === 'number' && <Hash size={11} />}
                        {col.type === 'string' && <Type size={11} />}
                        {col.type === 'date' && <Calendar size={11} />}
                        {col.type === 'boolean' && <ToggleLeft size={11} />}
                      </span>

                      {/* Header Title */}
                      <span>{col.label}</span>

                      {/* Sort Indicator */}
                      <span style={{ display: 'inline-flex', opacity: isSorted ? 1 : 0.35 }}>
                        {sortDir === 'asc' && <ArrowUp size={12} style={{ color: 'var(--border-accent)' }} />}
                        {sortDir === 'desc' && <ArrowDown size={12} style={{ color: 'var(--border-accent)' }} />}
                        {!sortDir && <ArrowUpDown size={11} />}
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
            {/* Index names (df.index.name / names) on their own row, as Jupyter and Colab show them */}
            {hasIndexNames && (
              <tr data-testid="dataframe-index-names">
                {columns.map((col, colIdx) => (
                  <th
                    key={colIdx}
                    scope={col.isIndex ? 'col' : undefined}
                    className={col.isIndex ? `df-index-name${colIdx === indexCount - 1 ? ' df-index-last' : ''}` : 'df-index-name-filler'}
                    style={{
                      position: 'sticky',
                      top: `${(headerBands.length + 1) * HEADER_ROW_HEIGHT}px`,
                      left: col.isIndex && colIdx === 0 ? 0 : undefined,
                      zIndex: col.isIndex && colIdx === 0 ? 5 : 3,
                      height: `${HEADER_ROW_HEIGHT}px`,
                      boxSizing: 'border-box',
                      padding: '0 12px',
                      borderBottom: '2px solid var(--border-secondary)',
                      borderRight: '1px solid var(--border-main)',
                      textAlign: 'left',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {col.isIndex ? col.indexName : ''}
                  </th>
                ))}
              </tr>
            )}
          </thead>

          {/* Table Body */}
          <tbody>
            {paginatedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{
                    padding: '32px 16px',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                  }}
                >
                  No matching records found
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, rIdx) => {
                const isEven = rIdx % 2 === 0;
                return (
                  <tr
                    key={rIdx}
                    style={{
                      backgroundColor: isEven ? 'transparent' : 'var(--bg-hover)',
                      transition: 'background-color 0.1s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = isEven ? 'transparent' : 'var(--bg-hover)';
                    }}
                  >
                    {row.map((cell, cIdx) => {
                      const colMeta = columns[cIdx];
                      const isNumeric = colMeta?.type === 'number';
                      const isMissing = isMissingValue(cell.text);

                      if (colMeta?.isIndex) {
                        return (
                          <th
                            key={cIdx}
                            scope="row"
                            data-testid="dataframe-index-cell"
                            className={`df-index-cell${cIdx === indexCount - 1 ? ' df-index-last' : ''}`}
                            style={{
                              position: cIdx === 0 ? 'sticky' : undefined,
                              left: cIdx === 0 ? 0 : undefined,
                              zIndex: cIdx === 0 ? 2 : undefined,
                              textAlign: isNumeric ? 'right' : 'left',
                            }}
                          >
                            {cell.text}
                          </th>
                        );
                      }

                      return (
                        <td
                          key={cIdx}
                          style={{
                            padding: '6px 12px',
                            borderBottom: '1px solid var(--border-main)',
                            borderRight: '1px solid var(--border-main)',
                            textAlign: isNumeric ? 'right' : 'left',
                            color: cell.isIndex ? 'var(--text-muted)' : 'var(--text-main)',
                            fontWeight: cell.isIndex ? 600 : 400,
                            fontFamily: isNumeric || cell.isIndex ? "'JetBrains Mono', monospace" : 'inherit',
                            fontSize: isNumeric || cell.isIndex ? '12px' : '12.5px',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {isMissing ? (
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '1px 5px',
                                borderRadius: '3px',
                                fontSize: '11px',
                                fontFamily: "'JetBrains Mono', monospace",
                                backgroundColor: 'var(--badge-bg)',
                                color: 'var(--text-muted)',
                                fontStyle: 'italic',
                                opacity: 0.7,
                              }}
                            >
                              {cell.text || 'NaN'}
                            </span>
                          ) : (
                            cell.text
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* 3. Pagination Footer */}
      {pageSize > 0 && totalPages > 1 && (
        <div
          style={{
            padding: '6px 12px',
            backgroundColor: 'var(--bg-cell-header)',
            borderTop: '1px solid var(--border-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          <div>
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({sortedRows.length} total entries)
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              style={{
                padding: '3px 6px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '4px',
                color: currentPage === 1 ? 'var(--text-muted)' : 'var(--btn-secondary-text)',
                cursor: currentPage === 1 ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              title="First Page"
            >
              <ChevronsLeft size={13} />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              style={{
                padding: '3px 6px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '4px',
                color: currentPage === 1 ? 'var(--text-muted)' : 'var(--btn-secondary-text)',
                cursor: currentPage === 1 ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Previous Page"
            >
              <ChevronLeft size={13} />
            </button>

            <span style={{ padding: '0 6px', fontWeight: 600, color: 'var(--text-main)' }}>
              {currentPage} / {totalPages}
            </span>

            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              style={{
                padding: '3px 6px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '4px',
                color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--btn-secondary-text)',
                cursor: currentPage === totalPages ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Next Page"
            >
              <ChevronRight size={13} />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              style={{
                padding: '3px 6px',
                backgroundColor: 'var(--btn-secondary-bg)',
                border: '1px solid var(--btn-secondary-border)',
                borderRadius: '4px',
                color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--btn-secondary-text)',
                cursor: currentPage === totalPages ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              title="Last Page"
            >
              <ChevronsRight size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

