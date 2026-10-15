# Example: flatten control flow with a guard clause

`None` means no limit; zero is a valid limit. Before:

```python
def process(items, *, limit=None):
    if limit is None or limit >= 0:
        result = process_items(items, limit=limit)
        return result
    raise ValueError("negative limit")
```

After, inverting the original condition so the invalid case fails first:

```python
def process(items, *, limit=None):
    if not (limit is None or limit >= 0):
        raise ValueError("negative limit")
    return process_items(items, limit=limit)
```

`limit is not None and limit < 0` is equivalent only for integers or `None`: NaN fails both
`>= 0` and `< 0`. `if not limit` confuses zero with absence. Invalid limits must fail before
`process_items` runs; valid ones reach it once, unchanged. Keep the nested form when a guard reads
worse.

[sourced] [guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html)
and [Python expression semantics](https://docs.python.org/3/reference/expressions.html).
