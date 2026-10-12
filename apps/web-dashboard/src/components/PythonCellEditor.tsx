import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { api } from '../services/api';
import {
  Box,
  Layers,
  Variable,
  Key,
  AlertTriangle,
} from 'lucide-react';

interface CompletionItem {
  label: string;
  type: string;
  detail?: string;
  documentation?: string;
  insert_text?: string;
}

interface DiagnosticItem {
  from_line: number;
  from_col: number;
  to_line: number;
  to_col: number;
  message: string;
  severity: string;
}

interface SignatureItem {
  name: string;
  signature: string;
  params: string[];
  docstring?: string;
  index: number;
}

interface PythonCellEditorProps {
  cellId: string;
  code: string;
  onChange: (newCode: string) => void;
  onRunCurrentCell: (cellId: string, code: string) => void;
  onRunAndAdvance: (cellId: string, code: string) => void;
  onRunAndInsertBelow: (cellId: string, code: string) => void;
  onFocus?: () => void;
  notebookContext?: string[];
  sessionId?: string;
  placeholder?: string;
  readOnly?: boolean;
  editorRef?: (el: HTMLTextAreaElement | null) => void;
  customHeight?: number;
  onHeightChange?: (cellId: string, height: number | undefined) => void;
  isActive?: boolean;
}

const PYTHON_KEYWORDS = [
  'import', 'from', 'def', 'class', 'return', 'for', 'while', 'if', 'elif', 'else',
  'try', 'except', 'finally', 'with', 'as', 'lambda', 'yield', 'async', 'await',
  'pass', 'break', 'continue', 'True', 'False', 'None', 'and', 'or', 'not', 'in',
  'is', 'raise', 'assert', 'del', 'global', 'nonlocal',
];

const PYTHON_BUILTINS: Array<{ label: string; type: string; doc?: string }> = [
  { label: 'print', type: 'function', doc: "print(*args, sep=' ', end='\\n', file=None, flush=False)" },
  { label: 'len', type: 'function', doc: 'Return the number of items in a container.' },
  { label: 'range', type: 'class', doc: 'range(stop) or range(start, stop[, step])' },
  { label: 'enumerate', type: 'class', doc: 'Return an enumerate object yielding (index, value) pairs.' },
  { label: 'zip', type: 'class', doc: 'Iterate over several iterables in parallel.' },
  { label: 'map', type: 'class', doc: 'Make an iterator that computes the function using arguments from each of the iterables.' },
  { label: 'filter', type: 'class', doc: 'Construct an iterator from elements of iterable for which function returns true.' },
  { label: 'sorted', type: 'function', doc: 'Return a new list containing all items from the iterable in ascending order.' },
  { label: 'reversed', type: 'class', doc: 'Return a reverse iterator over the values of the given sequence.' },
  { label: 'sum', type: 'function', doc: 'Return the sum of a start value (default: 0) plus an iterable of numbers.' },
  { label: 'min', type: 'function', doc: 'Return the smallest item in an iterable or the smallest of two or more arguments.' },
  { label: 'max', type: 'function', doc: 'Return the largest item in an iterable or the largest of two or more arguments.' },
  { label: 'abs', type: 'function', doc: 'Return the absolute value of the argument.' },
  { label: 'round', type: 'function', doc: 'Round a number to a given precision in decimal digits.' },
  { label: 'isinstance', type: 'function', doc: 'Return whether an object is an instance of a class or of a subclass thereof.' },
  { label: 'issubclass', type: 'function', doc: 'Return whether a class is a subclass of another class.' },
  { label: 'type', type: 'class', doc: 'Return the type of an object.' },
  { label: 'dir', type: 'function', doc: 'Return an alphabetized list of names comprising (some of) the attributes of the given object.' },
  { label: 'help', type: 'function', doc: 'Invoke the built-in help system.' },
  { label: 'open', type: 'function', doc: 'Open file and return a stream.' },
  { label: 'list', type: 'class', doc: 'Built-in mutable sequence.' },
  { label: 'dict', type: 'class', doc: 'dict() -> new empty dictionary' },
  { label: 'set', type: 'class', doc: 'set() -> new empty set object' },
  { label: 'tuple', type: 'class', doc: 'Built-in immutable sequence.' },
  { label: 'str', type: 'class', doc: 'Create a new string object from the given object.' },
  { label: 'int', type: 'class', doc: 'Convert a number or string to an integer.' },
  { label: 'float', type: 'class', doc: 'Convert a string or number to a floating point number.' },
  { label: 'bool', type: 'class', doc: 'Returns True when the argument x is true, False otherwise.' },
  { label: 'super', type: 'class', doc: 'Return a proxy object that delegates method calls to a parent or sibling class.' },
  { label: 'any', type: 'function', doc: 'Return True if bool(x) is True for any x in the iterable.' },
  { label: 'all', type: 'function', doc: 'Return True if bool(x) is True for all values x in the iterable.' },
  { label: 'getattr', type: 'function', doc: 'Get a named attribute from an object.' },
  { label: 'setattr', type: 'function', doc: 'Sets the named attribute on the given object to the specified value.' },
  { label: 'hasattr', type: 'function', doc: 'Return whether the object has an attribute with the given name.' },
  { label: 'Exception', type: 'class', doc: 'Common base class for all non-exit exceptions.' },
  { label: 'ValueError', type: 'class', doc: 'Inappropriate argument value (of correct type).' },
  { label: 'TypeError', type: 'class', doc: 'Inappropriate argument type.' },
  { label: 'KeyError', type: 'class', doc: 'Mapping key not found.' },
  { label: 'IndexError', type: 'class', doc: 'Sequence index out of range.' },
];

const COMMON_MODULES = [
  'pandas', 'numpy', 'matplotlib', 'seaborn', 'scipy', 'sklearn', 'os', 'sys',
  'json', 'math', 'datetime', 'pathlib', 're', 'time', 'collections', 'itertools',
  'functools', 'typing', 'random', 'statistics', 'sqlite3', 'csv', 'io', 'logging',
];

