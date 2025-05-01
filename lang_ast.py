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

@dataclass
class ReturnStmt:
    value: 'Expr'

@dataclass
class IfStmt:
    condition: 'Expr'
    then_body: List['Stmt']
    else_body: Optional[List['Stmt']]

@dataclass
class AssignStmt:
    target: str
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
class ListExpr:
    elements: List['Expr']

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

# Union Types
Stmt = Union[
    FunctionDef, ReturnStmt, IfStmt, AssignStmt, WhileStmt, ForStmt
]

Expr = Union[
    BinOp, Identifier, Literal, CallExpr, UnaryOp, ListExpr, DictExpr
]


