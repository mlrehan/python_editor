import os
import sys
import ast
import re
import asyncio
import importlib.util
import importlib.machinery
from typing import List, Dict, Any, Optional, Tuple, Union
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import jedi

from ..auth import get_current_user_or_guest, GuestUser
from ..models import User
from ..kernel_bridge import kernel_pool

router = APIRouter(prefix="/editor", tags=["Language Service / IntelliSense"])


class CompletionRequest(BaseModel):
    code: str = Field(..., description="Current cell code content")
    line: int = Field(1, description="1-indexed line number where cursor is located")
    column: int = Field(0, description="0-indexed column offset in the current line")
    notebook_context: List[str] = Field(default=[], description="Code of preceding notebook cells in order")
    session_id: Optional[str] = Field(None, description="Active kernel session ID for runtime introspection")


class CompletionItem(BaseModel):
    label: str
    type: str  # function, module, class, property, variable, keyword, etc.
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None


class CompletionResponse(BaseModel):
    completions: List[CompletionItem]
    signatures: List[Dict[str, Any]] = []


class SignatureRequest(BaseModel):
    code: str
    line: int = 1
    column: int = 0
    notebook_context: List[str] = []
    session_id: Optional[str] = None


class DiagnosticItem(BaseModel):
    from_line: int
    from_col: int
    to_line: int
    to_col: int
    message: str
    severity: str = "error"  # "error", "warning"


class DiagnosticsRequest(BaseModel):
    code: str
    notebook_context: List[str] = []
    session_id: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    diagnostics: List[DiagnosticItem]


def _build_virtual_script(code: str, line: int, notebook_context: List[str]):
    """Combines preceding cells and current cell to provide cross-cell notebook awareness."""
    clean_context = [c.strip("\r\n") for c in notebook_context if c.strip()]
    if not clean_context:
        return code, line

    prefix = "\n\n".join(clean_context) + "\n\n"
    line_offset = sum(c.count("\n") + 2 for c in clean_context)
    full_code = prefix + code
    eval_line = line_offset + line
    return full_code, eval_line


import time
import builtins
import keyword
import inspect
import threading

_WS_PATHS_CACHE: Dict[Tuple[str, str], Tuple[float, str, List[str]]] = {}
_WS_CACHE_TTL = 5.0

_JEDI_PROJECTS: Dict[Tuple[str, Tuple[str, ...]], Any] = {}
_JEDI_LOCK = threading.Lock()
_JEDI_COMP_CACHE: Dict[Tuple[str, str, str], Tuple[float, List["CompletionItem"]]] = {}
_OBJECT_MEMBER_CACHE: Dict[str, List["CompletionItem"]] = {}
_TOP_LEVEL_BUILTINS_CACHE: Optional[List["CompletionItem"]] = None

_DF_CREATORS = {
    "read_csv", "read_excel", "read_json", "read_parquet", "read_sql",
    "read_sql_query", "read_sql_table", "read_table", "read_feather",
    "read_fwf", "read_html", "read_pickle", "read_orc", "read_spss",
    "read_stata", "read_xml", "read_clipboard", "DataFrame", "concat",
    "merge", "merge_ordered", "merge_asof", "pivot", "pivot_table",
    "get_dummies", "crosstab", "json_normalize",
}
_DF_CHAIN_METHODS = {
    "dropna", "fillna", "drop", "drop_duplicates", "rename", "rename_axis",
    "sort_values", "sort_index", "reset_index", "set_index", "reindex",
    "query", "assign", "copy", "head", "tail", "sample", "nlargest",
    "nsmallest", "merge", "join", "astype", "replace", "abs", "round",
    "diff", "pct_change", "shift", "clip", "corr", "cov", "describe",
    "loc", "iloc", "groupby", "pivot", "pivot_table", "melt", "stack",
    "unstack", "T", "transpose", "filter", "where", "mask", "apply",
    "applymap", " map", "pipe", "ffill", "bfill", "interpolate",
}
_SERIES_CHAIN_METHODS = {
    "isna", "isnull", "notna", "notnull", "dropna", "fillna", "astype",
    "apply", "map", "replace", "clip", "abs", "round", "diff", "pct_change",
    "shift", "sort_values", "sort_index", "value_counts", "copy", "head",
    "tail", "sample", "nlargest", "nsmallest", "reset_index", "between",
    "isin", "ffill", "bfill", "interpolate", "where", "mask",
}
_NDARRAY_CREATORS = {
    "array", "arange", "zeros", "ones", "empty", "full", "linspace",
    "logspace", "geomspace", "eye", "identity", "asarray", "asanyarray",
    "ascontiguousarray", "frombuffer", "fromiter", "fromfunction",
    "meshgrid", "diag", "tri", "tril", "triu", "vander",
}


