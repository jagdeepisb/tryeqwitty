"""Shared validation primitives for the analytical contracts."""

from decimal import Decimal


def require(ok, message):
    if not ok:
        raise ValueError(message)


def indexed(rows, label):
    result = {row["id"]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate {label} IDs")
    return result


def refs(values, table, label):
    require(set(values) <= set(table), f"Unknown reference in {label}")


def number(value):
    require(len(value) <= 80, "Decimal too long")
    return Decimal(value)
