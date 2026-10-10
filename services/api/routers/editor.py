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


def _get_workspace_search_paths(
    session_id: Optional[str] = None,
    current_user: Optional[Union[User, GuestUser]] = None,
) -> Tuple[str, List[str]]:
    """
    Resolves the active workspace directory and all Python package search paths,
    including the user workspace root, .local/site-packages, and multi-tenant paths.
    """
    candidate_dirs: List[str] = []
    primary_ws: Optional[str] = None

    if session_id:
        session = kernel_pool.get_session(session_id)
        if session and session.workspace_dir:
            primary_ws = session.workspace_dir
            candidate_dirs.append(primary_ws)

    if not primary_ws and current_user:
        target_uid = f"guest_{current_user.guest_token}" if getattr(current_user, "is_guest", False) else getattr(current_user, "id", "public")
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

    return primary_ws or os.getcwd(), search_paths


@router.post("/complete", response_model=CompletionResponse)
async def get_completions(
    req: CompletionRequest,
    current_user: Union[User, GuestUser] = Depends(get_current_user_or_guest),
):
    """
    Intelligent Python Autocomplete / IntelliSense endpoint.
    Uses Jedi static analysis combined with optional active kernel runtime introspection.
    """
    full_code, eval_line = _build_virtual_script(req.code, req.line, req.notebook_context)
    seen_labels = set()
    completions_list: List[CompletionItem] = []
    signatures_list: List[Dict[str, Any]] = []

    primary_ws, search_paths = _get_workspace_search_paths(req.session_id, current_user)
    full_sys_paths = search_paths + [p for p in sys.path if p not in search_paths]

    # 1. Static Analysis via Jedi
    try:
        project = jedi.Project(path=primary_ws, sys_path=full_sys_paths)
        script = jedi.Script(code=full_code, project=project)
        jedi_comps = script.complete(eval_line, req.column)
        for c in jedi_comps:
            if c.name in seen_labels:
                continue
            seen_labels.add(c.name)
            doc = c.docstring(raw=True) if hasattr(c, "docstring") else ""
            completions_list.append(
                CompletionItem(
                    label=c.name,
                    type=c.type or "property",
                    detail=c.description or "",
                    documentation=doc[:600] if doc else "",
                    insert_text=c.name,
                )
            )

        # Get signature help if inside a function call parenthesis
        try:
            sigs = script.get_signatures(eval_line, req.column)
            for s in sigs:
                signatures_list.append({
                    "name": s.name,
                    "signature": s.to_string(),
                    "params": [p.name for p in s.params] if hasattr(s, "params") else [],
                    "docstring": (s.docstring(raw=True) or "")[:400],
                    "index": getattr(s, "index", 0),
                })
        except Exception:
            pass

    except Exception:
        pass

    # 2. Kernel Runtime Introspection (if active session provided)
    if req.session_id and req.session_id in kernel_pool.sessions:
        session = kernel_pool.sessions[req.session_id]
        if session.is_running and session.kc:
            try:
                # Query IPyKernel complete_request with 500ms timeout
                session.kc.complete(req.code, req.column)
                reply = await asyncio.wait_for(session.kc.get_shell_msg(timeout=0.5), timeout=0.6)
                if reply and "content" in reply and "matches" in reply["content"]:
                    for match in reply["content"]["matches"][:50]:
                        clean_match = match.split(".")[-1]
                        if clean_match and clean_match not in seen_labels:
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
    results = []
    primary_ws, search_paths = _get_workspace_search_paths(req.session_id, current_user)
    full_sys_paths = search_paths + [p for p in sys.path if p not in search_paths]

    try:
        project = jedi.Project(path=primary_ws, sys_path=full_sys_paths)
        script = jedi.Script(code=full_code, project=project)
        sigs = script.get_signatures(eval_line, req.column)
        for s in sigs:
            results.append({
                "name": s.name,
                "signature": s.to_string(),
                "params": [p.name for p in s.params] if hasattr(s, "params") else [],
                "docstring": (s.docstring(raw=True) or "")[:500],
                "index": getattr(s, "index", 0),
            })
    except Exception:
        pass
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

