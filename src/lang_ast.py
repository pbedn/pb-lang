from dataclasses import dataclass
from typing import List, Union, Optional

@dataclass
class Program:
    body: List['Stmt']

# Statements
@dataclass
class FunctionDef:
    name: str
    params: List[str]
    body: List['Stmt']
    return_type: Optional[str]
    globals_declared: Optional[set] = None

@dataclass
class ReturnStmt:
    value: 'Expr'

@dataclass
class ClassDef:
    name: str
    base: Optional[str]
    fields: List['VarDecl']
    methods: List['FunctionDef']

@dataclass
class AttributeExpr:
    obj: 'Expr'
    attr: str

@dataclass
class GlobalStmt:
    names: List[str]

@dataclass
class VarDecl:
    name: str
    declared_type: str
    value: 'Expr'

@dataclass
class IfStmt:
    condition: 'Expr'
    then_body: List['Stmt']
    else_body: Optional[List['Stmt']]

@dataclass
class AssignStmt:
    target: 'Expr'
    value: 'Expr'

@dataclass
class AugAssignStmt:
    target: 'Expr'
    op: str
    value: 'Expr'

@dataclass
class WhileStmt:
    condition: 'Expr'
    body: List['Stmt']

@dataclass
class ForStmt:
    var_name: str
    iterable: 'Expr'
    body: List['Stmt']

@dataclass
class AssertStmt:
    condition: 'Expr'

@dataclass
class BreakStmt:
    pass

@dataclass
class PassStmt:
    pass

@dataclass
class ContinueStmt:
    pass

@dataclass
class ListExpr:
    elements: List['Expr']
    elem_type: Optional[str] = None  # inferred during type checking

@dataclass
class IndexExpr:
    base: 'Expr'
    index: 'Expr'
    elem_type: Optional[str] = None

@dataclass
class DictExpr:
    pairs: List[tuple['Expr', 'Expr']]

# Expressions
@dataclass
class BinOp:
    left: 'Expr'
    op: str
    right: 'Expr'

@dataclass
class Identifier:
    name: str

@dataclass
class Literal:
    value: Union[int, float, str, bool]

@dataclass
class CallExpr:
    func: 'Expr'
    args: List['Expr']

@dataclass
class UnaryOp:
    op: str
    operand: 'Expr'

Stmt = Union[
    FunctionDef, ReturnStmt, IfStmt, AssignStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt, AugAssignStmt, GlobalStmt, VarDecl,
    PassStmt, ClassDef, AssertStmt
]

Expr = Union[
    BinOp, Identifier, Literal, CallExpr, UnaryOp, ListExpr, DictExpr,
    IndexExpr, AttributeExpr
]
