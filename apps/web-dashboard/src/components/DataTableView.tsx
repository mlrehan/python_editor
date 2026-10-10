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

interface CellData {
  text: string;
  html: string;
  isIndex: boolean;
  inlineStyle?: React.CSSProperties;
}

interface ColumnMeta {
  header: string;
  type: 'number' | 'string' | 'date' | 'boolean';
  isIndex: boolean;
}

interface DataTableViewProps {
  html: string;
  title?: string;
}

// Convert CSS style string from raw HTML to React inline CSSProperties
function parseInlineStyle(styleStr: string): React.CSSProperties {
  if (!styleStr) return {};
  const styleObj: Record<string, string> = {};
  styleStr.split(';').forEach((declaration) => {
    const [property, value] = declaration.split(':');
    if (property && value) {
      const camelProp = property.trim().replace(/-([a-z])/g, (_, char) => char.toUpperCase());
      styleObj[camelProp] = value.trim();
    }
  });
  return styleObj as React.CSSProperties;
}

// Detect missing/NaN values
function isMissingValue(val: string): boolean {
  const normalized = val.trim().toLowerCase();
  return (
    normalized === 'nan' ||
    normalized === 'none' ||
    normalized === 'null' ||
    normalized === '<na>' ||
    normalized === 'nat' ||
    normalized === 'undefined'
  );
}

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

  // Parse HTML table using standard DOMParser
  const parsedData = useMemo(() => {
    try {
      if (typeof window === 'undefined') return null;
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const table = doc.querySelector('table');
      if (!table) return null;

      // 1. Extract Headers
      const headerRows = Array.from(table.querySelectorAll('thead tr'));
      let rawHeaders: Array<{ text: string; isIndex: boolean }> = [];

      if (headerRows.length > 0) {
        // Use last header row for multi-level headers or standard single row
        const lastHeaderRow = headerRows[headerRows.length - 1];
        const thElements = Array.from(lastHeaderRow.querySelectorAll('th, td'));
        rawHeaders = thElements.map((th, idx) => ({
          text: th.textContent?.trim() || (idx === 0 ? '' : `Col_${idx}`),
          isIndex: th.tagName.toLowerCase() === 'th' && idx === 0 && !th.textContent?.trim(),
        }));
      }

      // 2. Extract Data Rows
      const bodyRows = Array.from(table.querySelectorAll('tbody tr'));
      // Fallback: if no <tbody>, collect all <tr> excluding first row
      const candidateRows = bodyRows.length > 0 ? bodyRows : Array.from(table.querySelectorAll('tr')).slice(1);

      const rows: CellData[][] = [];
      for (const tr of candidateRows) {
        const cells = Array.from(tr.querySelectorAll('th, td'));
        if (cells.length === 0) continue;

        const rowData: CellData[] = cells.map((cell, idx) => {
          const rawText = cell.textContent?.trim() || '';
          const isIndexCell = cell.tagName.toLowerCase() === 'th' || (rawHeaders[idx]?.isIndex ?? false);
          const styleAttr = cell.getAttribute('style') || '';
          const inlineStyle = styleAttr ? parseInlineStyle(styleAttr) : undefined;
          return {
            text: rawText,
            html: cell.innerHTML,
            isIndex: isIndexCell,
            inlineStyle,
          };
        });
        rows.push(rowData);
      }

      if (rows.length === 0 && rawHeaders.length === 0) {
        return null;
      }

      // If no thead was present, construct default headers from column count
      const colCount = Math.max(rawHeaders.length, rows[0]?.length || 0);
      if (rawHeaders.length === 0 && colCount > 0) {
        rawHeaders = Array.from({ length: colCount }, (_, i) => ({
          text: `Col_${i}`,
          isIndex: false,
        }));
      }

      // Pad headers if rows have more columns
      while (rawHeaders.length < colCount) {
        rawHeaders.push({ text: `Col_${rawHeaders.length}`, isIndex: false });
      }

      // 3. Infer Column Types
      const columns: ColumnMeta[] = rawHeaders.map((hdr, colIdx) => {
        let numericCount = 0;
        let dateCount = 0;
        let boolCount = 0;
        let sampleCount = 0;

        for (let r = 0; r < Math.min(rows.length, 50); r++) {
          const cell = rows[r][colIdx];
          if (!cell || isMissingValue(cell.text) || !cell.text) continue;
          sampleCount++;

          const cleanNum = cell.text.replace(/[\$,%]/g, '').trim();
          if (!isNaN(Number(cleanNum)) && cleanNum !== '') {
            numericCount++;
          } else if (cell.text.toLowerCase() === 'true' || cell.text.toLowerCase() === 'false') {
            boolCount++;
          } else if (!isNaN(Date.parse(cell.text)) && cell.text.length > 4 && /\d/.test(cell.text)) {
            dateCount++;
          }
        }

        let inferredType: ColumnMeta['type'] = 'string';
        if (sampleCount > 0) {
          if (numericCount / sampleCount >= 0.8) inferredType = 'number';
          else if (boolCount / sampleCount >= 0.8) inferredType = 'boolean';
          else if (dateCount / sampleCount >= 0.8) inferredType = 'date';
        }

        return {
          header: hdr.text,
          type: inferredType,
          isIndex: hdr.isIndex || (colIdx === 0 && rows.length > 0 && rows[0][0]?.isIndex),
        };
      });

      return { columns, rows };
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
    const headers = columns.map((c) => c.header || '').join('\t');
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
    const headers = columns.map((c) => escapeCSVField(c.header || '')).join(',');
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

  // Fallback to stylized standard HTML if structure cannot be parsed as a tabular dataset
  if (!parsedData || parsedData.columns.length === 0 || parsedData.rows.length === 0) {
    return (
      <div
        className="dataframe-fallback-wrapper"
        style={{
          margin: '8px 0',
          padding: '10px 12px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-main)',
          borderRadius: '6px',
          overflowX: 'auto',
          fontSize: '13px',
          color: 'var(--text-main)',
        }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }

  const { columns, rows } = parsedData;
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
                  <strong>{rows.length}</strong> rows × <strong>{columns.length}</strong> cols
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
            <tr>
              {columns.map((col, colIdx) => {
                const isSorted = sortConfig?.colIndex === colIdx;
                const sortDir = isSorted ? sortConfig.direction : null;
                const isNumeric = col.type === 'number';

                return (
                  <th
                    key={colIdx}
                    onClick={() => handleSort(colIdx)}
                    style={{
                      position: 'sticky',
                      top: 0,
                      zIndex: 3,
                      backgroundColor: 'var(--bg-cell-header)',
                      borderBottom: '2px solid var(--border-secondary)',
                      borderRight: '1px solid var(--border-main)',
                      padding: '8px 12px',
                      fontWeight: 600,
                      fontSize: '12px',
                      color: isSorted ? 'var(--border-accent)' : 'var(--text-main)',
                      textAlign: isNumeric ? 'right' : 'left',
                      cursor: 'pointer',
                      userSelect: 'none',
                      whiteSpace: 'nowrap',
                      transition: 'background-color 0.1s ease',
                    }}
                    title={`Click to sort by ${col.header || 'Index'}`}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: isNumeric ? 'flex-end' : 'flex-start',
                        gap: '6px',
                      }}
                    >
                      {/* Column Type Icon */}
                      <span style={{ opacity: 0.5 }}>
                        {col.type === 'number' && <Hash size={11} />}
                        {col.type === 'string' && <Type size={11} />}
                        {col.type === 'date' && <Calendar size={11} />}
                        {col.type === 'boolean' && <ToggleLeft size={11} />}
                      </span>

                      {/* Header Title */}
                      <span>{col.header || (col.isIndex ? '' : `Col_${colIdx}`)}</span>

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
                            ...cell.inlineStyle,
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