def _get_workspace_search_paths(
    session_id: Optional[str] = None,
    current_user: Optional[Union[User, GuestUser]] = None,
) -> Tuple[str, List[str]]:
    """
    Resolves the active workspace directory and all Python package search paths,
    including the user workspace root, .local/site-packages, and multi-tenant paths.
    Cached with a short TTL to avoid filesystem walks on every keystroke.
    """
    user_key = "anon"
    if current_user:
        user_key = (
            f"guest_{current_user.guest_token}"
            if getattr(current_user, "is_guest", False)
            else str(getattr(current_user, "id", "public"))
        )
    cache_key = (session_id or "", user_key)
    now = time.monotonic()
    cached = _WS_PATHS_CACHE.get(cache_key)
    if cached and (now - cached[0]) < _WS_CACHE_TTL:
        return cached[1], cached[2]

    candidate_dirs: List[str] = []
    primary_ws: Optional[str] = None

    if session_id:
        session = kernel_pool.get_session(session_id)
        if session and session.workspace_dir:
            primary_ws = session.workspace_dir
            candidate_dirs.append(primary_ws)

    if not primary_ws and current_user:
        target_uid = (
            f"guest_{current_user.guest_token}"
            if getattr(current_user, "is_guest", False)
            else getattr(current_user, "id", "public")
        )
        primary_ws = kernel_pool.get_user_workspace_path(target_uid)
        candidate_dirs.append(primary_ws)

    if not primary_ws:
        primary_ws = kernel_pool.get_public_workspace_path()
        candidate_dirs.append(primary_ws)

    # In multi-tenant environments, also discover existing workspaces under workspaces_root
    if hasattr(kernel_pool, "workspaces_root") and os.path.isdir(kernel_pool.workspaces_root):
        try:
            for entry in os.listdir(kernel_pool.workspaces_root):
                full_entry = os.path.join(kernel_pool.workspaces_root, entry)
                if os.path.isdir(full_entry):
                    candidate_dirs.append(full_entry)
                    default_sub = os.path.join(full_entry, "default")
                    if os.path.isdir(default_sub):
                        candidate_dirs.append(default_sub)
        except Exception:
            pass

    search_paths: List[str] = []
    for cdir in candidate_dirs:
        abs_cdir = os.path.abspath(cdir)
        if os.path.isdir(abs_cdir) and abs_cdir not in search_paths:
            search_paths.append(abs_cdir)

        local_dir = os.path.join(abs_cdir, ".local")
        if os.path.isdir(local_dir):
            try:
                for root, dirs, _ in os.walk(local_dir):
                    if os.path.basename(root) == "site-packages" and root not in search_paths:
                        search_paths.append(os.path.abspath(root))
            except Exception:
                pass

    resolved_ws = primary_ws or os.getcwd()
    _WS_PATHS_CACHE[cache_key] = (now, resolved_ws, search_paths)
    return resolved_ws, search_paths


def _get_cached_jedi_project(primary_ws: str, full_sys_paths: List[str]):
    key = (primary_ws, tuple(full_sys_paths))
    proj = _JEDI_PROJECTS.get(key)
    if proj is None:
        proj = jedi.Project(path=primary_ws, sys_path=full_sys_paths)
        _JEDI_PROJECTS[key] = proj
    return proj


