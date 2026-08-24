from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import re


class TokenKind(Enum):
    IDENTIFIER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    COMPARISON = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: object
    position: int
    text: str


class TokenizeError(ValueError):
    def __init__(self, message: str, position: int):
        super().__init__(message)
        self.message = message
        self.position = position


_NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_.%\-]*")


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    expecting_value = True
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "(":
            tokens.append(Token(TokenKind.LPAREN, char, index, char))
            index += 1
            expecting_value = True
            continue
        if char == ")":
            tokens.append(Token(TokenKind.RPAREN, char, index, char))
            index += 1
            expecting_value = False
            continue
        if char == ",":
            tokens.append(Token(TokenKind.COMMA, char, index, char))
            index += 1
            expecting_value = True
            continue
        if char == "[":
            closing = text.find("]", index + 1)
            if closing < 0:
                raise TokenizeError("Missing closing ']' for bracketed variable", index)
            raw = text[index + 1:closing]
            if not raw:
                raise TokenizeError("Bracketed variable name cannot be empty", index)
            tokens.append(Token(TokenKind.IDENTIFIER, raw, index, text[index:closing + 1]))
            index = closing + 1
            expecting_value = False
            continue
        matched_operator = next((op for op in ("<=", ">=", "==", "!=", "<>", "<", ">", "=") if text.startswith(op, index)), None)
        if matched_operator:
            tokens.append(Token(TokenKind.COMPARISON, matched_operator, index, matched_operator))
            index += len(matched_operator)
            expecting_value = True
            continue
        sign = ""
        number_start = index
        if char in "+-" and expecting_value and index + 1 < len(text) and (text[index + 1].isdigit() or text[index + 1] == "."):
            sign = char
            index += 1
        number = _NUMBER.match(text, index)
        if number:
            raw = sign + number.group(0)
            value = float(raw) if any(c in raw.lower() for c in (".", "e")) else int(raw)
            tokens.append(Token(TokenKind.NUMBER, value, number_start, raw))
            index = number.end()
            expecting_value = False
            continue
        if sign:
            raise TokenizeError(f"Expected a number after '{sign}'", number_start)
        identifier = _IDENTIFIER.match(text, index)
        if identifier:
            raw = identifier.group(0)
            upper = raw.upper()
            if upper == "AND":
                kind, value = TokenKind.AND, "AND"
                expecting_value = True
            elif upper == "OR":
                kind, value = TokenKind.OR, "OR"
                expecting_value = True
            elif upper == "NOT":
                kind, value = TokenKind.NOT, "NOT"
                expecting_value = True
            elif upper in {"TRUE", "FALSE"}:
                kind, value = TokenKind.BOOLEAN, upper == "TRUE"
                expecting_value = False
            else:
                kind, value = TokenKind.IDENTIFIER, raw
                expecting_value = False
            tokens.append(Token(kind, value, index, raw))
            index = identifier.end()
            continue
        raise TokenizeError(f"Unexpected character '{char}'", index)
    tokens.append(Token(TokenKind.EOF, None, len(text), ""))
    return tokens
