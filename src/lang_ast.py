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
    body: List[Stmt]

# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class FunctionDef:
    """``def name(param: type, ...) -> return_type: ...``"""

    name: str
    params: List[Tuple[str, str]]                # (parameter name, static type)
    body: List[Stmt]
    return_type: Optional[str]                   # None => void
    globals_declared: Optional[Set[str]] = None  #  filled in by parser/type-checker


@dataclass
class ClassDef:
    name: str
    base: Optional[str]             # single inheritance only
    fields: List["VarDecl"]         # field decls (VarDecl) and methods (FunctionDef)
    methods: List["FunctionDef"]


@dataclass
class GlobalStmt:
    names: List[str]


@dataclass
class VarDecl:
    name: str
    declared_type: str
    value: Expr


@dataclass
class AssignStmt:
    target: Expr                  # Identifier | AttributeExpr | IndexExpr
    value: Expr


@dataclass
class AugAssignStmt:
    target: Expr
    op: str                         # "+=", "-=", etc.
    value: Expr


@dataclass
class IfStmt:
    condition: Expr
    then_body: List[Stmt]
    elif_blocks: List[ElifStmt]
    else_body: Optional[List[Stmt]] = None


@dataclass
class ElifStmt:
    condition: Expr
    body: List[Stmt]


@dataclass
class WhileStmt:
    condition: Expr
    body: List[Stmt]
    else_body: Optional[List[Stmt]] = None


@dataclass
class ForStmt:
    var_name: str
    iterable: Expr             # e.g. range(...)
    body: List[Stmt]


@dataclass
class TryExceptStmt:
    try_body: List[Stmt]
    except_blocks: List[ExceptBlock]


@dataclass
class ExceptBlock:
    exc_type: Optional[str]      # class name
    alias: Optional[str]         # "as" name
    body: List[Stmt]


@dataclass
class RaiseStmt:
    exception: Expr


@dataclass
class ReturnStmt:
    value: Optional[Expr]        # None means no expression


@dataclass
class AssertStmt:
    condition: Expr


@dataclass
class BreakStmt:
    pass


@dataclass
class ContinueStmt:
    pass


@dataclass
class PassStmt:
    pass


@dataclass
class ExprStmt:
    expr: Expr                  # an expression used as a statement


# --- Imports (planned feature) ---------------------------------------------
@dataclass
class ImportStmt:
    module: List[str]


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class Identifier:
    name: str


@dataclass
class Literal:
    raw: str                     # raw lexeme (underscores stripped)
    # parsing into int/float happens later in a dedicated pass


@dataclass
class StringLiteral:
    value: str
    is_fstring: bool             # True if f"...", else False


@dataclass
class BinOp:
    left: Expr
    op: str                      # "+", "==", "is", "//", "and", etc.
    right: Expr


@dataclass
class UnaryOp:
    op: str                      # "-" or "not"
    operand: Expr


@dataclass
class CallExpr:
    func: Expr
    args: List[Expr]


@dataclass
class AttributeExpr:
    obj: Expr
    attr: str


@dataclass
class IndexExpr:
    base: Expr
    index: Expr
    elem_type: Optional[str] = None  # filled in by type‑checker


@dataclass
class ListExpr:
    elements: List[Expr]
    elem_type: Optional[str] = None  # filled in by type‑checker


@dataclass
class DictExpr:
    keys: List[Expr]
    values: List[Expr]


# ---------------------------------------------------------------------------
# Union aliases – the public surface of the AST module
# ---------------------------------------------------------------------------

Stmt = Union[
    FunctionDef,
    ClassDef,
    GlobalStmt,
    VarDecl,
    AssignStmt,
    AugAssignStmt,
    IfStmt,
    ElifStmt,
    WhileStmt,
    ForStmt,
    TryExceptStmt,
    ExceptBlock,
    RaiseStmt,
    ReturnStmt,
    AssertStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    ExprStmt,
    ImportStmt,
]

Expr = Union[
    Identifier,
    Literal,
    StringLiteral,
    BinOp,
    UnaryOp,
    CallExpr,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
]
