# Example: flatten control flow with a guard clause

Read when a concrete before/after comparison would help with nested control flow. The goal is to
expose the main operation while preserving validation and effect order. `process_items` represents
the existing operation; its behavior and callers are unchanged in this example.

## Before

The useful work is nested under the valid case. `None` means no limit; zero remains a valid limit.

```python
def process(items, *, limit=None):
    if limit is None or limit >= 0:
        result = process_items(items, limit=limit)
        return result
    raise ValueError("negative limit")
```

## After

Invert the original condition to reject the invalid case first, then leave the main call visible.

```python
def process(items, *, limit=None):
    if not (limit is None or limit >= 0):
        raise ValueError("negative limit")
    return process_items(items, limit=limit)
```

If the established input domain is integers or `None`, the guard can instead be written
`limit is not None and limit < 0`. For other values, those comparisons need not be equivalent:
NaN is neither greater than or equal to zero nor less than zero. Replacing the condition with
`if not limit` would also confuse zero with absence.

Check the supported boundary inputs and the operation's calls: invalid limits must fail before
`process_items` runs; valid limits must reach it once, unchanged. Preserve its result and propagated
exceptions. Do not reorder effectful predicates or move cleanup while flattening the function.
Keep the original conditional when a guard would make its meaning harder to follow.

[sourced] [guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html)
and [Python expression semantics](https://docs.python.org/3/reference/expressions.html).
