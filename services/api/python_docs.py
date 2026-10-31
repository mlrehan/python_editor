"""
Structured documentation for Python callables and objects, built only from real introspection:
inspect.signature (parameter kinds, defaults, annotations), typing.get_type_hints where it resolves,
and the object's own docstring parsed into sections (NumPy style as used by pandas, NumPy, SciPy,
scikit-learn, Matplotlib and Seaborn; Google style; reST :param: fields). Nothing is invented: a
section is present only when the docstring or signature provides it.
"""
import inspect
import re
import textwrap
from typing import Any, Dict, List, Optional

_DOC_CACHE: Dict[Any, Dict[str, Any]] = {}
_MAX_CACHE = 2048

# NumPy-style section names -> normalized keys
_NUMPY_SECTIONS = {
    "parameters": "parameters",
    "params": "parameters",
    "other parameters": "parameters",
    "keyword arguments": "parameters",
    "returns": "returns",
    "return": "returns",
    "yields": "returns",
    "raises": "raises",
    "warns": "raises",
    "see also": "see_also",
    "notes": "notes",
    "examples": "examples",
    "example": "examples",
    "attributes": "attributes",
    "methods": "methods",
    "references": "references",
    "warnings": "notes",
}
_GOOGLE_SECTIONS = {
    "args": "parameters",
    "arguments": "parameters",
    "parameters": "parameters",
    "params": "parameters",
    "keyword args": "parameters",
    "kwargs": "parameters",
    "returns": "returns",
    "return": "returns",
    "yields": "returns",
    "raises": "raises",
    "examples": "examples",
    "example": "examples",
    "note": "notes",
    "notes": "notes",
    "see also": "see_also",
    "attributes": "attributes",
}


def _type_text(annotation: Any) -> Optional[str]:
    if annotation is inspect.Parameter.empty or annotation is inspect.Signature.empty:
        return None
    if isinstance(annotation, str):
        return annotation
    text = inspect.formatannotation(annotation)
    return text or None


def _split_numpy_sections(doc: str) -> Dict[str, List[str]]:
    """Splits a dedented docstring at NumPy headers ("Parameters" over a line of dashes)."""
    lines = doc.split("\n")
    sections: Dict[str, List[str]] = {"_intro": []}
    current = "_intro"
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        header = line.strip().lower()
        if header in _NUMPY_SECTIONS and re.fullmatch(r"\s*-{3,}\s*", nxt or ""):
            current = _NUMPY_SECTIONS[header]
            sections.setdefault(current, [])
            i += 2
            continue
        sections.setdefault(current, []).append(line)
        i += 1
    return sections


def _split_google_sections(doc: str) -> Dict[str, List[str]]:
    lines = doc.split("\n")
    sections: Dict[str, List[str]] = {"_intro": []}
    current = "_intro"
    for line in lines:
        m = re.fullmatch(r"\s*([A-Za-z][A-Za-z ]*):\s*", line)
        if m and m.group(1).strip().lower() in _GOOGLE_SECTIONS and not line.startswith((" " * 8,)):
            current = _GOOGLE_SECTIONS[m.group(1).strip().lower()]
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _parse_numpy_items(lines: List[str]) -> List[Dict[str, Optional[str]]]:
    """'name : type' lines with indented descriptions (NumPy Parameters / Returns / Raises)."""
    items: List[Dict[str, Optional[str]]] = []
    base_indent: Optional[int] = None
    for line in lines:
        if not line.strip():
            if items:
                items[-1]["description"] = (items[-1]["description"] or "") + "\n"
            continue
        indent = len(line) - len(line.lstrip())
        if base_indent is None:
            base_indent = indent
        if indent <= base_indent:
            head = line.strip()
            if " : " in head or head.endswith(" :"):
                name, _, typ = head.partition(" :")
                items.append({"name": name.strip(), "type": typ.strip() or None, "description": ""})
            elif ":" in head and not head.startswith(("http", "``")) and re.match(r"^[\w*, ]+:", head):
                name, _, typ = head.partition(":")
                items.append({"name": name.strip(), "type": typ.strip() or None, "description": ""})
            else:
                # Returns sections often list only the type
                items.append({"name": None, "type": head, "description": ""})
        elif items:
            items[-1]["description"] = (items[-1]["description"] or "") + line.strip() + " "
    for it in items:
        it["description"] = re.sub(r"[ \t]+\n", "\n", (it["description"] or "")).strip() or None
    return items


def _parse_google_items(lines: List[str]) -> List[Dict[str, Optional[str]]]:
    items: List[Dict[str, Optional[str]]] = []
    base_indent: Optional[int] = None
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if base_indent is None:
            base_indent = indent
        m = re.match(r"^\s*(\*{0,2}[\w.]+)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$", line)
        if indent <= base_indent and m:
            items.append({"name": m.group(1), "type": m.group(2), "description": m.group(3).strip()})
        elif items:
            items[-1]["description"] = ((items[-1]["description"] or "") + " " + line.strip()).strip()
    return items


