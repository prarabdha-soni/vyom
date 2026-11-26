"""Product catalogue and reference safety information (RSI)."""

from __future__ import annotations

from typing import Any

from vyom_os import audit
from vyom_os.core import Ctx, InvalidInput, NotFound
from vyom_os.db import Jsonb, fetch_all, fetch_one

_COLUMNS = """
    id::text as id, code, name, active_ingredient, dosage_form, strength,
    international_birth_date, reference_safety_terms, rsi_version, active
"""


def list_products(connection: Any, *, active_only: bool = False) -> list[dict[str, Any]]:
    where = "where active" if active_only else ""
    return fetch_all(connection, f"select {_COLUMNS} from products {where} order by code")


def get_product(connection: Any, code: str) -> dict[str, Any]:
    row = fetch_one(connection, f"select {_COLUMNS} from products where code = %s", (code,))
    if row is None:
        raise NotFound(f"No product {code}.")
    return row


def product_label(product: dict[str, Any]) -> str:
    """`CODE (Name)`, or just the name when it already carries the code."""
    code, name = str(product.get("code") or ""), str(product.get("name") or "")
    if not name or name == code:
        return code
    if code and name.startswith(code):
        return name
    return f"{code} ({name})" if code else name


def catalogue(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What a model is told about the tenant's products."""
    return [
        {"code": p["code"], "name": p["name"], "active_ingredient": p["active_ingredient"]}
        for p in products
        if p.get("active", True)
    ]


def mentions(text: str, products: list[dict[str, Any]]) -> list[str]:
    """Product codes whose code, name or active ingredient appears in the text."""
    folded = text.casefold()
    found = []
    for product in products:
        needles = [product["code"], product["name"], product["active_ingredient"]]
        if any(needle and str(needle).casefold() in folded for needle in needles):
            found.append(product["code"])
    return found


def update_reference_terms(
    connection: Any, ctx: Ctx, code: str, *, terms: list[str], rsi_version: str, reason: str
) -> dict[str, Any]:
    ctx.require("product.write")
    cleaned = sorted({term.strip() for term in terms if term and term.strip()}, key=str.casefold)
    if len(cleaned) > 500 or any(len(term) > 200 for term in cleaned):
        raise InvalidInput("Reference terms are limited to 500 terms of 200 characters.")
    if not rsi_version.strip() or len(rsi_version) > 40:
        raise InvalidInput("Give the RSI version, for example the CCDS or SmPC date.")
    if not reason.strip():
        raise InvalidInput("Give a reason for the change.")
    product = get_product(connection, code)
    connection.execute(
        "update products set reference_safety_terms = %s, rsi_version = %s where code = %s",
        (Jsonb([{"term": term} for term in cleaned]), rsi_version.strip(), code),
    )
    audit.record(
        connection,
        entity_kind="product",
        entity_ref=code,
        event_type="rsi_updated",
        actor=ctx.actor,
        detail={
            "from_version": product["rsi_version"],
            "to_version": rsi_version.strip(),
            "terms": len(cleaned),
            "reason": reason.strip()[:500],
        },
    )
    return get_product(connection, code)
