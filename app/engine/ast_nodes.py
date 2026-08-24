from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ASTNode:
    def variables(self) -> set[str]:
        raise NotImplementedError

    def tree_lines(self, prefix: str = "", last: bool = True) -> list[str]:
        connector = "└── " if last else "├── "
        lines = [prefix + connector + self.label()]
        children = self.children()
        extension = "    " if last else "│   "
        for index, child in enumerate(children):
            lines.extend(child.tree_lines(prefix + extension, index == len(children) - 1))
        return lines

    def label(self) -> str:
        return type(self).__name__

    def children(self) -> list[ASTNode]:
        return []


@dataclass(slots=True)
class Literal(ASTNode):
    value: Any

    def variables(self) -> set[str]:
        return set()

    def label(self) -> str:
        if isinstance(self.value, bool):
            return "TRUE" if self.value else "FALSE"
        return str(self.value)


@dataclass(slots=True)
class Variable(ASTNode):
    name: str

    def variables(self) -> set[str]:
        return {self.name}

    def label(self) -> str:
        return self.name


@dataclass(slots=True)
class FunctionCall(ASTNode):
    name: str
    arguments: list[ASTNode] = field(default_factory=list)

    def variables(self) -> set[str]:
        return set().union(*(arg.variables() for arg in self.arguments)) if self.arguments else set()

    def label(self) -> str:
        return self.name.upper() + "()"

    def children(self) -> list[ASTNode]:
        return self.arguments


@dataclass(slots=True)
class Comparison(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode

    def variables(self) -> set[str]:
        return self.left.variables() | self.right.variables()

    def label(self) -> str:
        return self.operator

    def children(self) -> list[ASTNode]:
        return [self.left, self.right]


@dataclass(slots=True)
class Logical(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode

    def variables(self) -> set[str]:
        return self.left.variables() | self.right.variables()

    def label(self) -> str:
        return self.operator.upper()

    def children(self) -> list[ASTNode]:
        return [self.left, self.right]


@dataclass(slots=True)
class Not(ASTNode):
    operand: ASTNode

    def variables(self) -> set[str]:
        return self.operand.variables()

    def label(self) -> str:
        return "NOT"

    def children(self) -> list[ASTNode]:
        return [self.operand]


def format_ast(node: ASTNode) -> str:
    lines = [node.label()]
    children = node.children()
    for index, child in enumerate(children):
        lines.extend(child.tree_lines("", index == len(children) - 1))
    return "\n".join(lines)
