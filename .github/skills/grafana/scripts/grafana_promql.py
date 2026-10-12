"""Bounded PromQL inspection shared by dependency discovery and dashboard hygiene.

The parser is imported only when inspecting an expression. Grafana variables are
reported without substituting values; literal selectors can still be recovered
when variables occur inside quoted label values.
"""

import re
from typing import NamedTuple

MAX_TEXT = 16000
MAX_DEPTH, MAX_NODES, MAX_TOKENS = 64, 256, 256
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::[^}]*)?\}|\$([A-Za-z_][A-Za-z0-9_]*)|\[\[([A-Za-z_][A-Za-z0-9_]*)(?::[^]]*)?\]\]")
METRIC = r"[a-zA-Z_:][a-zA-Z0-9_:]*"
RATE_FUNCTIONS = frozenset({"rate", "irate", "increase"})
# Tokenization bounds native parsing and masks text for the portable fallback.
# Metric names and call relationships always come from the AST when available.
TOKEN = re.compile(r'''(?P<string>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`[^`]*`)|(?P<comment>\#[^\n]*)|[A-Za-z0-9_:]+|[^\s]''', re.DOTALL)


class Analysis(NamedTuple):
    metrics: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    truncated: bool = False
    ast_complete: bool = False
    rate_calls: tuple[str, ...] = ()
    unrated_counters: tuple[str, ...] = ()


def input_limit(expression):
    """Bound native parsing before it constructs recursive Python AST objects."""
    if len(expression) > MAX_TEXT:
        return "expression_truncated"
    depth = tokens = 0
    for match in TOKEN.finditer(expression):
        if match.lastgroup == "comment":
            continue
        tokens += 1
        if tokens > MAX_TOKENS:
            return "promql_token_limit"
        if match.lastgroup == "string":
            continue
        token = match[0]
        if token in ("(", "[", "{"):
            depth += 1
            if depth > MAX_DEPTH:
                return "promql_depth_limit"
        elif token in (")", "]", "}"):
            depth -= 1
    return None


def code_only(expression):
    """Mask quoted values and comments without changing source offsets."""
    return TOKEN.sub(lambda match: " " * len(match[0])
                     if match.lastgroup in ("string", "comment") else match[0], expression)


def _selector_metrics(selector, parser):
    names, gaps = set(), set()
    groups = selector.matchers.or_matchers or [selector.matchers.matchers]
    for group in groups:
        candidates = {selector.name} if selector.name else set()
        name_matchers = [matcher for matcher in group if matcher.name == "__name__"]
        if any(matcher.op != parser.MatchOp.Equal for matcher in name_matchers):
            gaps.add("promql_metric_name_unresolved")
            continue
        candidates.update(matcher.value for matcher in name_matchers)
        if len(candidates) != 1:
            gaps.add("promql_metric_name_unresolved")
            continue
        name = candidates.pop()
        if VARIABLE.search(name):
            gaps.add("promql_template_unresolved")
        elif not re.fullmatch(METRIC, name):
            gaps.add("promql_metric_name_unresolved")
        else:
            names.add(name)
    return names, gaps


def analyze(expression):
    """Inspect selectors and rate-call ancestry once, retaining fixed gap codes.

    ImportError is left to the caller: dependency graphs require the parser,
    while the standalone hygiene checker can explicitly report a text fallback.
    """
    if limit := input_limit(expression):
        return Analysis(gaps=(limit,), truncated=True)
    import promql_parser  # noqa: PLC0415 - importing this helper stays stdlib-only.

    gaps = {"promql_template_unresolved"} if VARIABLE.search(expression) else set()
    try:
        root = promql_parser.parse(expression)
    except ValueError:
        # Parser diagnostics can quote query text. Expose only static gap codes.
        return Analysis(gaps=tuple(sorted(gaps | {"promql_parse_error"})))
    names, counters, calls = set(), [], []
    pending, visited = [(root, 0, False)], 0
    while pending:
        node, depth, inside_rate = pending.pop()
        visited += 1
        if depth > MAX_DEPTH or visited > MAX_NODES:
            limit = "promql_depth_limit" if depth > MAX_DEPTH else "promql_node_limit"
            return Analysis(gaps=tuple(sorted(gaps | {limit})), truncated=True)
        if isinstance(node, promql_parser.VectorSelector):
            selected, unresolved = _selector_metrics(node, promql_parser)
            names.update(selected)
            gaps.update(unresolved)
            if not inside_rate:
                counters.extend(name for name in sorted(selected) if name.endswith("_total"))
            children = []
        elif isinstance(node, promql_parser.MatrixSelector):
            children = [node.vector_selector]
        elif isinstance(node, promql_parser.BinaryExpr):
            children = [node.lhs, node.rhs]
        elif isinstance(node, promql_parser.AggregateExpr):
            children = [node.expr] + ([node.param] if node.param is not None else [])
        elif isinstance(node, (promql_parser.UnaryExpr, promql_parser.ParenExpr, promql_parser.SubqueryExpr)):
            children = [node.expr]
        elif isinstance(node, promql_parser.Call):
            if node.func.name in RATE_FUNCTIONS:
                calls.append(node)
                inside_rate = True
            children = node.args
        elif isinstance(node, (promql_parser.NumberLiteral, promql_parser.StringLiteral)):
            children = []
        else:
            children = []
            gaps.add("promql_ast_node_unsupported")
        pending.extend((child, depth + 1, inside_rate) for child in reversed(children))
    return Analysis(metrics=tuple(sorted(names)), gaps=tuple(sorted(gaps)),
                    ast_complete="promql_ast_node_unsupported" not in gaps,
                    rate_calls=tuple(node.prettify()[:60] for node in calls),
                    unrated_counters=tuple(dict.fromkeys(counters)))