def _inspect_object_completions(obj: Any, cache_key: str) -> List[CompletionItem]:
    cached = _OBJECT_MEMBER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    items: List[CompletionItem] = []
    try:
        names = dir(obj)
    except Exception:
        names = []

    for name in names:
        if name.startswith("_"):
            continue
        val = None
        try:
            val = getattr(obj, name)
        except Exception:
            pass

        if isinstance(val, type):
            item_type = "class"
        elif callable(val):
            item_type = "function"
        elif isinstance(val, property):
            item_type = "property"
        elif inspect.ismodule(val):
            item_type = "module"
        else:
            item_type = "property"

        doc = ""
        try:
            raw_doc = getattr(val, "__doc__", None)
            if isinstance(raw_doc, str) and raw_doc.strip():
                doc = raw_doc.strip()[:400]
        except Exception:
            pass

        items.append(
            CompletionItem(
                label=name,
                type=item_type,
                detail=f"{cache_key}.{name}",
                documentation=doc,
                insert_text=name,
            )
        )

    _OBJECT_MEMBER_CACHE[cache_key] = items
    return items


def _resolve_runtime_target(target_key: str) -> Optional[Any]:
    try:
        if target_key == "pandas.DataFrame":
            import pandas as pd
            return pd.DataFrame
        if target_key == "pandas.Series":
            import pandas as pd
            return pd.Series
        if target_key == "pandas.Series.str":
            import pandas as pd
            return pd.Series.str
        if target_key == "pandas.Series.dt":
            import pandas as pd
            return pd.Series.dt
        if target_key == "numpy.ndarray":
            import numpy as np
            return np.ndarray
        if target_key == "builtins.str":
            return str
        if target_key == "builtins.list":
            return list
        if target_key == "builtins.dict":
            return dict
        if target_key == "builtins.set":
            return set
        if target_key == "builtins.tuple":
            return tuple
        if target_key in sys.modules:
            return sys.modules[target_key]
        return importlib.import_module(target_key)
    except Exception:
        return None


def _extract_receiver_and_prefix(line_before_cursor: str) -> Optional[Tuple[str, str]]:
    """
    If line_before_cursor ends with `<receiver>.<prefix>`, extracts `(receiver, prefix)`
    while respecting nested parentheses/brackets (e.g. `print(df['Order Date'].isna().s` ->
    receiver=`df['Order Date'].isna()`, prefix=`s`).
    """
    dot_match = re.search(r"\.([a-zA-Z0-9_]*)$", line_before_cursor)
    if not dot_match:
        return None
    prefix = dot_match.group(1)
    before_dot = line_before_cursor[:dot_match.start()]
    if not before_dot:
        return None

    depth = 0
    in_quote: Optional[str] = None
    idx = len(before_dot) - 1
    while idx >= 0:
        ch = before_dot[idx]
        if in_quote:
            if ch == in_quote and (idx == 0 or before_dot[idx - 1] != "\\"):
                in_quote = None
            idx -= 1
            continue

        if ch in ("'", '"'):
            in_quote = ch
            idx -= 1
            continue

        if ch in (")", "]", "}"):
            depth += 1
            idx -= 1
            continue

        if ch in ("(", "[", "{"):
            if depth > 0:
                depth -= 1
                idx -= 1
                continue
            else:
                break

        if depth == 0:
            if re.match(r"[a-zA-Z0-9_\.]", ch):
                idx -= 1
                continue
            else:
                break
        idx -= 1

    receiver = before_dot[idx + 1:].strip()
    if not receiver:
        return None
    return receiver, prefix