const CATALOG_MEMBERS: Record<string, Array<{ label: string; type: string; doc?: string }>> = {
  pandas: [
    'read_clipboard', 'read_csv', 'read_excel', 'read_feather', 'read_fwf', 'read_gbq',
    'read_hdf', 'read_html', 'read_iceberg', 'read_json', 'read_orc', 'read_parquet',
    'read_pickle', 'read_sas', 'read_spss', 'read_sql', 'read_sql_query', 'read_sql_table',
    'read_stata', 'read_table', 'read_xml', 'DataFrame', 'Series', 'Index', 'Categorical',
    'Timestamp', 'Timedelta', 'NaT', 'NA', 'concat', 'merge', 'merge_asof', 'merge_ordered',
    'isna', 'isnull', 'notna', 'notnull', 'to_datetime', 'to_numeric', 'to_timedelta',
    'date_range', 'bdate_range', 'period_range', 'timedelta_range', 'crosstab', 'pivot',
    'pivot_table', 'melt', 'cut', 'qcut', 'get_dummies', 'factorize', 'unique', 'value_counts',
    'option_context', 'set_option', 'get_option', 'reset_option', 'describe_option', 'show_versions',
  ].map((name) => ({
    label: name,
    type: /^[A-Z]/.test(name) ? 'class' : 'function',
    doc: `pandas.${name}`,
  })),
  numpy: [
    'array', 'asarray', 'arange', 'linspace', 'logspace', 'zeros', 'zeros_like', 'ones',
    'ones_like', 'empty', 'empty_like', 'full', 'full_like', 'eye', 'identity', 'diag',
    'random', 'linalg', 'fft', 'mean', 'nanmean', 'median', 'nanmedian', 'std', 'nanstd',
    'var', 'nanvar', 'sum', 'nansum', 'prod', 'cumsum', 'cumprod', 'min', 'nanmin', 'max',
    'nanmax', 'argmin', 'argmax', 'argsort', 'sort', 'where', 'select', 'clip', 'round',
    'floor', 'ceil', 'abs', 'sqrt', 'exp', 'log', 'log10', 'log2', 'sin', 'cos', 'tan',
    'dot', 'matmul', 'inner', 'outer', 'concatenate', 'stack', 'vstack', 'hstack', 'split',
    'reshape', 'ravel', 'transpose', 'squeeze', 'expand_dims', 'unique', 'isin', 'isnan',
    'isinf', 'isfinite', 'all', 'any', 'allclose', 'meshgrid', 'histogram', 'corrcoef',
    'cov', 'percentile', 'quantile', 'diff', 'gradient', 'load', 'save', 'loadtxt', 'savetxt',
    'ndarray', 'dtype', 'float32', 'float64', 'int32', 'int64', 'bool_', 'nan', 'inf', 'pi', 'e',
  ].map((name) => ({
    label: name,
    type: ['random', 'linalg', 'fft'].includes(name)
      ? 'module'
      : ['nan', 'inf', 'pi', 'e'].includes(name)
      ? 'property'
      : 'function',
    doc: `numpy.${name}`,
  })),
  DataFrame: [
    'head', 'tail', 'sample', 'info', 'describe', 'shape', 'columns', 'index', 'dtypes',
    'values', 'size', 'ndim', 'empty', 'T', 'loc', 'iloc', 'at', 'iat', 'groupby', 'resample',
    'rolling', 'expanding', 'merge', 'join', 'assign', 'drop', 'dropna', 'drop_duplicates',
    'duplicated', 'fillna', 'ffill', 'bfill', 'isna', 'isnull', 'notna', 'notnull', 'replace',
    'interpolate', 'astype', 'rename', 'set_index', 'reset_index', 'reindex', 'sort_values',
    'sort_index', 'nlargest', 'nsmallest', 'value_counts', 'nunique', 'unique', 'count', 'sum',
    'mean', 'median', 'min', 'max', 'std', 'var', 'quantile', 'cumsum', 'cumprod', 'diff',
    'pct_change', 'corr', 'cov', 'apply', 'map', 'pipe', 'agg', 'aggregate', 'transform',
    'filter', 'query', 'eval', 'where', 'mask', 'clip', 'pivot', 'pivot_table', 'melt',
    'stack', 'unstack', 'explode', 'to_csv', 'to_excel', 'to_json', 'to_parquet', 'to_sql',
    'to_dict', 'to_numpy', 'to_markdown', 'to_html', 'to_string', 'copy', 'plot', 'hist',
    'boxplot', 'style', 'memory_usage', 'select_dtypes', 'iterrows', 'itertuples', 'items',
  ].map((name) => ({
    label: name,
    type: ['shape', 'columns', 'index', 'dtypes', 'values', 'size', 'ndim', 'empty', 'T', 'loc', 'iloc', 'at', 'iat', 'style'].includes(name)
      ? 'property'
      : 'method',
    doc: `DataFrame.${name}`,
  })),
  Series: [
    'head', 'tail', 'sample', 'describe', 'info', 'shape', 'index', 'dtype', 'dtypes',
    'values', 'name', 'size', 'ndim', 'empty', 'loc', 'iloc', 'at', 'iat', 'value_counts',
    'unique', 'nunique', 'count', 'isna', 'isnull', 'notna', 'notnull', 'dropna', 'fillna',
    'ffill', 'bfill', 'replace', 'interpolate', 'astype', 'map', 'apply', 'agg', 'aggregate',
    'transform', 'groupby', 'rolling', 'expanding', 'str', 'dt', 'cat', 'plot', 'hist',
    'sum', 'mean', 'median', 'min', 'max', 'std', 'var', 'quantile', 'cumsum', 'cumprod',
    'diff', 'pct_change', 'corr', 'cov', 'nlargest', 'nsmallest', 'sort_values', 'sort_index',
    'reset_index', 'rename', 'drop', 'drop_duplicates', 'duplicated', 'between', 'isin',
    'where', 'mask', 'clip', 'abs', 'round', 'idxmax', 'idxmin', 'to_list', 'tolist',
    'to_numpy', 'to_frame', 'to_dict', 'to_csv', 'copy', 'any', 'all', 'argmax', 'argmin',
  ].map((name) => ({
    label: name,
    type: ['shape', 'index', 'dtype', 'dtypes', 'values', 'name', 'size', 'ndim', 'empty', 'loc', 'iloc', 'at', 'iat', 'str', 'dt', 'cat'].includes(name)
      ? 'property'
      : 'method',
    doc: `Series.${name}`,
  })),
  'matplotlib.pyplot': [
    'figure', 'subplots', 'subplot', 'gca', 'gcf', 'plot', 'scatter', 'bar', 'barh', 'hist',
    'boxplot', 'violinplot', 'pie', 'errorbar', 'fill_between', 'imshow', 'matshow', 'contour',
    'contourf', 'xlabel', 'ylabel', 'title', 'suptitle', 'legend', 'grid', 'xlim', 'ylim',
    'xticks', 'yticks', 'xscale', 'yscale', 'axis', 'axhline', 'axvline', 'annotate', 'text',
    'colorbar', 'tight_layout', 'subplots_adjust', 'savefig', 'show', 'close', 'clf', 'cla',
    'style', 'rcParams',
  ].map((name) => ({
    label: name,
    type: ['style', 'rcParams'].includes(name) ? 'property' : 'function',
    doc: `matplotlib.pyplot.${name}`,
  })),
  seaborn: [
    'scatterplot', 'lineplot', 'relplot', 'barplot', 'countplot', 'boxplot', 'violinplot',
    'stripplot', 'swarmplot', 'catplot', 'histplot', 'kdeplot', 'ecdfplot', 'rugplot',
    'displot', 'jointplot', 'pairplot', 'heatmap', 'clustermap', 'regplot', 'lmplot',
    'FacetGrid', 'PairGrid', 'JointGrid', 'set_theme', 'set_style', 'set_context',
    'set_palette', 'color_palette', 'despine', 'load_dataset',
  ].map((name) => ({
    label: name,
    type: /^[A-Z]/.test(name) ? 'class' : 'function',
    doc: `seaborn.${name}`,
  })),
};

const BUILTIN_SIGNATURES: Record<string, { signature: string; params: string[]; docstring: string }> = {
  print: {
    signature: "print(*args, sep=' ', end='\\n', file=None, flush=False)",
    params: ['args', 'sep', 'end', 'file', 'flush'],
    docstring: 'Prints the values to a stream, or to sys.stdout by default.',
  },
  len: {
    signature: 'len(obj)',
    params: ['obj'],
    docstring: 'Return the number of items in a container.',
  },
  range: {
    signature: 'range(start, stop, step=1)',
    params: ['start', 'stop', 'step'],
    docstring: 'Return an object that produces a sequence of integers from start to stop.',
  },
  isinstance: {
    signature: 'isinstance(obj, class_or_tuple)',
    params: ['obj', 'class_or_tuple'],
    docstring: 'Return whether an object is an instance of a class or of a subclass thereof.',
  },
  open: {
    signature: "open(file, mode='r', encoding=None)",
    params: ['file', 'mode', 'encoding'],
    docstring: 'Open file and return a stream.',
  },
  'pd.read_csv': {
    signature: "read_csv(filepath_or_buffer, sep=',', header='infer', index_col=None, usecols=None, dtype=None, nrows=None)",
    params: ['filepath_or_buffer', 'sep', 'header', 'index_col', 'usecols', 'dtype', 'nrows'],
    docstring: 'Read a comma-separated values (csv) file into DataFrame.',
  },
  'pd.DataFrame': {
    signature: 'DataFrame(data=None, index=None, columns=None, dtype=None, copy=None)',
    params: ['data', 'index', 'columns', 'dtype', 'copy'],
    docstring: 'Two-dimensional, size-mutable, potentially heterogeneous tabular data.',
  },
  'np.array': {
    signature: "array(object, dtype=None, copy=True, order='K', subok=False, ndmin=0)",
    params: ['object', 'dtype', 'copy', 'order', 'subok', 'ndmin'],
    docstring: 'Create an array.',
  },
};

