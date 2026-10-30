/*
 * Parses the HTML that pandas produces for DataFrame._repr_html_ / to_html into a table model.
 *
 * pandas layouts this handles:
 *  - a named index (df.index.name / pivot tables): an extra header row holding the index name with
 *    empty cells under the data columns. Taking only the last header row turned every data column
 *    header into an empty cell (rendered as Col_1, Col_2, ...). Index names are now merged into the
 *    index column labels instead.
 *  - a named column axis (df.columns.name): its name sits in the index column of the header row.
 *  - MultiIndex columns: several header rows with colspan; each leaf column keeps its full path.
 *  - MultiIndex rows: index cells with rowspan; values are repeated into every row they span so
 *    sorting and filtering stay correct.
 *  - truncated frames: the "N rows × M columns" footer gives the real shape.
 */

export interface DataFrameCell {
  text: string;
  isIndex: boolean;
}

export interface DataFrameColumn {
  /** Leaf label shown in the sortable header row */
  label: string;
  /** Full label (all levels joined with " / "), used for copy / CSV export */
  fullLabel: string;
  isIndex: boolean;
  type: 'number' | 'string' | 'date' | 'boolean';
}

export interface HeaderBandCell {
  text: string;
  span: number;
  isIndex: boolean;
}

export interface ParsedDataFrame {
  columns: DataFrameColumn[];
  /** Upper column levels (MultiIndex columns), rendered above the sortable row; empty for flat columns */
  headerBands: HeaderBandCell[][];
  rows: DataFrameCell[][];
  indexCount: number;
  /** Shape reported by pandas (includes rows hidden by truncation), when present */
  shape: { rows: number; columns: number } | null;
}

interface GridCell {
  text: string;
  isTh: boolean;
  /** The source element: equal for all grid positions covered by one colspan/rowspan cell */
  source: Element;
}

export function isMissingValue(val: string): boolean {
  const normalized = val.trim().toLowerCase();
  return normalized === 'nan' || normalized === 'none' || normalized === 'null' || normalized === '<na>' || normalized === 'nat' || normalized === 'undefined';
}

/** Expands rows of <th>/<td> into a rectangular grid, resolving colspan and rowspan. */
function expandRows(trs: Element[]): GridCell[][] {
  const grid: GridCell[][] = [];
  trs.forEach((tr, r) => {
    grid[r] = grid[r] || [];
    let c = 0;
    for (const cell of Array.from(tr.children)) {
      const tag = cell.tagName.toLowerCase();
      if (tag !== 'th' && tag !== 'td') continue;
      while (grid[r][c]) c++; // skip positions filled by a rowspan from above
      const colspan = Math.max(1, parseInt(cell.getAttribute('colspan') || '1', 10) || 1);
      const rowspan = Math.max(1, parseInt(cell.getAttribute('rowspan') || '1', 10) || 1);
      const entry: GridCell = { text: (cell.textContent || '').trim(), isTh: tag === 'th', source: cell };
      for (let dr = 0; dr < rowspan && r + dr < trs.length; dr++) {
        grid[r + dr] = grid[r + dr] || [];
        for (let dc = 0; dc < colspan; dc++) grid[r + dr][c + dc] = entry;
      }
      c += colspan;
    }
  });
  return grid;
}

function inferType(values: string[]): DataFrameColumn['type'] {
  let sample = 0;
  let numeric = 0;
  let bool = 0;
  let date = 0;
  for (const v of values.slice(0, 50)) {
    if (!v || isMissingValue(v) || v === '...') continue;
    sample++;
    const num = v.replace(/[$,%]/g, '').trim();
    if (num !== '' && !isNaN(Number(num))) numeric++;
    else if (v.toLowerCase() === 'true' || v.toLowerCase() === 'false') bool++;
    else if (v.length > 4 && /\d/.test(v) && !isNaN(Date.parse(v))) date++;
  }
  if (!sample) return 'string';
  if (numeric / sample >= 0.8) return 'number';
  if (bool / sample >= 0.8) return 'boolean';
  if (date / sample >= 0.8) return 'date';
  return 'string';
}