def _infer_code_types(full_code: str) -> Tuple[Dict[str, str], Dict[str, str], List[CompletionItem]]:
    """
    Rapidly parses imports, variable type assignments, and user symbols from `full_code` in <0.5ms.
    """
    aliases: Dict[str, str] = {}
    var_types: Dict[str, str] = {}
    user_symbols: Dict[str, CompletionItem] = {}

    for line in full_code.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        # 1. import X as Y
        m_imp = re.match(r"^import\s+([a-zA-Z0-9_\.]+)(?:\s+as\s+([a-zA-Z0-9_]+))?", s)
        if m_imp:
            mod_name = m_imp.group(1)
            alias = m_imp.group(2) or mod_name.split(".")[0]
            aliases[alias] = mod_name
            user_symbols[alias] = CompletionItem(
                label=alias, type="module", detail=f"module {mod_name}", documentation="", insert_text=alias
            )
            continue

        # 2. from X import Y as Z
        m_from = re.match(r"^from\s+([a-zA-Z0-9_\.]+)\s+import\s+(.+)$", s)
        if m_from:
            mod_name, imports_part = m_from.group(1), m_from.group(2)
            for part in imports_part.split(","):
                part = part.strip()
                m_sym = re.match(r"^([a-zA-Z0-9_]+)(?:\s+as\s+([a-zA-Z0-9_]+))?", part)
                if m_sym:
                    sym, alias = m_sym.group(1), m_sym.group(2)
                    target_alias = alias or sym
                    if sym == "DataFrame" and mod_name.startswith("pandas"):
                        aliases[target_alias] = "pandas.DataFrame"
                    elif sym == "Series" and mod_name.startswith("pandas"):
                        aliases[target_alias] = "pandas.Series"
                    else:
                        aliases[target_alias] = f"{mod_name}.{sym}"
                    user_symbols[target_alias] = CompletionItem(
                        label=target_alias, type="module", detail=f"from {mod_name} import {sym}", documentation="", insert_text=target_alias
                    )
            continue

        # 3. def func_name(...)
        m_def = re.match(r"^(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)", s)
        if m_def:
            fname, fparams = m_def.group(1), m_def.group(2)
            user_symbols[fname] = CompletionItem(
                label=fname, type="function", detail=f"def {fname}({fparams})", documentation="", insert_text=fname
            )
            for p in fparams.split(","):
                pname = p.split("=")[0].split(":")[0].strip().lstrip("*")
                if pname and pname != "self" and pname.isidentifier():
                    user_symbols[pname] = CompletionItem(
                        label=pname, type="variable", detail="parameter", documentation="", insert_text=pname
                    )
            continue

        # 4. class ClassName
        m_cls = re.match(r"^class\s+([a-zA-Z_][a-zA-Z0-9_]*)", s)
        if m_cls:
            cname = m_cls.group(1)
            user_symbols[cname] = CompletionItem(
                label=cname, type="class", detail=f"class {cname}", documentation="", insert_text=cname
            )
            continue

        # 5. for var in ...
        m_for = re.match(r"^for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+", s)
        if m_for:
            vname = m_for.group(1)
            user_symbols[vname] = CompletionItem(
                label=vname, type="variable", detail="loop variable", documentation="", insert_text=vname
            )
            continue

        # 6. var = rhs
        m_assign = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::[^=]+)?=\s*(.+)$", s)
        if m_assign and not s.startswith("=="):
            var_name, rhs = m_assign.group(1), m_assign.group(2).strip()
            inferred = _infer_expr_type(rhs, aliases, var_types)
            if inferred:
                var_types[var_name] = inferred
            user_symbols[var_name] = CompletionItem(
                label=var_name,
                type="variable",
                detail=inferred or "variable",
                documentation="",
                insert_text=var_name,
            )

    return aliases, var_types, list(user_symbols.values())


def _infer_expr_type(expr: str, aliases: Dict[str, str], var_types: Dict[str, str]) -> Optional[str]:
    expr = expr.strip()
    if not expr:
        return None
    if expr in aliases:
        return aliases[expr]
    if expr in var_types:
        return var_types[expr]

    # Literal types
    if (expr.startswith("[") and expr.endswith("]")) or expr.startswith("list("):
        return "builtins.list"
    if (expr.startswith("{") and ":" in expr) or expr.startswith("dict("):
        return "builtins.dict"
    if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')) or expr.startswith("str("):
        return "builtins.str"
    if expr.startswith("set("):
        return "builtins.set"

    # Check DataFrame subscript: df['col'] or df["col"] -> Series, df[['a', 'b']] -> DataFrame
    m_sub = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\[(.+)\](.*)$", expr)
    if m_sub:
        base_var, inner, rest = m_sub.group(1), m_sub.group(2).strip(), m_sub.group(3).strip()
        if var_types.get(base_var) == "pandas.DataFrame":
            base_type = "pandas.DataFrame" if inner.startswith("[") else "pandas.Series"
            if not rest:
                return base_type
            if rest == ".str":
                return "pandas.Series.str"
            if rest == ".dt":
                return "pandas.Series.dt"
            m_chain = re.findall(r"\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", rest)
            if m_chain:
                last_m = m_chain[-1]
                if base_type == "pandas.Series" and last_m in _SERIES_CHAIN_METHODS:
                    return "pandas.Series"
                if base_type == "pandas.DataFrame" and last_m in _DF_CHAIN_METHODS:
                    return "pandas.DataFrame"

    # Check direct module creator or chained calls: e.g. pd.read_csv(...), np.array(...), raw.dropna()
    m_call = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)(.*)$", expr)
    if m_call:
        root, attr, rest = m_call.group(1), m_call.group(2), m_call.group(3).strip()
        root_mod = aliases.get(root)
        if root_mod == "pandas":
            if attr in _DF_CREATORS:
                return "pandas.DataFrame"
            if attr == "Series":
                return "pandas.Series"
        elif root_mod == "numpy":
            if attr in _NDARRAY_CREATORS:
                return "numpy.ndarray"

        vtype = var_types.get(root)
        if vtype == "pandas.DataFrame":
            if attr in _DF_CHAIN_METHODS:
                return "pandas.DataFrame"
            if attr in _SERIES_CHAIN_METHODS:
                return "pandas.Series"
        elif vtype == "pandas.Series":
            if attr == "str" and not rest:
                return "pandas.Series.str"
            if attr == "dt" and not rest:
                return "pandas.Series.dt"
            if attr in _SERIES_CHAIN_METHODS:
                return "pandas.Series"
        elif vtype == "numpy.ndarray":
            return "numpy.ndarray"

    return None


