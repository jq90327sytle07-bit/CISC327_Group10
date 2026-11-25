"""Kylin's A4 browser workflows; run against local Flask or the Docker app."""

import re
from uuid import uuid4

import pytest
from playwright.sync_api import expect


pytestmark = pytest.mark.e2e


def _product_row(page, sku):
    return page.get_by_role("row").filter(
        has=page.get_by_role("cell", name=sku, exact=True)
    )


def _transaction_rows(page, product_id):
    return page.get_by_role("row").filter(
        has=page.locator(
            "td:nth-child(2)", has_text=re.compile(rf"^{re.escape(product_id)}$")
        )
    )


@pytest.fixture
def stocked_product(page, base_url):
    """Create this test's product through the UI and remove it during teardown."""
    suffix = uuid4().hex[:12]
    product = {"name": f"Kylin A4 Product {suffix}", "sku": f"A4-K-{suffix}"}

    page.goto(f"{base_url}/ui/products")
    page.get_by_label("Name", exact=True).fill(product["name"])
    page.get_by_label("SKU", exact=True).fill(product["sku"])
    page.get_by_label("Unit Price", exact=True).fill("10.00")
    page.get_by_label("Quantity on Hand", exact=True).fill("10")
    page.get_by_role("button", name="Add Product", exact=True).click()

    row = _product_row(page, product["sku"])
    expect(row).to_have_count(1)
    expect(row.get_by_role("cell").nth(4)).to_have_text("10")
    product["id"] = row.get_by_role("cell").nth(0).inner_text().strip()

    yield product

    page.goto(f"{base_url}/ui/products")
    row = _product_row(page, product["sku"])
    if row.count():
        row.get_by_role("button", name="Delete", exact=True).click()
        expect(_product_row(page, product["sku"])).to_have_count(0)


def test_incoming_stock_updates_inventory_and_history(page, base_url, stocked_product):
    """K1: receiving five units updates the visible history and stock to fifteen."""
    page.goto(f"{base_url}/ui/transactions")
    expect(_transaction_rows(page, stocked_product["id"])).to_have_count(0)

    page.get_by_label("Product ID", exact=True).fill(stocked_product["id"])
    page.locator('select[name="type"]').select_option("IN")
    page.get_by_label("Quantity", exact=True).fill("5")
    page.get_by_role("button", name="Record", exact=True).click()

    rows = _transaction_rows(page, stocked_product["id"])
    expect(rows).to_have_count(1)
    expect(rows.get_by_role("cell").nth(3)).to_have_text("IN")
    expect(rows.get_by_role("cell").nth(4)).to_have_text("5")

    page.reload()
    expect(_transaction_rows(page, stocked_product["id"])).to_have_count(1)
    page.goto(f"{base_url}/ui/products")
    expect(
        _product_row(page, stocked_product["sku"]).get_by_role("cell").nth(4)
    ).to_have_text("15")


def test_zero_outgoing_quantity_preserves_inventory_and_history(
    page, base_url, stocked_product
):
    """K2: native form validation rejects zero without creating a transaction."""
    page.goto(f"{base_url}/ui/transactions")
    expect(_transaction_rows(page, stocked_product["id"])).to_have_count(0)

    page.get_by_label("Product ID", exact=True).fill(stocked_product["id"])
    page.locator('select[name="type"]').select_option("OUT")
    quantity = page.get_by_label("Quantity", exact=True)
    quantity.fill("0")
    page.get_by_role("button", name="Record", exact=True).click()

    expect(quantity).to_be_focused()
    expect(quantity).to_have_value("0")
    assert quantity.evaluate("input => input.validity.rangeUnderflow")
    assert quantity.evaluate("input => input.validationMessage.length > 0")

    page.reload()
    expect(_transaction_rows(page, stocked_product["id"])).to_have_count(0)
    page.goto(f"{base_url}/ui/products")
    expect(
        _product_row(page, stocked_product["sku"]).get_by_role("cell").nth(4)
    ).to_have_text("10")
