import os
import sys
import ast
import re
import importlib.util
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import jedi

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


@router.post("/complete", response_model=CompletionResponse)
async def get_completions(req: CompletionRequest):
    """
    Intelligent Python Autocomplete / IntelliSense endpoint.
    Uses Jedi static analysis combined with optional active kernel runtime introspection.
    """
    full_code, eval_line = _build_virtual_script(req.code, req.line, req.notebook_context)
    seen_labels = set()
    completions_list: List[CompletionItem] = []
    signatures_list: List[Dict[str, Any]] = []

    # 1. Static Analysis via Jedi
    try:
        script = jedi.Script(code=full_code)
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

    except Exception as e:
        # Fallback or pass
        pass

    # 2. Kernel Runtime Introspection (if active session provided)
    if req.session_id and req.session_id in kernel_pool.sessions:
        session = kernel_pool.sessions[req.session_id]
        if session.is_running and session.kc:
            try:
                # Query IPyKernel complete_request with 500ms timeout
                msg_id = session.kc.complete(req.code, req.column)
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
async def get_signatures(req: SignatureRequest):
    """Returns signature help and parameter information for the current function call."""
    full_code, eval_line = _build_virtual_script(req.code, req.line, req.notebook_context)
    results = []
    try:
        script = jedi.Script(code=full_code)
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
async def get_diagnostics(req: DiagnosticsRequest):
    """
    Performs real Python syntax error validation and unresolved module checking.
    Guarantees:
    - NO red squiggly underlines on valid code (numpy, pandas, user variables, etc.)
    - NO red squiggly underlines on transient typing expressions like 'np.' or 'pd.'
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

    # 2. Missing Module Import Detection
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                # Check active Python environment
                if root_pkg not in sys.builtin_module_names:
                    try:
                        spec = importlib.util.find_spec(root_pkg)
                    except Exception:
                        spec = None
                    if spec is None:
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
                if root_pkg not in sys.builtin_module_names:
                    try:
                        spec = importlib.util.find_spec(root_pkg)
                    except Exception:
                        spec = None
                    if spec is None:
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

