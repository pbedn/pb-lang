from __future__ import annotations

"""Abstract‑syntax tree (AST) node definitions for the PB language.
This module is consumed by the lexer, parser, type‑checker and code‑generator.
It strives to be **complete** – any syntactic construct recognised by the parser
should have a corresponding dataclass here so that downstream passes can rely
on a single, strongly‑typed representation.

Conventions
-----------
* Forward‑references are written as *string literals* (or enabled via
  ``from __future__ import annotations``) so that the file can be imported
  without cyclical issues.
* Every concrete node belongs to exactly one of the two root union aliases
  ``Stmt`` or ``Expr``.
* Keep the nodes *minimal*: only store the fields required by later stages;
  helper attributes (e.g. inferred types) live in those later passes.
"""

from dataclasses import dataclass
from typing import List, Tuple, Union, Optional, Set

# === Root module ===
@dataclass
class Program:
    body: List["Stmt"]

# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class FunctionDef:
    """``def name(param: type, ...) -> return_type: ...``"""

    name: str
    params: List[Tuple[str, str]]  # (parameter name, static type)
    body: List["Stmt"]
    return_type: Optional[str]  # ``None`` → ``void`` / no explicit return
    globals_declared: Optional[Set[str]] = None  # names seen in a ``global`` stmt


@dataclass
class ReturnStmt:
    value: "Expr"  # use ``Literal(None)`` for an empty ``return``


@dataclass
class ClassDef:
    name: str
    base: Optional[str]  # ``None`` means *no inheritance*
    fields: List["VarDecl"]
    methods: List["FunctionDef"]


@dataclass
class GlobalStmt:
    names: List[str]


@dataclass
class VarDecl:
    """``x: int = 5`` – *declaration* and *initialiser* in one."""

    name: str
    declared_type: str
    value: "Expr"


@dataclass
class IfStmt:
    condition: "Expr"
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None


@dataclass
class WhileStmt:
    condition: "Expr"
    body: List["Stmt"]


@dataclass
class ForStmt:
    var_name: str
    iterable: "Expr"  # currently only ``range`` is supported
    body: List["Stmt"]


@dataclass
class AssignStmt:
    target: "Expr"  # Identifier | AttributeExpr | IndexExpr
    value: "Expr"


@dataclass
class AugAssignStmt:
    target: "Expr"
    op: str  # ``+=`` → "+", etc.  see parser for mapping
    value: "Expr"


@dataclass
class AssertStmt:
    condition: "Expr"


@dataclass
class BreakStmt:
    pass


@dataclass
class ContinueStmt:
    pass


@dataclass
class PassStmt:
    pass


# --- Exception handling (planned feature, tokens already reserved) ----------
@dataclass
class RaiseStmt:
    exception: "Expr"


@dataclass
class TryExceptStmt:
    try_body: List["Stmt"]
    except_var: Optional[str]  # name after ``except RuntimeError as e``
    except_body: List["Stmt"]


# --- Imports (planned feature) ---------------------------------------------
@dataclass
class ImportStmt:
    module: str  # simple absolute import only


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class Identifier:
    name: str


@dataclass
class Literal:
    value: Union[int, float, str, bool, None]


@dataclass
class BinOp:
    left: "Expr"
    op: str  # e.g. "+", "is", "and", "//", ...
    right: "Expr"


@dataclass
class UnaryOp:
    op: str  # "-" or "not"
    operand: "Expr"


@dataclass
class CallExpr:
    func: "Expr"
    args: List["Expr"]


@dataclass
class AttributeExpr:
    obj: "Expr"
    attr: str


@dataclass
class IndexExpr:
    base: "Expr"
    index: "Expr"
    elem_type: Optional[str] = None  # filled in by type‑checker


@dataclass
class ListExpr:
    elements: List["Expr"]
    elem_type: Optional[str] = None  # filled in by type‑checker


@dataclass
class DictExpr:
    pairs: List[Tuple["Expr", "Expr"]]


# ---------------------------------------------------------------------------
# Union aliases – the public surface of the AST module
# ---------------------------------------------------------------------------

Stmt = Union[
    FunctionDef,
    ReturnStmt,
    ClassDef,
    GlobalStmt,
    VarDecl,
    IfStmt,
    WhileStmt,
    ForStmt,
    AssignStmt,
    AugAssignStmt,
    AssertStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    RaiseStmt,
    TryExceptStmt,
    ImportStmt,
]

Expr = Union[
    Identifier,
    Literal,
    BinOp,
    UnaryOp,
    CallExpr,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
]
