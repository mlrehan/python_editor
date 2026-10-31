"""
Runtime introspection of a user's kernel for the editor (IntelliSense), without running user code.

A small helper module is installed into the kernel's sys.modules (never into the user's namespace)
and called through `user_expressions` of a silent execute request, so it leaves no history, does not
change the execution count and produces no output. It only *reads* the namespace:
  - names are looked up in the namespace dict; attribute chains only through objects' __dict__, so
    properties and __getattr__ are never triggered;
  - DataFrame columns and dtypes are read from pandas objects that already exist (pandas is never
    imported by the helper; if the user has not imported it, there is no DataFrame to inspect).
"""
import json

HELPER_MODULE = "_pcs_introspect"

HELPER_SOURCE = r'''
import json as _json
import sys as _sys

_SKIP = {"In", "Out", "exit", "quit", "get_ipython", "open"}


def _lookup(ns, expr):
    parts = expr.split(".")
    if not parts or parts[0] not in ns:
        return None, "missing"
    obj = ns[parts[0]]
    for part in parts[1:]:
        attrs = getattr(obj, "__dict__", None)
        if not isinstance(attrs, dict) or part not in attrs:
            return None, "unresolved"
        obj = attrs[part]
    return obj, None


def _label(col):
    if isinstance(col, tuple):
        return " / ".join(str(c) for c in col)
    return str(col)


def columns(ns, expr):
    obj, err = _lookup(ns, expr)
    if err:
        return {"error": err}
    pd = _sys.modules.get("pandas")
    if pd is None or not isinstance(obj, pd.DataFrame):
        return {"error": "not_dataframe", "type": type(obj).__module__ + "." + type(obj).__qualname__}
    cols = obj.columns
    dtypes = list(obj.dtypes)
    items = []
    for i, col in enumerate(cols):
        items.append({
            "label": _label(col),
            "key": repr(col),
            "is_str": isinstance(col, str),
            "dtype": str(dtypes[i]) if i < len(dtypes) else "",
        })
    return {
        "kind": "DataFrame",
        "columns": items,
        "shape": list(obj.shape),
        "multiindex": isinstance(cols, pd.MultiIndex),
    }


def namespace(ns):
    out = {}
    for name, value in list(ns.items()):
        if name.startswith("_") or name in _SKIP:
            continue
        t = type(value)
        if t.__name__ == "module" and t.__module__ == "builtins":
            out[name] = "module:" + getattr(value, "__name__", name)  # e.g. "module:numpy"
        else:
            out[name] = t.__module__ + "." + t.__qualname__
    return out


def run(ns, request):
    try:
        if request.get("kind") == "columns":
            result = columns(ns, request["expr"])
        else:
            result = namespace(ns)
    except Exception as exc:
        result = {"error": "failed", "detail": repr(exc)[:200]}
    return _json.dumps(result, default=str)
'''

# One expression statement: installs the helper module once per kernel, defines no user names
SETUP_CODE = (
    "__import__('sys').modules.get(%r) or exec(compile(%r, '<pcs-introspect>', 'exec'), "
    "__import__('sys').modules.setdefault(%r, __import__('types').ModuleType(%r)).__dict__)"
    % (HELPER_MODULE, HELPER_SOURCE, HELPER_MODULE, HELPER_MODULE)
)


def request_expression(request: dict) -> str:
    """The user_expressions entry that calls the helper with `request` (a JSON-safe dict)."""
    return "__import__('sys').modules[%r].run(globals(), __import__('json').loads(%r))" % (
        HELPER_MODULE,
        json.dumps(request),
    )