def _parse_rest_fields(doc: str) -> Dict[str, Any]:
    params: Dict[str, Dict[str, Optional[str]]] = {}
    returns = None
    for m in re.finditer(r"^\s*:param\s+(?:([\w\[\], .]+)\s+)?(\w+):\s*(.*)$", doc, re.MULTILINE):
        params[m.group(2)] = {"name": m.group(2), "type": m.group(1), "description": m.group(3).strip()}
    for m in re.finditer(r"^\s*:type\s+(\w+):\s*(.*)$", doc, re.MULTILINE):
        params.setdefault(m.group(1), {"name": m.group(1), "type": None, "description": None})["type"] = m.group(2).strip()
    m = re.search(r"^\s*:returns?:\s*(.*)$", doc, re.MULTILINE)
    if m:
        returns = [{"name": None, "type": None, "description": m.group(1).strip()}]
    m = re.search(r"^\s*:rtype:\s*(.*)$", doc, re.MULTILINE)
    if m:
        returns = returns or [{"name": None, "type": None, "description": None}]
        returns[0]["type"] = m.group(1).strip()
    return {"parameters": list(params.values()), "returns": returns}


def _clean_block(lines: List[str]) -> Optional[str]:
    text = textwrap.dedent("\n".join(lines)).strip("\n")
    return text.strip() or None


def _see_also(lines: List[str]) -> List[str]:
    names: List[str] = []
    for line in lines:
        head = line.strip()
        if not head or line.startswith(("    ", "\t")) and not re.match(r"^\s{0,4}[\w.]+", line):
            continue
        m = re.match(r"^\s*([\w.]+(?:\s*,\s*[\w.]+)*)\s*(?::.*)?$", line)
        if m and (len(line) - len(line.lstrip())) <= 4:
            names.extend(n.strip() for n in m.group(1).split(","))
    return [n for n in dict.fromkeys(names) if n][:20]


def parse_docstring(doc: str) -> Dict[str, Any]:
    """Splits a docstring into summary, description and named sections."""
    doc = inspect.cleandoc(doc or "")
    if not doc:
        return {}
    is_numpy = bool(re.search(r"^\s*[A-Za-z ]+\n\s*-{3,}\s*$", doc, re.MULTILINE))
    if is_numpy:
        sections = _split_numpy_sections(doc)
        parse_items = _parse_numpy_items
    else:
        sections = _split_google_sections(doc)
        parse_items = _parse_google_items

    intro = _clean_block(sections.get("_intro", [])) or ""
    # reST field lists live in the intro when the docstring has no sections
    rest = _parse_rest_fields(intro) if ":param" in intro or ":return" in intro else None
    if rest:
        intro = re.split(r"^\s*:(?:param|type|returns?|rtype|raises?)\b", intro, maxsplit=1, flags=re.MULTILINE)[0].strip()

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", intro) if p.strip()]
    summary = paragraphs[0] if paragraphs else None
    description = "\n\n".join(paragraphs[1:]) or None

    out: Dict[str, Any] = {"summary": summary, "description": description}
    params = parse_items(sections["parameters"]) if "parameters" in sections else (rest or {}).get("parameters") or []
    out["parameters"] = [p for p in params if p.get("name")]
    returns = parse_items(sections["returns"]) if "returns" in sections else (rest or {}).get("returns")
    if returns and not is_numpy:
        # Google style "Returns:  str: the result." names the type, not a variable
        returns = [{"name": None, "type": r.get("type") or r.get("name"), "description": r.get("description")} for r in returns]
    out["returns"] = returns or []
    out["raises"] = parse_items(sections["raises"]) if "raises" in sections else []
    out["see_also"] = _see_also(sections["see_also"]) if "see_also" in sections else []
    out["notes"] = _clean_block(sections["notes"]) if "notes" in sections else None
    out["examples"] = _clean_block(sections["examples"]) if "examples" in sections else None
    return out


def _signature_params(obj: Any) -> List[Dict[str, Optional[str]]]:
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return []
    hints: Dict[str, Any] = {}
    try:
        import typing

        hints = typing.get_type_hints(obj)
    except Exception:
        hints = {}
    params = []
    for p in sig.parameters.values():
        if p.name in ("self", "cls"):
            continue
        kind = {
            p.VAR_POSITIONAL: "*args",
            p.VAR_KEYWORD: "**kwargs",
            p.KEYWORD_ONLY: "keyword-only",
            p.POSITIONAL_ONLY: "positional-only",
        }.get(p.kind, "positional or keyword")
        annotation = hints.get(p.name, p.annotation)
        params.append({
            "name": ("*" if p.kind == p.VAR_POSITIONAL else "**" if p.kind == p.VAR_KEYWORD else "") + p.name,
            "kind": kind,
            "annotation": _type_text(annotation),
            "default": None if p.default is p.empty else repr(p.default),
        })
    return params