function parseCodeContext(fullCode: string) {
  const aliases: Record<string, string> = {
    pd: 'pandas',
    np: 'numpy',
    plt: 'matplotlib.pyplot',
    sns: 'seaborn',
  };
  const varTypes: Record<string, string> = {};
  const userSymbols: Map<string, CompletionItem> = new Map();
  const userSignatures: Record<string, { signature: string; params: string[]; docstring: string }> = {};

  const lines = fullCode.split('\n');
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    // import X as Y / import X
    const impMatch = line.match(/^import\s+([A-Za-z0-9_.]+)(?:\s+as\s+([A-Za-z_]\w*))?/);
    if (impMatch) {
      const modName = impMatch[1];
      const alias = impMatch[2] || modName.split('.')[0];
      aliases[alias] = modName;
      userSymbols.set(alias, { label: alias, type: 'module', detail: 'module', documentation: `module ${modName}` });
      continue;
    }

    // from X import Y as Z
    const fromMatch = line.match(/^from\s+([A-Za-z0-9_.]+)\s+import\s+(.+)/);
    if (fromMatch) {
      const modName = fromMatch[1];
      const targets = fromMatch[2].split(',');
      for (const t of targets) {
        const parts = t.trim().split(/\s+as\s+/);
        const orig = parts[0].trim();
        const alias = (parts[1] || orig).trim();
        if (/^[A-Za-z_]\w*$/.test(alias)) {
          aliases[alias] = `${modName}.${orig}`;
          userSymbols.set(alias, { label: alias, type: 'module', detail: 'module', documentation: `from ${modName} import ${orig}` });
        }
      }
      continue;
    }

    // def func_name(params):
    const defMatch = line.match(/^def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)/);
    if (defMatch) {
      const fnName = defMatch[1];
      const paramsRaw = defMatch[2].trim();
      const params = paramsRaw
        ? paramsRaw
            .split(',')
            .map((p) => p.trim().split('=')[0].split(':')[0].replace(/^\*+/, '').trim())
            .filter(Boolean)
        : [];
      userSymbols.set(fnName, { label: fnName, type: 'function', detail: 'function', documentation: `${fnName}(${paramsRaw})` });
      userSignatures[fnName] = {
        signature: `${fnName}(${paramsRaw})`,
        params,
        docstring: `User-defined function ${fnName}`,
      };
      continue;
    }

    // class ClassName:
    const clsMatch = line.match(/^class\s+([A-Za-z_]\w*)/);
    if (clsMatch) {
      const clsName = clsMatch[1];
      userSymbols.set(clsName, { label: clsName, type: 'class', detail: 'class', documentation: `class ${clsName}` });
      continue;
    }

    // var = expr
    const assignMatch = line.match(/^([A-Za-z_]\w*)\s*=\s*(.+)$/);
    if (assignMatch) {
      const varName = assignMatch[1];
      const rhs = assignMatch[2].trim();
      userSymbols.set(varName, { label: varName, type: 'variable', detail: 'variable', documentation: `${varName} = ${rhs.slice(0, 60)}` });

      if (/\b(pd|pandas)\.(read_\w+|DataFrame|concat|merge|pivot_table|crosstab|get_dummies)\s*\(/.test(rhs)) {
        varTypes[varName] = 'DataFrame';
      } else if (/\b(pd|pandas)\.Series\s*\(/.test(rhs)) {
        varTypes[varName] = 'Series';
      } else if (/\b(np|numpy)\.(array|asarray|arange|linspace|zeros|ones|empty|full|eye|random\.\w+)\s*\(/.test(rhs)) {
        varTypes[varName] = 'numpy';
      } else {
        const rhsBase = rhs.match(/^([A-Za-z_]\w*)/)?.[1];
        if (rhsBase && varTypes[rhsBase] === 'DataFrame') {
          if (/^([A-Za-z_]\w*)\[['"][^'"]+['"]\]/.test(rhs)) {
            varTypes[varName] = 'Series';
          } else {
            varTypes[varName] = 'DataFrame';
          }
        }
      }
    }
  }

  return { aliases, varTypes, userSymbols, userSignatures };
}

function resolveReceiverType(receiver: string, aliases: Record<string, string>, varTypes: Record<string, string>): string | null {
  const expr = receiver.trim();
  if (aliases[expr]) return aliases[expr];
  if (varTypes[expr]) return varTypes[expr];
  if (CATALOG_MEMBERS[expr]) return expr;

  // Subscript or chained call on known variable: e.g. df['Order Date'] or df['Order Date'].isna()
  const baseMatch = expr.match(/^([A-Za-z_]\w*)/);
  if (baseMatch) {
    const baseVar = baseMatch[1];
    const baseType = varTypes[baseVar] || (['df', 'raw', 'data', 'dataset', 'table'].includes(baseVar) ? 'DataFrame' : null);
    if (baseType === 'DataFrame') {
      const rest = expr.slice(baseVar.length);
      if (/^\[['"][^'"]+['"]\]/.test(rest)) {
        return 'Series';
      }
      return 'DataFrame';
    }
    if (baseType === 'Series') {
      return 'Series';
    }
  }
  return null;
}

// Compute caret (x, y) coordinates relative to the textarea
function getCaretCoordinates(textarea: HTMLTextAreaElement, position: number) {
  const div = document.createElement('div');
  const style = window.getComputedStyle(textarea);

  const propertiesToCopy = [
    'direction', 'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'borderStyle', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
    'fontSizeAdjust', 'lineHeight', 'fontFamily', 'textAlign', 'textTransform',
    'textIndent', 'textDecoration', 'letterSpacing', 'wordSpacing', 'tabSize',
    'whiteSpace', 'wordBreak',
  ];

  propertiesToCopy.forEach((prop: any) => {
    (div.style as any)[prop] = (style as any)[prop];
  });

  div.style.position = 'absolute';
  div.style.top = '-9999px';
  div.style.left = '-9999px';
  div.style.visibility = 'hidden';
  div.style.whiteSpace = 'pre-wrap';

  const textBefore = textarea.value.substring(0, position);
  div.textContent = textBefore;

  const span = document.createElement('span');
  span.textContent = textarea.value.substring(position) || '.';
  div.appendChild(span);

  document.body.appendChild(div);

  const coordinates = {
    top: span.offsetTop + parseInt(style.borderTopWidth || '0', 10),
    left: span.offsetLeft + parseInt(style.borderLeftWidth || '0', 10),
    lineHeight: parseInt(style.lineHeight || '21', 10),
  };

  document.body.removeChild(div);
  return coordinates;
}

const PythonCellEditorInner: React.FC<PythonCellEditorProps> = ({
  cellId,
  code,
  onChange,
  onRunCurrentCell,
  onRunAndAdvance,
  onRunAndInsertBelow,
  onFocus,
  notebookContext = [],
  sessionId,
  placeholder = '# Write Python code here...',
  readOnly = false,
  editorRef,
  customHeight,
  onHeightChange,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const signatureRef = useRef<HTMLDivElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);
  const diagnosticLayerRef = useRef<HTMLDivElement>(null);
  const autocompleteReqIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const receiverCacheRef = useRef<Map<string, CompletionItem[]>>(new Map());
  const userNavigatedRef = useRef(false);
  const lastInputEventRef = useRef<{ val: string; cursor: number; time: number }>({ val: '', cursor: -1, time: 0 });
  const notebookContextRef = useRef<string[]>(notebookContext);
  notebookContextRef.current = notebookContext;

  // Vertical Resizing State
  const [liveHeight, setLiveHeight] = useState<number | undefined>(customHeight);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    setLiveHeight(customHeight);
  }, [customHeight]);

  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = e.currentTarget.scrollTop;
    }
    if (diagnosticLayerRef.current) {
      diagnosticLayerRef.current.scrollTop = e.currentTarget.scrollTop;
    }
    if ((isDropdownOpen || activeSignature) && textareaRef.current) {
      updatePopupPositions(textareaRef.current.selectionStart);
    }
  };

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    const startY = e.clientY;
    const initialH = liveHeight || textareaRef.current?.clientHeight || 90;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - startY;
      const clamped = Math.max(80, Math.min(800, initialH + delta));
      setLiveHeight(clamped);
      document.body.style.cursor = 'ns-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseUp = (upEvent: MouseEvent) => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsResizing(false);
      const delta = upEvent.clientY - startY;
      const finalH = Math.max(80, Math.min(800, initialH + delta));
      if (onHeightChange) {
        onHeightChange(cellId, finalH);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleResetHeight = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setLiveHeight(undefined);
    if (onHeightChange) {
      onHeightChange(cellId, undefined);
    }
  };

  // Autocomplete state
  const [completions, setCompletions] = useState<CompletionItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; placement: 'above' | 'below' }>({
    top: 0,
    left: 0,
    placement: 'below',
  });

  // Signature help state
  const [activeSignature, setActiveSignature] = useState<SignatureItem | null>(null);
  const [signaturePos, setSignaturePos] = useState<{ top: number; left: number; placement: 'above' | 'below' }>({
    top: 0,
    left: 0,
    placement: 'above',
  });

  // Diagnostics (real Python syntax errors and missing imports)
  const [diagnostics, setDiagnostics] = useState<DiagnosticItem[]>([]);

  const lines = useMemo(() => code.split('\n'), [code]);

  // 1. Fetch Diagnostics (Debounced 300ms, only when this cell's code changes or kernel refreshes)
  const diagnosticsAbortRef = useRef<AbortController | null>(null);

  const fetchDiagnostics = useCallback(async () => {
    if (!code.trim()) {
      setDiagnostics([]);
      return;
    }
    diagnosticsAbortRef.current?.abort();
    const controller = new AbortController();
    diagnosticsAbortRef.current = controller;
    try {
      const res = await api.getDiagnostics(code, notebookContextRef.current, sessionId, controller.signal);
      if (!controller.signal.aborted) {
        setDiagnostics(res.diagnostics || []);
      }
    } catch {
      // Quietly handle network, abort, or dev errors
    }
  }, [code, sessionId]);

  useEffect(() => {
    let isCancelled = false;
    const timer = setTimeout(async () => {
      if (!code.trim()) {
        setDiagnostics([]);
        return;
      }
      diagnosticsAbortRef.current?.abort();
      const controller = new AbortController();
      diagnosticsAbortRef.current = controller;
      try {
        const res = await api.getDiagnostics(code, notebookContextRef.current, sessionId, controller.signal);
        if (!isCancelled && !controller.signal.aborted) {
          setDiagnostics(res.diagnostics || []);
        }
      } catch {
        // Quietly handle network, abort, or dev errors
      }
    }, 300);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
      diagnosticsAbortRef.current?.abort();
    };
  }, [code, sessionId]);

  // Immediately re-fetch diagnostics upon kernel events (package install, kernel restart)
  useEffect(() => {
    const handleGlobalRefresh = () => {
      fetchDiagnostics();
    };
    window.addEventListener('pcs-refresh-diagnostics', handleGlobalRefresh);
    return () => {
      window.removeEventListener('pcs-refresh-diagnostics', handleGlobalRefresh);
    };
  }, [fetchDiagnostics]);

  // Helper to render signature with active parameter highlighted
  const renderSignatureHelp = useCallback((sig: SignatureItem) => {
    if (!sig.signature) return null;
    if (!sig.params || sig.params.length === 0 || sig.index === undefined || sig.index < 0 || sig.index >= sig.params.length) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    const rawParam = sig.params[sig.index];
    const cleanParam = rawParam ? rawParam.replace(/^\*+/, '').split('=')[0].split(':')[0].trim() : '';
    if (!cleanParam) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    let parts: string[];
    try {
      const escapedParam = cleanParam.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(\\b\\*{0,2}${escapedParam}\\b(?:=[^,)]*)?)`, 'g');
      parts = sig.signature.split(regex);
    } catch {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    if (parts.length <= 1) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    return (
      <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>
        {parts.map((part, i) => {
          const isParamMatch = part.replace(/^\*+/, '').startsWith(cleanParam);
          if (isParamMatch) {
            return (
              <span
                key={i}
                style={{
                  textDecoration: 'underline',
                  textDecorationThickness: '2px',
                  color: '#38bdf8',
                  fontWeight: 700,
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  padding: '1px 3px',
                  borderRadius: '3px',
                }}
              >
                {part}
              </span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </div>
    );
  }, []);

  // Priority popup dismissal: closes autocomplete first, signature second
  const dismissTopmostPopup = useCallback((): boolean => {
    autocompleteReqIdRef.current++;
    abortControllerRef.current?.abort();
    if (isDropdownOpen) {
      setIsDropdownOpen(false);
      return true;
    }
    if (activeSignature) {
      setActiveSignature(null);
      return true;
    }
    return false;
  }, [isDropdownOpen, activeSignature]);

  // Dynamically compute caret coordinates and non-overlapping popup positioning
  const updatePopupPositions = useCallback((cursorIndex: number) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    try {
      const coords = getCaretCoordinates(textarea, cursorIndex);
      const textareaRect = textarea.getBoundingClientRect();
      const scrollTop = textarea.scrollTop || 0;
      const scrollLeft = textarea.scrollLeft || 0;

      // Line number gutter width is 44px
      const cursorXInContainer = coords.left + 44 - scrollLeft;
      const cursorYInContainer = coords.top - scrollTop;
      const lineHeight = coords.lineHeight || 21;
      const lineTop = cursorYInContainer;
      const lineBottom = cursorYInContainer + lineHeight;

      // Viewport checks for vertical placement (above vs below cursor)
      const cursorViewportY = textareaRect.top + coords.top - scrollTop;
      const viewportHeight = window.innerHeight;
      const dropdownHeight = 260; // Max height of autocomplete dropdown
      const spaceBelow = viewportHeight - (cursorViewportY + lineHeight + 10);
      const spaceAbove = cursorViewportY - 10;

      // 1. Dropdown positioning (Google Colab style: below cursor if space permits, above if tight below)
      let dropTop: number;
      let dropPlacement: 'above' | 'below';

      if (spaceBelow < dropdownHeight && spaceAbove > spaceBelow) {
        // Open dropdown ABOVE cursor line
        dropTop = lineTop - 6;
        dropPlacement = 'above';
      } else {
        // Open dropdown BELOW cursor line
        dropTop = lineBottom + 6;
        dropPlacement = 'below';
      }

      // 2. Signature Help positioning (Google Colab style: opposite side of dropdown so they never collide)
      let sigTop: number;
      let sigPlacement: 'above' | 'below';

      if (dropPlacement === 'below') {
        // Dropdown is below -> place signature help ABOVE the cursor line
        // If space above in viewport is very tight (< 60px) and dropdown is NOT open, place signature help below
        if (!isDropdownOpen && spaceAbove < 60 && spaceBelow > spaceAbove) {
          sigTop = lineBottom + 6;
          sigPlacement = 'below';
        } else {
          sigTop = lineTop - 6;
          sigPlacement = 'above';
        }
      } else {
        // Dropdown is above -> place signature help BELOW the cursor line
        sigTop = lineBottom + 6;
        sigPlacement = 'below';
      }

      const containerWidth = containerRef.current?.clientWidth || 600;
      const dropdownWidth = 320;
      const sigWidth = 480;

      // Clamp horizontal positions within container bounds
      const dropLeft = Math.max(10, Math.min(cursorXInContainer + 8, containerWidth - dropdownWidth - 16));
      const sigLeft = Math.max(10, Math.min(cursorXInContainer + 8, containerWidth - sigWidth - 16));

      setDropdownPos({ top: dropTop, left: dropLeft, placement: dropPlacement });
      setSignaturePos({ top: sigTop, left: sigLeft, placement: sigPlacement });
    } catch {
      // Fallback
    }
  }, [isDropdownOpen]);

  // Synchronize active selection with visible scroll area
  useEffect(() => {
    if (!isDropdownOpen || !listRef.current) return;
    const container = listRef.current;
    const activeItem = container.children[selectedIndex] as HTMLElement | undefined;
    if (activeItem) {
      const itemTop = activeItem.offsetTop;
      const itemBottom = itemTop + activeItem.offsetHeight;
      const containerTop = container.scrollTop;
      const containerBottom = containerTop + container.clientHeight;

      if (itemTop < containerTop) {
        container.scrollTop = itemTop;
      } else if (itemBottom > containerBottom) {
        container.scrollTop = itemBottom - container.clientHeight;
      }
    }
  }, [selectedIndex, isDropdownOpen]);

  // Click outside to dismiss autocomplete dropdown & signature tooltip
  useEffect(() => {
    if (!isDropdownOpen && !activeSignature) return;

    const handlePointerDownOutside = (e: PointerEvent | MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;

      // Inside dropdown or signature tooltip -> keep open
      if (dropdownRef.current && dropdownRef.current.contains(target)) return;
      if (signatureRef.current && signatureRef.current.contains(target)) return;

      // Inside this cell's textarea -> let textarea handle cursor placement
      if (textareaRef.current && textareaRef.current.contains(target)) return;

      // Clicked outside this editor
      autocompleteReqIdRef.current++;
      abortControllerRef.current?.abort();
      setIsDropdownOpen(false);
      setActiveSignature(null);
    };

    document.addEventListener('pointerdown', handlePointerDownOutside, true);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDownOutside, true);
    };
  }, [isDropdownOpen, activeSignature]);

  // Global Escape handler to ensure dropdown and signature tooltip close with proper priority
  useEffect(() => {
    if (!isDropdownOpen && !activeSignature) return;

    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if ((e as any).__pcsHandledEscape) return;
        (e as any).__pcsHandledEscape = true;
        if (dismissTopmostPopup()) {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [isDropdownOpen, activeSignature, dismissTopmostPopup]);

  // Reposition on window resize
  useEffect(() => {
    const handleWindowResize = () => {
      if ((isDropdownOpen || activeSignature) && textareaRef.current) {
        updatePopupPositions(textareaRef.current.selectionStart);
      }
    };
    window.addEventListener('resize', handleWindowResize);
    return () => window.removeEventListener('resize', handleWindowResize);
  }, [isDropdownOpen, activeSignature, updatePopupPositions]);

  // 2. Trigger Autocomplete when cursor moves or code changes
  // Instant synchronous client-side suggestions (0ms lag) + non-blocking async backend enrichment
  const triggerAutocomplete = useCallback(
    async (cursorIndex: number, explicit = false, overrideCode?: string) => {
      if (readOnly || !textareaRef.current) return;

      const currentCode = overrideCode ?? textareaRef.current?.value ?? code;
      const textBeforeCursor = currentCode.substring(0, cursorIndex);
      const linesBefore = textBeforeCursor.split('\n');
      const currentLine = linesBefore.length;
      const currentCol = linesBefore[linesBefore.length - 1].length;
      const currentLineText = linesBefore[linesBefore.length - 1];

      // Extract current word/prefix and trigger symbol
      const match = currentLineText.match(/([a-zA-Z0-9_\.]+)$/);
      const token = match ? match[1] : '';

      // Check if cursor is inside unclosed function call parentheses
      let openParenCount = 0;
      for (let i = 0; i < textBeforeCursor.length; i++) {
        const ch = textBeforeCursor[i];
        if (ch === '(') openParenCount++;
        else if (ch === ')') openParenCount = Math.max(0, openParenCount - 1);
      }
      const isInsideParens = openParenCount > 0;

      // Check if cursor is inside a string literal or comment on the current line, or naming a declaration/alias
      let inSingleQuote = false;
      let inDoubleQuote = false;
      let inComment = false;
      for (let i = 0; i < currentLineText.length; i++) {
        const ch = currentLineText[i];
        if (ch === '\\') {
          i++;
          continue;
        }
        if (!inSingleQuote && !inDoubleQuote && ch === '#') {
          inComment = true;
          break;
        }
        if (!inDoubleQuote && ch === "'") inSingleQuote = !inSingleQuote;
        else if (!inSingleQuote && ch === '"') inDoubleQuote = !inDoubleQuote;
      }
      const isInStringOrComment = inSingleQuote || inDoubleQuote || inComment;
      const isDeclarationName =
        /^\s*(?:import\s+.+\s+as|from\s+.+\s+import\s+.+\s+as|def|class|for|except\s+.+\s+as)\s+[A-Za-z_]\w*$/.test(
          currentLineText
        );

      if (!explicit && (isInStringOrComment || isDeclarationName)) {
        autocompleteReqIdRef.current++;
        abortControllerRef.current?.abort();
        setIsDropdownOpen(false);
        if (inComment || !isInsideParens) {
          setActiveSignature(null);
        }
        return;
      }

      const isDotTrigger = currentLineText.endsWith('.');
      const isWordTrigger =
        token.length >= 1 && (token.includes('.') || explicit || token.length >= 2 || (isInsideParens && token.length >= 1));

      if (!explicit && !isDotTrigger && !isWordTrigger && !isInsideParens) {
        autocompleteReqIdRef.current++;
        abortControllerRef.current?.abort();
        setIsDropdownOpen(false);
        setActiveSignature(null);
        return;
      }

      // Extract receiver & prefix for member completions (including subscript/call chains like df['col']. or df.isna().)
      const dotReceiverMatch = currentLineText.match(
        /([A-Za-z_]\w*(?:\[[^\]]+\]|\([^)]*\)|\.[A-Za-z_]\w*)*)\.([A-Za-z0-9_]*)$/
      );
      const isMemberAccess = dotReceiverMatch !== null || isDotTrigger || token.includes('.');
      const receiverExpr = dotReceiverMatch
        ? dotReceiverMatch[1]
        : token.includes('.')
        ? token.slice(0, token.lastIndexOf('.'))
        : '';
      const prefix = dotReceiverMatch
        ? dotReceiverMatch[2]
        : token.includes('.')
        ? token.split('.').pop() || ''
        : token;

      const filterAndRank = (rawItems: CompletionItem[], pfx: string): CompletionItem[] => {
        if (!pfx) return rawItems;
        const lowerPfx = pfx.toLowerCase();
        const filtered = rawItems.filter((item) => item.label.toLowerCase().includes(lowerPfx));
        filtered.sort((a, b) => {
          const aStarts = a.label.toLowerCase().startsWith(lowerPfx);
          const bStarts = b.label.toLowerCase().startsWith(lowerPfx);
          if (aStarts && !bStarts) return -1;
          if (!aStarts && bStarts) return 1;
          return a.label.localeCompare(b.label);
        });
        return filtered;
      };

      // Compute Caret Coordinates for floating dropdown & signature
      const reqId = ++autocompleteReqIdRef.current;
      userNavigatedRef.current = false;
      updatePopupPositions(cursorIndex);

      // Dropdown should ONLY open if explicit (Ctrl+Space), dot trigger, or a non-empty word token
      // NOT on empty paren trigger like print(
      const shouldShowDropdown = explicit || isDotTrigger || (token.length >= 1 && !currentLineText.endsWith('('));

      // --- PHASE 1: Instant Synchronous Client-Side Completions & Signature Help (0ms) ---
      const otherLines = currentCode.split('\n').filter((_, idx) => idx !== currentLine - 1);
      const fullSource = [...notebookContextRef.current, ...otherLines].join('\n');
      const parsed = parseCodeContext(fullSource);
      let localCandidates: CompletionItem[] = [];

      if (isMemberAccess) {
        const seenLabels = new Set<string>();
        const cached = receiverCacheRef.current.get(receiverExpr) || [];
        for (const item of cached) {
          if (!seenLabels.has(item.label)) {
            seenLabels.add(item.label);
            localCandidates.push(item);
          }
        }
        const resolvedType = resolveReceiverType(receiverExpr, parsed.aliases, parsed.varTypes);
        const catalogItems = (resolvedType && CATALOG_MEMBERS[resolvedType]) || [];
        for (const c of catalogItems) {
          if (!seenLabels.has(c.label)) {
            seenLabels.add(c.label);
            localCandidates.push({
              label: c.label,
              type: c.type,
              detail: c.type,
              documentation: c.doc || `${receiverExpr}.${c.label}`,
            });
          }
        }
      } else {
        const seenLabels = new Set<string>();
        for (const sym of parsed.userSymbols.values()) {
          if (!seenLabels.has(sym.label)) {
            seenLabels.add(sym.label);
            localCandidates.push(sym);
          }
        }
        for (const b of PYTHON_BUILTINS) {
          if (!seenLabels.has(b.label)) {
            seenLabels.add(b.label);
            localCandidates.push({
              label: b.label,
              type: b.type,
              detail: b.type,
              documentation: b.doc,
            });
          }
        }
        for (const kw of PYTHON_KEYWORDS) {
          if (!seenLabels.has(kw)) {
            seenLabels.add(kw);
            localCandidates.push({
              label: kw,
              type: 'keyword',
              detail: 'keyword',
              documentation: `Python keyword '${kw}'`,
            });
          }
        }
        for (const mod of COMMON_MODULES) {
          if (!seenLabels.has(mod)) {
            seenLabels.add(mod);
            localCandidates.push({
              label: mod,
              type: 'module',
              detail: 'module',
              documentation: `Python module '${mod}'`,
            });
          }
        }
      }

      const localItems = filterAndRank(localCandidates, prefix);
      if (shouldShowDropdown && localItems.length > 0) {
        setCompletions(localItems);
        setSelectedIndex(0);
        if (listRef.current) {
          listRef.current.scrollTop = 0;
        }
        setIsDropdownOpen(true);
      } else if (!shouldShowDropdown) {
        setIsDropdownOpen(false);
      }

      // Instant synchronous signature help if inside parens
      let localSigFound = false;
      if (isInsideParens) {
        let depth = 0;
        let openIdx = -1;
        let commaCount = 0;
        for (let i = textBeforeCursor.length - 1; i >= 0; i--) {
          const ch = textBeforeCursor[i];
          if (ch === ')' || ch === ']' || ch === '}') depth++;
          else if (ch === '(' || ch === '[' || ch === '{') {
            if (depth === 0 && ch === '(') {
              openIdx = i;
              break;
            }
            depth = Math.max(0, depth - 1);
          } else if (ch === ',' && depth === 0) {
            commaCount++;
          }
        }
        if (openIdx >= 0) {
          const beforeParen = textBeforeCursor.slice(0, openIdx);
          const fnMatch = beforeParen.match(/([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*$/);
          if (fnMatch) {
            const fnExpr = fnMatch[1];
            const sigDef =
              parsed.userSignatures[fnExpr] ||
              BUILTIN_SIGNATURES[fnExpr];
            if (sigDef) {
              localSigFound = true;
              setActiveSignature({
                name: fnExpr.split('.').pop() || fnExpr,
                signature: sigDef.signature,
                params: sigDef.params,
                docstring: sigDef.docstring,
                index: sigDef.params.length > 0 ? Math.min(commaCount, sigDef.params.length - 1) : 0,
              });
            }
          }
        }
      } else {
        setActiveSignature(null);
      }

      // --- PHASE 2: Non-Blocking Async Backend Enrichment with AbortController ---
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const res = await api.getCompletions(
          currentCode,
          currentLine,
          currentCol,
          notebookContextRef.current,
          sessionId,
          controller.signal
        );
        if (reqId !== autocompleteReqIdRef.current || controller.signal.aborted) return;

        const backendRaw = res.completions || [];

        // Update receiver cache so subsequent characters after this dot resolve in 0ms
        if (isMemberAccess && receiverExpr && backendRaw.length > 0) {
          if (!prefix) {
            receiverCacheRef.current.set(receiverExpr, backendRaw);
          } else {
            const existing = receiverCacheRef.current.get(receiverExpr) || [];
            const mergedCache = new Map<string, CompletionItem>();
            for (const item of existing) mergedCache.set(item.label, item);
            for (const item of backendRaw) mergedCache.set(item.label, item);
            receiverCacheRef.current.set(receiverExpr, Array.from(mergedCache.values()));
          }
        }

        // Merge backend items with local items (preferring backend metadata)
        const mergedMap = new Map<string, CompletionItem>();
        for (const item of backendRaw) {
          mergedMap.set(item.label, item);
        }
        for (const item of localItems) {
          if (!mergedMap.has(item.label)) {
            mergedMap.set(item.label, item);
          }
        }

        const finalItems = filterAndRank(Array.from(mergedMap.values()), prefix);

        if (shouldShowDropdown && finalItems.length > 0) {
          setCompletions(finalItems);
          if (!userNavigatedRef.current) {
            setSelectedIndex(0);
            if (listRef.current) {
              listRef.current.scrollTop = 0;
            }
          } else {
            setSelectedIndex((prev) => Math.min(prev, finalItems.length - 1));
          }
          setIsDropdownOpen(true);
        } else if (finalItems.length === 0) {
          setIsDropdownOpen(false);
        }

        // Signature help (only when inside parentheses)
        if (isInsideParens) {
          if (res.signatures && res.signatures.length > 0) {
            setActiveSignature(res.signatures[0]);
          } else if (!localSigFound) {
            setActiveSignature(null);
          }
        } else {
          setActiveSignature(null);
        }
      } catch (err: any) {
        if (err?.name === 'AbortError' || controller.signal.aborted || reqId !== autocompleteReqIdRef.current) {
          return;
        }
        if (localItems.length === 0) {
          setIsDropdownOpen(false);
        }
        if (!localSigFound) {
          setActiveSignature(null);
        }
      }
    },
    [code, sessionId, readOnly, updatePopupPositions]
  );

  // Insert selected completion into textarea
  const acceptCompletion = useCallback(
    (item: CompletionItem) => {
      const el = textareaRef.current;
      if (!el) return;

      const currentValue = el.value;
      const cursorPos = el.selectionStart;

      // Extract the line up to the cursor
      const textBefore = currentValue.substring(0, cursorPos);
      const lines = textBefore.split('\n');
      const currentLine = lines[lines.length - 1];

      // Match the incomplete token being completed:
      // Case A: Member completion after a dot: e.g. "pd.re", "pd.read_c", "pd."
      // The prefix to replace is whatever follows the last dot on this line.
      const dotMatch = currentLine.match(/\.([a-zA-Z0-9_]*)$/);

      let replaceStart = cursorPos;
      if (dotMatch !== null) {
        const prefix = dotMatch[1];
        replaceStart = cursorPos - prefix.length;
      } else {
        // Case B: Standalone identifier: e.g. "pri", "im"
        const idMatch = currentLine.match(/([a-zA-Z0-9_]+)$/);
        if (idMatch !== null) {
          const prefix = idMatch[1];
          replaceStart = cursorPos - prefix.length;
        }
      }

      // Check for any matching identifier suffix immediately following cursor
      const textAfter = currentValue.substring(cursorPos);
      const firstLineAfter = textAfter.split('\n')[0];
      const suffixMatch = firstLineAfter.match(/^([a-zA-Z0-9_]+)/);
      const replaceEnd = suffixMatch ? cursorPos + suffixMatch[1].length : el.selectionEnd;

      const before = currentValue.substring(0, replaceStart);
      const after = currentValue.substring(replaceEnd);
      const insert = item.insert_text || item.label;
      const newCode = before + insert + after;
      const newCursorPos = before.length + insert.length;

      autocompleteReqIdRef.current++;
      abortControllerRef.current?.abort();
      el.value = newCode;
      el.setSelectionRange(newCursorPos, newCursorPos);
      lastInputEventRef.current = { val: newCode, cursor: newCursorPos, time: performance.now() };
      onChange(newCode);
      setIsDropdownOpen(false);
      setActiveSignature(null);

      // Restore focus and update cursor position
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        }
      });
    },
    [onChange]
  );

  // 3. Keyboard Navigation in Code & Autocomplete
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // 1. Cross-platform Execution Shortcuts
    const isCtrlOrCmdEnter = (e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.shiftKey && !e.altKey;
    const isShiftEnter = e.shiftKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey;
    const isAltEnter = e.altKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey;

    if (isCtrlOrCmdEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      abortControllerRef.current?.abort();
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunCurrentCell(cellId, e.currentTarget.value);
      return;
    }

    if (isShiftEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      abortControllerRef.current?.abort();
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunAndAdvance(cellId, e.currentTarget.value);
      return;
    }

    if (isAltEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      abortControllerRef.current?.abort();
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunAndInsertBelow(cellId, e.currentTarget.value);
      return;
    }

    // 2. Dropdown active keyboard handling
    if (isDropdownOpen && completions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        userNavigatedRef.current = true;
        setSelectedIndex((prev) => (prev + 1) % completions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        userNavigatedRef.current = true;
        setSelectedIndex((prev) => (prev - 1 + completions.length) % completions.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        e.stopPropagation();
        acceptCompletion(completions[selectedIndex]);
        return;
      }
    }

    // Dismiss popups on Escape with single-key priority
    if (e.key === 'Escape') {
      if ((e.nativeEvent as any)?.__pcsHandledEscape) {
        return;
      }
      (e.nativeEvent as any).__pcsHandledEscape = true;
      if (dismissTopmostPopup()) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
    }

    // 3. Manual Autocomplete Trigger (Ctrl+Space / Cmd+Space)
    if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
      e.preventDefault();
      triggerAutocomplete(e.currentTarget.selectionStart, true, e.currentTarget.value);
      return;
    }

    // 4. Tab key: Indent 4 spaces if dropdown is closed
    if (e.key === 'Tab' && !isDropdownOpen) {
      e.preventDefault();
      const el = e.currentTarget;
      const currentVal = el.value;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const newCode = currentVal.substring(0, start) + '    ' + currentVal.substring(end);
      el.value = newCode;
      el.selectionStart = el.selectionEnd = start + 4;
      lastInputEventRef.current = { val: newCode, cursor: start + 4, time: performance.now() };
      onChange(newCode);
      return;
    }

    // 5a. Step over existing closing pair character: ), ], }, ', "
    const closingChars = new Set([')', ']', '}', '"', "'"]);
    if (closingChars.has(e.key) && !e.ctrlKey && !e.metaKey) {
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      if (start === end && el.value[start] === e.key) {
        e.preventDefault();
        el.selectionStart = el.selectionEnd = start + 1;
        triggerAutocomplete(start + 1, false, el.value);
        return;
      }
    }

    // 5b. Auto-closing pairs: (, [, {, ', "
    const pairs: Record<string, string> = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" };
    if (pairs[e.key] && !e.ctrlKey && !e.metaKey) {
      const el = e.currentTarget;
      const currentVal = el.value;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      if (start === end) {
        const closeChar = pairs[e.key];
        e.preventDefault();
        const newCode = currentVal.substring(0, start) + e.key + closeChar + currentVal.substring(end);
        el.value = newCode;
        el.selectionStart = el.selectionEnd = start + 1;
        lastInputEventRef.current = { val: newCode, cursor: start + 1, time: performance.now() };
        onChange(newCode);
        triggerAutocomplete(start + 1, false, newCode);
        return;
      }
    }

    // 6. Auto-indentation after colon
    if (e.key === 'Enter') {
      const el = e.currentTarget;
      const currentVal = el.value;
      const cursor = el.selectionStart;
      const lineBeforeCursor = currentVal.substring(0, cursor).split('\n').pop() || '';
      const matchIndent = lineBeforeCursor.match(/^(\s*)/);
      const currentIndent = matchIndent ? matchIndent[1] : '';
      const extraIndent = lineBeforeCursor.trim().endsWith(':') ? '    ' : '';

      if (currentIndent || extraIndent) {
        e.preventDefault();
        const insertText = '\n' + currentIndent + extraIndent;
        const newCode = currentVal.substring(0, cursor) + insertText + currentVal.substring(cursor);
        const newPos = cursor + insertText.length;
        el.value = newCode;
        el.selectionStart = el.selectionEnd = newPos;
        lastInputEventRef.current = { val: newCode, cursor: newPos, time: performance.now() };
        onChange(newCode);
        return;
      }
    }
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const val = e.currentTarget.value;
    const cursor = e.currentTarget.selectionStart;
    const now = performance.now();

    // Only notify parent state when code actually changed
    if (val !== code) {
      onChange(val);
    }

    // Deduplicate back-to-back onChange + onInput events firing in the same tick for the exact same (val, cursor)
    if (
      val === lastInputEventRef.current.val &&
      cursor === lastInputEventRef.current.cursor &&
      now - lastInputEventRef.current.time < 25
    ) {
      return;
    }
    lastInputEventRef.current = { val, cursor, time: now };

    // Trigger autocomplete synchronously so local completions render in the same frame (0ms delay)
    triggerAutocomplete(cursor, false, val);
  };

  const handleClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    if (isDropdownOpen) setIsDropdownOpen(false);
    triggerAutocomplete(e.currentTarget.selectionStart, false, e.currentTarget.value);
  };

  // Icon mapping for completion item types
  const renderItemIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'function':
      case 'method':
        return <span style={{ color: '#60a5fa', fontWeight: 700, fontSize: '11px', width: '16px', textAlign: 'center' }}>ƒ</span>;
      case 'module':
      case 'package':
        return <Box size={13} color="#f59e0b" />;
      case 'class':
        return <Layers size={13} color="#a855f7" />;
      case 'keyword':
        return <Key size={13} color="#ec4899" />;
      case 'property':
      case 'statement':
        return <span style={{ color: '#38bdf8', fontSize: '12px' }}>✦</span>;
      default:
        return <Variable size={13} color="#10b981" />;
    }
  };

  // Check if a line has an active diagnostic
  const getLineDiagnostic = (lineNum: number) => {
    return diagnostics.find((d) => d.from_line === lineNum);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        backgroundColor: 'var(--bg-cell)',
        borderRadius: '6px',
        border: '1px solid var(--border-main)',
        overflow: 'visible',
      }}
    >
      <div style={{ display: 'flex', width: '100%', position: 'relative' }}>
        {/* 1. Left Line Number Gutter */}
        <div
          ref={gutterRef}
          style={{
            width: '44px',
            padding: '10px 0',
            backgroundColor: 'var(--bg-cell-gutter)',
            borderRight: '1px solid var(--border-main)',
            color: 'var(--text-muted)',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            fontSize: '12.5px',
            lineHeight: '21px',
            textAlign: 'right',
            userSelect: 'none',
            flexShrink: 0,
            overflowY: 'hidden',
            height: liveHeight ? `${liveHeight}px` : undefined,
            minHeight: liveHeight ? `${liveHeight}px` : `${Math.max(68, lines.length * 21 + 20)}px`,
            maxHeight: liveHeight ? `${liveHeight}px` : undefined,
          }}
        >
          {lines.map((_, i) => {
            const lineNum = i + 1;
            const diag = getLineDiagnostic(lineNum);
            return (
              <div
                key={lineNum}
                style={{
                  paddingRight: '10px',
                  height: '21px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  gap: '4px',
                  color: diag ? '#ef4444' : 'var(--text-muted)',
                  fontWeight: diag ? 700 : 400,
                }}
                title={diag ? diag.message : undefined}
              >
                {diag && <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#ef4444' }} />}
                {lineNum}
              </div>
            );
          })}
        </div>

        {/* 2. Main Editor Area */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {/* Underlying Diagnostics Underline Layer */}
          <div
            ref={diagnosticLayerRef}
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              padding: '10px 14px',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              fontSize: '13.5px',
              lineHeight: '21px',
              pointerEvents: 'none',
              whiteSpace: 'pre',
              zIndex: 1,
              color: 'transparent',
              overflowY: 'hidden',
              overflowX: 'hidden',
              height: liveHeight ? `${liveHeight}px` : undefined,
              maxHeight: liveHeight ? `${liveHeight}px` : undefined,
            }}
          >
            {lines.map((lineStr, lineIdx) => {
              const lineNum = lineIdx + 1;
              const diag = getLineDiagnostic(lineNum);

              if (!diag) {
                return (
                  <div key={lineIdx} style={{ height: '21px' }}>
                    {lineStr || ' '}
                  </div>
                );
              }

              const fromCol = Math.max(0, Math.min(lineStr.length, diag.from_col));
              const toCol = Math.max(fromCol + 1, Math.min(lineStr.length, diag.to_col));

              const before = lineStr.substring(0, fromCol);
              const errorPart = lineStr.substring(fromCol, toCol) || lineStr.slice(-1) || ' ';
              const after = lineStr.substring(toCol);

              return (
                <div key={lineIdx} style={{ height: '21px' }}>
                  <span>{before}</span>
                  <span
                    style={{
                      textDecoration: 'underline wavy #ef4444',
                      textDecorationSkipInk: 'none',
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      borderRadius: '2px',
                    }}
                  >
                    {errorPart}
                  </span>
                  <span>{after}</span>
                </div>
              );
            })}
          </div>

          {/* Real Editor Textarea */}
          <textarea
            ref={(el) => {
              (textareaRef as React.MutableRefObject<HTMLTextAreaElement | null>).current = el;
              if (editorRef) editorRef(el);
            }}
            data-testid="code-cell-editor"
            className="code-font code-cell-editor"
            value={code}
            onFocus={onFocus}
            onChange={handleInput}
            onInput={handleInput}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            placeholder={placeholder}
            readOnly={readOnly}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            data-gramm="false"
            style={{
              width: '100%',
              height: liveHeight ? `${liveHeight}px` : undefined,
              minHeight: liveHeight ? `${liveHeight}px` : `${Math.max(68, lines.length * 21 + 20)}px`,
              maxHeight: liveHeight ? `${liveHeight}px` : undefined,
              backgroundColor: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--code-text)',
              fontSize: '13.5px',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              lineHeight: '21px',
              padding: '10px 14px',
              resize: 'none',
              whiteSpace: 'pre',
              overflowX: 'auto',
              overflowY: liveHeight ? 'auto' : 'hidden',
              position: 'relative',
              zIndex: 2,
              caretColor: 'var(--border-accent)',
            }}
          />

          {/* Hover Diagnostic Tooltip */}
          {diagnostics.length > 0 && (
            <div
              data-testid="diagnostic-badge"
              style={{
                position: 'absolute',
                right: '12px',
                bottom: '8px',
                zIndex: 3,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '5px',
                padding: '3px 8px',
                fontSize: '11px',
                color: '#ef4444',
                pointerEvents: 'none',
              }}
            >
              <AlertTriangle size={12} color="#ef4444" />
              <span>{diagnostics[0].message}</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. Draggable vertical resize handle */}
      <div
        data-testid="cell-resize-handle"
        onMouseDown={handleResizeMouseDown}
        onDoubleClick={handleResetHeight}
        style={{
          height: '10px',
          cursor: 'ns-resize',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: isResizing ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
          borderTop: '1px solid var(--border-main)',
          userSelect: 'none',
          width: '100%',
          transition: 'background-color 0.15s ease',
        }}
        title="Drag up/down to resize code cell. Double-click to auto-fit."
      >
        <div
          style={{
            width: '36px',
            height: '4px',
            borderRadius: '2px',
            backgroundColor: isResizing ? 'var(--border-accent)' : 'var(--border-secondary)',
          }}
        />
      </div>

      {/* 4. Floating Signature Help Tooltip */}
      {activeSignature && (
        <div
          ref={signatureRef}
          data-testid="signature-help-tooltip"
          style={{
            position: 'absolute',
            top: `${signaturePos.top}px`,
            left: `${signaturePos.left}px`,
            transform: signaturePos.placement === 'above' ? 'translateY(-100%)' : 'none',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-accent)',
            borderRadius: '6px',
            padding: '6px 12px',
            zIndex: 1001,
            boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
            fontSize: '12px',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            color: 'var(--text-main)',
            maxWidth: '480px',
            pointerEvents: 'none',
          }}
        >
          {renderSignatureHelp(activeSignature)}
          {activeSignature.docstring && (
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', whiteSpace: 'pre-wrap', maxHeight: '100px', overflowY: 'auto' }}>
              {activeSignature.docstring}
            </div>
          )}
        </div>
      )}

      {/* 5. Google Colab-style Autocomplete Dropdown */}
      {isDropdownOpen && completions.length > 0 && (
        <div
          ref={dropdownRef}
          data-testid="autocomplete-dropdown"
          role="dialog"
          aria-label="Code Suggestions"
          style={{
            position: 'absolute',
            top: `${dropdownPos.top}px`,
            left: `${dropdownPos.left}px`,
            transform: dropdownPos.placement === 'above' ? 'translateY(-100%)' : 'none',
            width: '320px',
            maxHeight: '260px',
            backgroundColor: 'var(--dropdown-bg)',
            border: '1px solid var(--dropdown-border)',
            borderRadius: '8px',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.25)',
            zIndex: 1000,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header indicator */}
          <div
            style={{
              padding: '5px 10px',
              backgroundColor: 'var(--dropdown-header-bg)',
              borderBottom: '1px solid var(--border-main)',
              fontSize: '10.5px',
              color: 'var(--text-muted)',
              fontWeight: 600,
              display: 'flex',
              justifyContent: 'space-between',
              userSelect: 'none',
            }}
          >
            <span>SUGGESTIONS ({completions.length})</span>
            <span>Tab / ↵ to insert</span>
          </div>

          {/* Completion List */}
          <div
            ref={listRef}
            role="listbox"
            tabIndex={-1}
            style={{
              overflowY: 'auto',
              maxHeight: '220px',
              overscrollBehavior: 'contain',
            }}
          >
            {completions.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={`${item.label}-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  data-testid={`completion-item-${item.label}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    acceptCompletion(item);
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    acceptCompletion(item);
                  }}
                  onMouseEnter={() => {
                    userNavigatedRef.current = true;
                    setSelectedIndex(idx);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 10px',
                    backgroundColor: isSelected ? 'var(--dropdown-item-selected)' : 'transparent',
                    cursor: 'pointer',
                    fontSize: '12.5px',
                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                    borderBottom: '1px solid var(--border-main)',
                    transition: 'background-color 0.05s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    {renderItemIcon(item.type)}
                    <span
                      style={{
                        color: isSelected ? 'var(--dropdown-item-selected-text)' : 'var(--text-main)',
                        fontWeight: isSelected ? 600 : 400,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {item.label}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      color: isSelected ? 'var(--dropdown-item-selected-text)' : 'var(--text-muted)',
                      flexShrink: 0,
                      marginLeft: '8px',
                    }}
                  >
                    {item.type}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Selected Item Documentation Preview Footer */}
          {completions[selectedIndex]?.documentation && (
            <div
              style={{
                padding: '6px 10px',
                backgroundColor: 'var(--dropdown-header-bg)',
                borderTop: '1px solid var(--border-main)',
                fontSize: '11px',
                color: 'var(--text-secondary)',
                maxHeight: '60px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                overscrollBehavior: 'contain',
              }}
            >
              {completions[selectedIndex].documentation}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const PythonCellEditor = React.memo(PythonCellEditorInner, (prev, next) => {
  if (
    prev.cellId !== next.cellId ||
    prev.code !== next.code ||
    prev.customHeight !== next.customHeight ||
    prev.readOnly !== next.readOnly ||
    prev.sessionId !== next.sessionId ||
    prev.placeholder !== next.placeholder ||
    prev.isActive !== next.isActive
  ) {
    return false;
  }
  // If this cell is currently active, check whether preceding cells' context changed
  if (next.isActive) {
    const prevCtx = prev.notebookContext || [];
    const nextCtx = next.notebookContext || [];
    if (prevCtx.length !== nextCtx.length) return false;
    for (let i = 0; i < prevCtx.length; i++) {
      if (prevCtx[i] !== nextCtx[i]) return false;
    }
  }
  return true;
});

