from __future__ import annotations

from .ast_nodes import ASTNode, Comparison, FunctionCall, Literal, Logical, Not, Variable
from .tokenizer import Token, TokenKind, TokenizeError, tokenize


class ParseError(ValueError):
    def __init__(self, message: str, position: int = 0):
        super().__init__(message)
        self.message = message
        self.position = position


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def match(self, *kinds: TokenKind) -> Token | None:
        if self.current.kind in kinds:
            return self.advance()
        return None

    def parse(self) -> ASTNode:
        if self.current.kind == TokenKind.EOF:
            raise ParseError("Expression is empty", 0)
        result = self.parse_or()
        if self.current.kind != TokenKind.EOF:
            if self.current.kind == TokenKind.RPAREN:
                raise ParseError("Unexpected closing parenthesis", self.current.position)
            raise ParseError(f"Unexpected '{self.current.text}'", self.current.position)
        return result

    def parse_or(self) -> ASTNode:
        node = self.parse_and()
        while self.match(TokenKind.OR):
            if self.current.kind in {TokenKind.EOF, TokenKind.RPAREN}:
                raise ParseError("Missing condition after 'OR'", self.current.position)
            node = Logical(node, "OR", self.parse_and())
        return node

    def parse_and(self) -> ASTNode:
        node = self.parse_not()
        while self.match(TokenKind.AND):
            if self.current.kind in {TokenKind.EOF, TokenKind.RPAREN}:
                raise ParseError("Missing condition after 'AND'", self.current.position)
            node = Logical(node, "AND", self.parse_not())
        return node

    def parse_not(self) -> ASTNode:
        if self.match(TokenKind.NOT):
            if self.current.kind in {TokenKind.EOF, TokenKind.RPAREN}:
                raise ParseError("Missing condition after 'NOT'", self.current.position)
            return Not(self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        left = self.parse_primary()
        operator = self.match(TokenKind.COMPARISON)
        if operator:
            if self.current.kind in {TokenKind.EOF, TokenKind.RPAREN, TokenKind.AND, TokenKind.OR, TokenKind.COMMA}:
                raise ParseError(f"Missing value after '{operator.value}'", self.current.position)
            return Comparison(left, str(operator.value), self.parse_primary())
        return left

    def parse_primary(self) -> ASTNode:
        number = self.match(TokenKind.NUMBER)
        if number:
            return Literal(number.value)
        boolean = self.match(TokenKind.BOOLEAN)
        if boolean:
            return Literal(boolean.value)
        identifier = self.match(TokenKind.IDENTIFIER)
        if identifier:
            name = str(identifier.value)
            if self.match(TokenKind.LPAREN):
                arguments: list[ASTNode] = []
                if not self.match(TokenKind.RPAREN):
                    while True:
                        arguments.append(self.parse_or())
                        if self.match(TokenKind.RPAREN):
                            break
                        if not self.match(TokenKind.COMMA):
                            if self.current.kind == TokenKind.EOF:
                                raise ParseError("Missing closing parenthesis", self.current.position)
                            raise ParseError("Expected ',' or ')' in function call", self.current.position)
                return FunctionCall(name, arguments)
            return Variable(name)
        if self.match(TokenKind.LPAREN):
            node = self.parse_or()
            if not self.match(TokenKind.RPAREN):
                raise ParseError("Missing closing parenthesis", self.current.position)
            return node
        if self.current.kind == TokenKind.EOF:
            raise ParseError("Expression ends unexpectedly", self.current.position)
        raise ParseError(f"Expected a value or variable, found '{self.current.text}'", self.current.position)


def parse_expression(text: str) -> ASTNode:
    try:
        return Parser(tokenize(text)).parse()
    except TokenizeError as error:
        raise ParseError(error.message, error.position) from error