def _get_top_level_builtins() -> List[CompletionItem]:
    global _TOP_LEVEL_BUILTINS_CACHE
    if _TOP_LEVEL_BUILTINS_CACHE is not None:
        return _TOP_LEVEL_BUILTINS_CACHE

    items: List[CompletionItem] = []
    seen = set()
    for kw in keyword.kwlist:
        seen.add(kw)
        items.append(CompletionItem(label=kw, type="keyword", detail="Python keyword", documentation="", insert_text=kw))

    for name in dir(builtins):
        if name.startswith("_") or name in seen:
            continue
        seen.add(name)
        val = getattr(builtins, name, None)
        btype = "class" if isinstance(val, type) else ("function" if callable(val) else "variable")
        doc = ""
        raw_doc = getattr(val, "__doc__", None)
        if isinstance(raw_doc, str):
            doc = raw_doc.strip()[:300]
        items.append(CompletionItem(label=name, type=btype, detail="builtin", documentation=doc, insert_text=name))

    _TOP_LEVEL_BUILTINS_CACHE = items
    return items


def _fast_resolve_signature(full_code: str, line_before_cursor: str, aliases: Dict[str, str], var_types: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Resolves function call signature in <0.5ms using inspect.signature or AST when inside parentheses.
    """
    # Find innermost unclosed '(' on line_before_cursor
    depth = 0
    open_paren_pos = -1
    comma_count = 0
    in_quote: Optional[str] = None

    for i in range(len(line_before_cursor) - 1, -1, -1):
        ch = line_before_cursor[i]
        if in_quote:
            if ch == in_quote and (i == 0 or line_before_cursor[i - 1] != "\\"):
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
            continue
        if ch in (")", "]", "}"):
            depth += 1
        elif ch in ("[", "{"):
            if depth > 0:
                depth -= 1
        elif ch == ",":
            if depth == 0:
                comma_count += 1
        elif ch == "(":
            if depth > 0:
                depth -= 1
            else:
                open_paren_pos = i
                break

    if open_paren_pos < 0:
        return []

    before_paren = line_before_cursor[:open_paren_pos].rstrip()
    m_fn = re.search(r"([a-zA-Z_][a-zA-Z0-9_\.]*)$", before_paren)
    if not m_fn:
        return []

    fn_expr = m_fn.group(1)
    target_fn = None
    fn_short_name = fn_expr.split(".")[-1]

    if "." not in fn_expr:
        # Check builtins or user-defined functions in full_code
        if hasattr(builtins, fn_expr):
            target_fn = getattr(builtins, fn_expr)
        else:
            # Check user-defined function in full_code
            pattern = re.compile(rf"^\s*(?:async\s+)?def\s+{re.escape(fn_expr)}\s*\(([^)]*)\)", re.MULTILINE)
            m_user_def = pattern.search(full_code)
            if m_user_def:
                params_raw = m_user_def.group(1)
                params = [p.split("=")[0].split(":")[0].strip() for p in params_raw.split(",") if p.strip()]
                return [{
                    "name": fn_expr,
                    "signature": f"{fn_expr}({params_raw})",
                    "params": params,
                    "docstring": "",
                    "index": min(comma_count, max(0, len(params) - 1)),
                }]
    else:
        parts = fn_expr.rsplit(".", 1)
        recv, method_name = parts[0], parts[1]
        inferred_recv = _infer_expr_type(recv, aliases, var_types)
        if inferred_recv:
            obj = _resolve_runtime_target(inferred_recv)
            if obj is not None:
                target_fn = getattr(obj, method_name, None)

    if target_fn is not None and callable(target_fn):
        try:
            sig = inspect.signature(target_fn)
            params = [p.name for p in sig.parameters.values() if p.name != "self"]
            doc = (getattr(target_fn, "__doc__", "") or "").strip()[:400]
            return [{
                "name": fn_short_name,
                "signature": f"{fn_short_name}{sig}",
                "params": params,
                "docstring": doc,
                "index": min(comma_count, max(0, len(params) - 1)) if params else 0,
            }]
        except Exception:
            pass

    return []


def _run_jedi_sync(
    full_code: str,
    eval_line: int,
    column: int,
    primary_ws: str,
    full_sys_paths: List[str],
    need_completions: bool,
    need_signatures: bool,
) -> Tuple[List[CompletionItem], List[Dict[str, Any]]]:
    comps_out: List[CompletionItem] = []
    sigs_out: List[Dict[str, Any]] = []
    seen = set()

    with _JEDI_LOCK:
        project = _get_cached_jedi_project(primary_ws, full_sys_paths)
        script = jedi.Script(code=full_code, project=project)

        if need_completions:
            try:
                jedi_comps = script.complete(eval_line, column)
                fetch_docs = len(jedi_comps) <= 25
                for c in jedi_comps:
                    name = c.name
                    if name in seen or name.startswith("_"):
                        continue
                    seen.add(name)
                    api_type = getattr(c._name, "api_type", None) or "property"
                    doc = ""
                    if fetch_docs:
                        try:
                            doc = (c.docstring(raw=True, fast=True) or "")[:400]
                        except Exception:
                            doc = ""
                    comps_out.append(
                        CompletionItem(
                            label=name,
                            type=api_type,
                            detail=name,
                            documentation=doc,
                            insert_text=name,
                        )
                    )
            except Exception:
                pass

        if need_signatures:
            try:
                sigs = script.get_signatures(eval_line, column)
                for s in sigs:
                    sigs_out.append({
                        "name": s.name,
                        "signature": s.to_string(),
                        "params": [p.name for p in s.params] if hasattr(s, "params") else [],
                        "docstring": (s.docstring(raw=True, fast=True) or "")[:400],
                        "index": getattr(s, "index", 0),
                    })
            except Exception:
                pass

    return comps_out, sigs_out


@router.post("/complete", response_model=CompletionResponse)
async def get_completions(
    req: CompletionRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Intelligent Python Autocomplete / IntelliSense endpoint.
    Uses fast in-memory module/DataFrame/Series/ndarray introspection combined with
    cached Jedi static analysis and optional non-blocking kernel runtime introspection.
    """
    full_code, eval_line = _build_virtual_script(req.code, req.line, req.notebook_context)
    seen_labels = set()
    completions_list: List[CompletionItem] = []
    signatures_list: List[Dict[str, Any]] = []

    code_lines = req.code.split("\n")
    current_line_str = code_lines[req.line - 1] if 1 <= req.line <= len(code_lines) else ""
    line_before_cursor = current_line_str[:req.column]
    stripped_line = line_before_cursor.lstrip()

    aliases, var_types, user_symbols = _infer_code_types(full_code)

    # Check if cursor is inside unclosed parentheses for signature help
    open_parens = 0
    for ch in req.code[: sum(len(l) + 1 for l in code_lines[: req.line - 1]) + req.column]:
        if ch == "(":
            open_parens += 1
        elif ch == ")":
            open_parens = max(0, open_parens - 1)
    is_inside_parens = open_parens > 0

    if is_inside_parens:
        signatures_list = _fast_resolve_signature(full_code, line_before_cursor, aliases, var_types)

    # 1. Fast-Path Member Completion (`<receiver>.<prefix>`)
    recv_info = _extract_receiver_and_prefix(line_before_cursor)
    is_import_stmt = stripped_line.startswith(("import ", "from "))

    if recv_info is not None and not is_import_stmt:
        receiver, prefix = recv_info
        target_type = _infer_expr_type(receiver, aliases, var_types)
        if target_type:
            target_obj = _resolve_runtime_target(target_type)
            if target_obj is not None:
                raw_items = _inspect_object_completions(target_obj, target_type)
                lower_pfx = prefix.lower()
                for item in raw_items:
                    if not lower_pfx or item.label.lower().startswith(lower_pfx):
                        if item.label not in seen_labels:
                            seen_labels.add(item.label)
                            completions_list.append(item)

    # 2. Fast-Path Top-Level Identifier Completion (no dot, not import statement)
    elif recv_info is None and not is_import_stmt:
        m_id = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)$", line_before_cursor)
        prefix = m_id.group(1) if m_id else ""
        lower_pfx = prefix.lower()
        for sym in user_symbols:
            if (not lower_pfx or sym.label.lower().startswith(lower_pfx)) and sym.label not in seen_labels:
                seen_labels.add(sym.label)
                completions_list.append(sym)
        for bitem in _get_top_level_builtins():
            if (not lower_pfx or bitem.label.lower().startswith(lower_pfx)) and bitem.label not in seen_labels:
                seen_labels.add(bitem.label)
                completions_list.append(bitem)

    # 3. Cached Jedi Static Analysis Fallback (for imports, custom classes, or unresolved signatures)
    need_jedi_comps = len(completions_list) == 0
    need_jedi_sigs = is_inside_parens and len(signatures_list) == 0

    if need_jedi_comps or need_jedi_sigs:
        primary_ws, search_paths = _get_workspace_search_paths(req.session_id, current_user)
        full_sys_paths = search_paths + [p for p in sys.path if p not in search_paths]
        jedi_comps, jedi_sigs = await asyncio.to_thread(
            _run_jedi_sync,
            full_code,
            eval_line,
            req.column,
            primary_ws,
            full_sys_paths,
            need_jedi_comps,
            need_jedi_sigs,
        )
        if need_jedi_comps:
            for c in jedi_comps:
                if c.label not in seen_labels:
                    seen_labels.add(c.label)
                    completions_list.append(c)
        if need_jedi_sigs and jedi_sigs:
            signatures_list = jedi_sigs

    # 4. Non-blocking Kernel Runtime Introspection (only if static/fast analysis returned no matches and kernel is idle)
    if not completions_list and req.session_id and req.session_id in kernel_pool.sessions:
        session = kernel_pool.sessions[req.session_id]
        if session.is_running and session.kc and not session._lock.locked():
            try:
                cursor_pos = sum(len(l) + 1 for l in code_lines[: req.line - 1]) + req.column
                msg_id = session.kc.complete(req.code, cursor_pos)
                deadline = time.monotonic() + 0.06
                while time.monotonic() < deadline:
                    rem = max(0.01, deadline - time.monotonic())
                    reply = await asyncio.wait_for(session.kc.get_shell_msg(timeout=rem), timeout=rem + 0.01)
                    if reply and reply.get("parent_header", {}).get("msg_id") == msg_id:
                        if "content" in reply and "matches" in reply["content"]:
                            for match in reply["content"]["matches"][:50]:
                                clean_match = match.split(".")[-1]
                                if clean_match and not clean_match.startswith("_") and clean_match not in seen_labels:
                                    seen_labels.add(clean_match)
                                    completions_list.append(
                                        CompletionItem(
                                            label=clean_match,
                                            type="variable",
                                            detail="Runtime Object (Active Kernel)",
                                            documentation="Inspected from running Python kernel state.",
                                            insert_text=clean_match,
                                        )
                                    )
                        break
            except Exception:
                pass

    return CompletionResponse(completions=completions_list, signatures=signatures_list)


