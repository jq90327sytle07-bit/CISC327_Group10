from uuid import uuid4

from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:5000"


def test_create_product_through_web_form(page: Page):
    # Generate a unique SKU so the test can run repeatedly.
    sku = f"A4-{uuid4().hex[:8]}"

    # Open the HTML Products page (not the JSON API).
    page.goto(f"{BASE_URL}/ui/products")

    # Fill out the product creation form.
    page.locator('input[name="name"]').fill("A4 Test Desk")
    page.locator('input[name="sku"]').fill(sku)
    page.locator('input[name="unit_price"]').fill("49.99")
    page.locator('input[name="quantity_on_hand"]').fill("10")

    # Submit the form.
    page.get_by_role("button", name="Add Product").click()

    # Verify the new product appears in the table.
    product_row = page.locator("tr").filter(has_text=sku)

    expect(product_row).to_be_visible()
    expect(product_row).to_contain_text("A4 Test Desk")
    expect(product_row).to_contain_text("49.99")
    expect(product_row).to_contain_text("10")


def test_invalid_supplier_email_blocks_submission(page: Page):
    # Open the actual Suppliers webpage.
    page.goto(f"{BASE_URL}/ui/suppliers")

    # Enter a unique supplier name and an invalid email address.
    supplier_name = f"A4 Invalid Supplier {uuid4().hex[:8]}"

    page.locator('input[name="name"]').fill(supplier_name)
    email_field = page.locator('input[name="contact_email"]')
    email_field.fill("not-an-email")

    # Attempt to submit the form.
    page.get_by_role("button", name="Add Supplier").click()

    # The browser should reject the invalid email.
    assert email_field.evaluate("(element) => element.validity.typeMismatch")

    # Confirm we remain on the supplier form.
    expect(page).to_have_url(f"{BASE_URL}/ui/suppliers")

    # Verify that the invalid supplier was not added to the table.
    supplier_row = page.locator("tr").filter(has_text=supplier_name)
    expect(supplier_row).to_have_count(0)