export function parseDataFrameHtml(html: string): ParsedDataFrame | null {
  if (typeof DOMParser === 'undefined') return null;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const table = doc.querySelector('table');
  if (!table) return null;

  const theadRows = Array.from(table.querySelectorAll(':scope > thead > tr'));
  let bodyRows = Array.from(table.querySelectorAll(':scope > tbody > tr'));
  let headerTrs = theadRows;
  if (!theadRows.length) {
    // No <thead>: a leading row made only of <th> is the header
    const all = Array.from(table.querySelectorAll('tr'));
    const first = all[0];
    const firstIsHeader = !!first && Array.from(first.children).every((c) => c.tagName.toLowerCase() === 'th');
    headerTrs = firstIsHeader ? [first] : [];
    bodyRows = firstIsHeader ? all.slice(1) : all;
  }

  const header = expandRows(headerTrs);
  const body = expandRows(bodyRows).filter((row) => row.length > 0);
  if (!body.length && !header.length) return null;

  const colCount = Math.max(0, ...header.map((r) => r.length), ...body.map((r) => r.length));
  if (!colCount) return null;

  // Index columns: the leading <th> cells of the body rows (pandas writes the row index as <th>)
  let indexCount = 0;
  if (body.length) {
    while (indexCount < colCount && body[0][indexCount]?.isTh) indexCount++;
  }

  // The index-names row: text only under the index columns, empty under every data column
  let indexNames: string[] = [];
  const levels = header.filter((row) => {
    const isIndexNamesRow =
      indexCount > 0 &&
      row.slice(0, indexCount).some((cell) => cell?.text) &&
      row.slice(indexCount).every((cell) => !cell || !cell.text);
    if (isIndexNamesRow) indexNames = row.slice(0, indexCount).map((cell) => cell?.text || '');
    return !isIndexNamesRow;
  });

  const cellText = (row: GridCell[] | undefined, c: number) => row?.[c]?.text || '';
  const leafRow = levels[levels.length - 1];

  const columns: DataFrameColumn[] = [];
  for (let c = 0; c < colCount; c++) {
    const isIndex = c < indexCount;
    const values = body.map((row) => cellText(row, c));
    if (isIndex) {
      // Index name if pandas wrote one; otherwise the column-axis name shown in that corner
      const label = indexNames[c] || cellText(leafRow, c);
      columns.push({ label, fullLabel: label, isIndex, type: inferType(values) });
      continue;
    }
    const path = levels.map((row) => cellText(row, c));
    const label = levels.length ? cellText(leafRow, c) : `Column ${c - indexCount + 1}`;
    const fullLabel = levels.length ? path.filter(Boolean).join(' / ') : label;
    columns.push({ label, fullLabel, isIndex, type: inferType(values) });
  }

  // Upper levels of MultiIndex columns, with consecutive positions of one source cell merged
  const headerBands: HeaderBandCell[][] = levels.slice(0, -1).map((row) => {
    const band: HeaderBandCell[] = [];
    let c = 0;
    while (c < colCount) {
      const source = row[c]?.source;
      let span = 1;
      while (source && c + span < colCount && row[c + span]?.source === source) span++;
      band.push({ text: cellText(row, c), span, isIndex: c < indexCount });
      c += span;
    }
    return band;
  });

  const rows: DataFrameCell[][] = body.map((row) =>
    Array.from({ length: colCount }, (_, c) => ({
      text: cellText(row, c),
      isIndex: c < indexCount || !!row[c]?.isTh,
    }))
  );

  // pandas appends "<p>N rows × M columns</p>" when it truncates (and for display.show_dimensions)
  let shape: ParsedDataFrame['shape'] = null;
  const dims = (doc.body.textContent || '').match(/([\d,]+)\s+rows?\s+[×x]\s+([\d,]+)\s+columns?/);
  if (dims) shape = { rows: parseInt(dims[1].replace(/,/g, ''), 10), columns: parseInt(dims[2].replace(/,/g, ''), 10) };

  return { columns, headerBands, rows, indexCount, shape };
}