@router.post("/signatures")
async def get_signatures(
    req: SignatureRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """Returns signature help and parameter information for the current function call."""
    full_code, eval_line = _build_virtual_script(req.code, req.line, req.notebook_context)
    code_lines = req.code.split("\n")
    current_line_str = code_lines[req.line - 1] if 1 <= req.line <= len(code_lines) else ""
    line_before_cursor = current_line_str[:req.column]

    aliases, var_types, _ = _infer_code_types(full_code)
    fast_sigs = _fast_resolve_signature(full_code, line_before_cursor, aliases, var_types)
    if fast_sigs:
        return {"signatures": fast_sigs}

    primary_ws, search_paths = _get_workspace_search_paths(req.session_id, current_user)
    full_sys_paths = search_paths + [p for p in sys.path if p not in search_paths]
    _, results = await asyncio.to_thread(
        _run_jedi_sync,
        full_code,
        eval_line,
        req.column,
        primary_ws,
        full_sys_paths,
        False,
        True,
    )
    return {"signatures": results}



@router.post("/diagnostics", response_model=DiagnosticsResponse)
async def get_diagnostics(
    req: DiagnosticsRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Performs real Python syntax error validation and unresolved module checking.
    Guarantees:
    - NO red squiggly underlines on valid code (numpy, pandas, user variables, etc.)
    - NO red squiggly underlines on transient typing expressions like 'np.' or 'pd.'
    - ACCURATE detection of installed packages in workspace site-packages or user environment.
    - ACCURATE red squiggly underlines on genuine syntax errors and missing packages.
    """
    code = req.code
    if not code.strip():
        return DiagnosticsResponse(diagnostics=[])

    lines = code.split("\n")
    diagnostics: List[DiagnosticItem] = []

    # Detect if user is currently typing an incomplete expression ending with a dot or open delimiter
    is_incomplete_expression = False
    for l in lines:
        stripped = l.rstrip()
        if stripped.endswith((".", "(", "[", "{", ",", "+", "-", "*", "/", "%", "=", ":")):
            is_incomplete_expression = True
            break

    # 1. Genuine Syntax Error Detection via Python's AST parser
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        err_line = e.lineno or 1
        # Suppress transient syntax errors on the line currently being typed if it ends with a dot or operator
        line_content = lines[err_line - 1] if err_line <= len(lines) else ""
        if not (is_incomplete_expression and line_content.rstrip().endswith(".")):
            from_col = max(0, (e.offset or 1) - 1)
            to_col = max(from_col + 1, e.end_offset or (from_col + 1))
            diagnostics.append(
                DiagnosticItem(
                    from_line=err_line,
                    from_col=from_col,
                    to_line=e.end_lineno or err_line,
                    to_col=to_col,
                    message=f"Syntax Error: {e.msg or 'Invalid Python syntax'}",
                    severity="error",
                )
            )
        return DiagnosticsResponse(diagnostics=diagnostics)

    primary_ws, search_paths = _get_workspace_search_paths(req.session_id, current_user)

    def is_module_available(pkg_name: str) -> bool:
        """Determines if a root module exists in builtins, global python, or workspace search paths."""
        if pkg_name in sys.builtin_module_names:
            return True
        try:
            if importlib.util.find_spec(pkg_name) is not None:
                return True
        except Exception:
            pass
        try:
            if importlib.machinery.PathFinder.find_spec(pkg_name, search_paths) is not None:
                return True
        except Exception:
            pass
        return False

    # 2. Missing Module Import Detection
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if not is_module_available(root_pkg):
                    diagnostics.append(
                        DiagnosticItem(
                            from_line=node.lineno,
                            from_col=node.col_offset,
                            to_line=getattr(node, "end_lineno", node.lineno),
                            to_col=getattr(node, "end_col_offset", node.col_offset + len(alias.name) + 7),
                            message=f"Unresolved import '{alias.name}': No module named '{root_pkg}' found in active Python runtime.",
                            severity="error",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                if not is_module_available(root_pkg):
                    diagnostics.append(
                        DiagnosticItem(
                            from_line=node.lineno,
                            from_col=node.col_offset,
                            to_line=getattr(node, "end_lineno", node.lineno),
                            to_col=getattr(node, "end_col_offset", node.col_offset + len(node.module) + 5),
                            message=f"Unresolved import '{node.module}': No module named '{root_pkg}' found in active Python runtime.",
                            severity="error",
                        )
                    )

    return DiagnosticsResponse(diagnostics=diagnostics)

