from __future__ import annotations

"""Abstract‑syntax tree (AST) node definitions for the PB language.
This module is consumed by the lexer, parser, type‑checker and code‑generator.
It strives to be **complete** – any syntactic construct recognised by the parser
should have a corresponding dataclass here so that downstream passes can rely
on a single, strongly‑typed representation.

Conventions
-----------
* Every concrete node belongs to exactly one of the two root union aliases
  ``Stmt`` or ``Expr``.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional, Set

# === Root module ===
@dataclass
class Program:
    body: List[Stmt]

    #  class_name → field_name → pb_type
    inferred_instance_fields: dict[str, dict[str, str]] = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class Parameter:
    name: str
    type: Optional[str]               # None means not annotated
    default: Optional[Expr] = None    # None ⇒ no default
    inferred_type: Optional[str] = None

@dataclass
class FunctionDef:
    name: str
    params: List[Parameter]
    body: List[Stmt]
    return_type: Optional[str]                   # None => void
    globals_declared: Optional[Set[str]] = None  #  filled in by parser/type-checker
    inferred_return_type: Optional[str] = None


@dataclass
class ClassDef:
    name: str
    base: Optional[str]             # single inheritance only
    fields: List["VarDecl"]         # field decls (VarDecl) 
    methods: List["FunctionDef"]    # methods (FunctionDef)


@dataclass
class GlobalStmt:
    names: List[str]


@dataclass
class VarDecl:
    name: str
    declared_type: str
    value: Expr
    inferred_type: Optional[str] = None


@dataclass
class AssignStmt:
    target: Expr                  # Identifier | AttributeExpr | IndexExpr
    value: Expr
    inferred_type: Optional[str] = None


@dataclass
class AugAssignStmt:
    target: Expr
    op: str                         # "+=", "-=", etc.
    value: Expr
    inferred_type: Optional[str] = None


@dataclass
class IfBranch:
    condition: Optional[Expr]  # None for 'else'
    body: List[Stmt]

@dataclass
class IfStmt:
    branches: List[IfBranch]


@dataclass
class WhileStmt:
    condition: Expr
    body: List[Stmt]


@dataclass
class ForStmt:
    var_name: str
    iterable: Expr             # e.g. range(...)
    body: List[Stmt]
    elem_type: Optional[str] = None


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
    inferred_type: Optional[str] = None


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
    inferred_type: Optional[str] = None


@dataclass
class Literal:
    raw: str                     # raw lexeme (underscores stripped)
    # parsing into int/float happens later in a dedicated pass
    inferred_type: Optional[str] = None


@dataclass
class StringLiteral:
    value: str
    inferred_type: Optional[str] = None


@dataclass
class FStringLiteral:
    raw: str                     # text between the quotes (without the leading f)
    vars: List[str] = field(default_factory=list)       # names found between {…} - filled by lexer
    inferred_type: Optional[str] = None


@dataclass
class BinOp:
    left: Expr
    op: str                      # "+", "==", "is", "//", "and", etc.
    right: Expr
    inferred_type: Optional[str] = None


@dataclass
class UnaryOp:
    op: str                      # "-" or "not"
    operand: Expr
    inferred_type: Optional[str] = None


@dataclass
class CallExpr:
    func: Expr
    args: List[Expr]
    inferred_type: Optional[str] = None


@dataclass
class AttributeExpr:
    obj: Expr
    attr: str
    inferred_type: Optional[str] = None


@dataclass
class IndexExpr:
    base: Expr
    index: Expr
    elem_type: Optional[str] = None     # For value type


@dataclass
class ListExpr:
    elements: List[Expr]
    elem_type: Optional[str] = None     # For value type
    inferred_type: Optional[str] = None


@dataclass
class DictExpr:
    keys: List[Expr]
    values: List[Expr]
    elem_type: Optional[str] = None     # For value type
    inferred_type: Optional[str] = None


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
    IfBranch,
    IfStmt,
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
    FStringLiteral,
    BinOp,
    UnaryOp,
    CallExpr,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
]