def build_doc(obj: Any, name: Optional[str] = None) -> Dict[str, Any]:
    """Structured documentation for `obj` (function, method, class, module or value)."""
    try:
        key = (id(obj), name)
        if key in _DOC_CACHE:
            return _DOC_CACHE[key]
    except Exception:
        key = None

    qualname = getattr(obj, "__qualname__", None) or getattr(obj, "__name__", None) or type(obj).__name__
    module = getattr(obj, "__module__", None)
    display = name or getattr(obj, "__name__", None) or qualname
    kind = (
        "class" if inspect.isclass(obj)
        else "module" if inspect.ismodule(obj)
        else "method" if inspect.ismethod(obj) or ("." in str(qualname) and callable(obj))
        else "function" if callable(obj)
        else "value"
    )

    signature = None
    return_annotation = None
    if callable(obj) and not inspect.ismodule(obj):
        try:
            sig = inspect.signature(obj)
            sig = sig.replace(parameters=[p for p in sig.parameters.values() if p.name not in ("self", "cls")])
            signature = f"{display}{sig}"
            return_annotation = _type_text(sig.return_annotation)
        except (TypeError, ValueError):
            signature = None

    raw_doc = inspect.getdoc(obj) if not isinstance(obj, (int, float, str, bytes, bool)) else None
    parsed = parse_docstring(raw_doc or "")

    # Merge signature facts (defaults, annotations, kinds) with the docstring's descriptions
    by_name = {}
    for p in parsed.get("parameters", []):
        for single in str(p["name"]).split(","):
            by_name[single.strip().lstrip("*")] = p
    params = []
    sig_params = _signature_params(obj) if callable(obj) else []
    for sp in sig_params:
        documented = by_name.pop(sp["name"].lstrip("*"), None) or {}
        params.append({
            "name": sp["name"],
            "kind": sp["kind"],
            "type": sp["annotation"] or documented.get("type"),
            "default": sp["default"],
            "description": documented.get("description"),
        })
    # Parameters described in the docstring but hidden behind **kwargs in the signature
    for leftover in {id(v): v for v in by_name.values()}.values():
        params.append({"name": leftover.get("name"), "kind": "documented", "type": leftover.get("type"),
                       "default": None, "description": leftover.get("description")})

    returns = parsed.get("returns") or []
    if return_annotation and not any(r.get("type") for r in returns):
        returns = [{"name": None, "type": return_annotation, "description": (returns[0].get("description") if returns else None)}]

    doc = {
        "name": display,
        "qualname": f"{module}.{qualname}" if module and module != "builtins" else str(qualname),
        "kind": kind,
        "signature": signature,
        "summary": parsed.get("summary"),
        "description": parsed.get("description"),
        "parameters": params,
        "returns": returns,
        "raises": parsed.get("raises") or [],
        "examples": parsed.get("examples"),
        "notes": parsed.get("notes"),
        "see_also": parsed.get("see_also") or [],
        "has_docstring": bool(raw_doc),
    }
    if key is not None:
        if len(_DOC_CACHE) > _MAX_CACHE:
            _DOC_CACHE.clear()
        _DOC_CACHE[key] = doc
    return doc


def doc_from_text(name: str, signature: Optional[str], docstring: str, param_strings: List[str]) -> Dict[str, Any]:
    """Structured doc when only text is available (e.g. Jedi's static analysis of user code)."""
    parsed = parse_docstring(docstring or "")
    by_name = {str(p["name"]).lstrip("*"): p for p in parsed.get("parameters", [])}
    params = []
    for ps in param_strings:
        m = re.match(r"^(\*{0,2}[\w]+)\s*(?::\s*([^=]+?))?\s*(?:=\s*(.+))?$", ps.strip())
        if not m:
            continue
        pname = m.group(1)
        documented = by_name.get(pname.lstrip("*"), {})
        params.append({
            "name": pname,
            "kind": "**kwargs" if pname.startswith("**") else "*args" if pname.startswith("*") else "positional or keyword",
            "type": (m.group(2) or "").strip() or documented.get("type"),
            "default": (m.group(3) or "").strip() or None,
            "description": documented.get("description"),
        })
    return {
        "name": name,
        "qualname": name,
        "kind": "function",
        "signature": signature,
        "summary": parsed.get("summary"),
        "description": parsed.get("description"),
        "parameters": params,
        "returns": parsed.get("returns") or [],
        "raises": parsed.get("raises") or [],
        "examples": parsed.get("examples"),
        "notes": parsed.get("notes"),
        "see_also": parsed.get("see_also") or [],
        "has_docstring": bool(docstring),
    }
