from unittest.mock import patch

def test_low_stock_notification_success_stub(client, monkeypatch):
    from app import store

    # Force the notification service to report success.
    monkeypatch.setattr(
        "app.routes.transactions.send_notification",
        lambda recipient, subject, message: True,
    )

    # Create a product with 12 units and a reorder level of 10.
    product_response = client.post("/products", json={
        "name": "Notebook",
        "sku": "A3-NOTEBOOK-001",
        "unit_price": 5.0,
        "quantity_on_hand": 12,
        "reorder_level": 10,
    })
    assert product_response.status_code == 201
    product_id = product_response.get_json()["id"]

    # Remove 5 units, leaving 7 (below the reorder level).
    response = client.post("/transactions", json={
        "product_id": product_id,
        "type": "OUT",
        "quantity": 5,
    })

    assert response.status_code == 201
    assert response.get_json()["notification_sent"] is True

    # The transaction still updates the inventory correctly.
    assert store.products[product_id].quantity_on_hand == 7


def test_low_stock_notification_at_reorder_boundary(client):
    from app import store

    # Create a product that will reach its exact reorder level.
    product_response = client.post("/products", json={
        "name": "USB-C Adapter",
        "sku": "USB-C-014",
        "unit_price": 12.0,
        "quantity_on_hand": 18,
        "reorder_level": 8,
    })
    assert product_response.status_code == 201
    product_id = product_response.get_json()["id"]

    # Mock the notification service and record its calls.
    with patch("app.routes.transactions.send_notification", return_value=True) as mock_send:
        response = client.post("/transactions", json={
            "product_id": product_id,
            "type": "OUT",
            "quantity": 10,
        })

    # Verify the transaction and resulting inventory state.
    assert response.status_code == 201
    assert response.get_json()["notification_sent"] is True
    assert store.products[product_id].quantity_on_hand == 8

    # Verify the notification was called exactly once with the right details.
    mock_send.assert_called_once_with(
        "inventory-staff",
        "Low Stock",
        "Product USB-C Adapter (SKU: USB-C-014) is low on stock. "
        "Current quantity: 8. Reorder level: 8."
    )


def test_create_purchase_order_rejects_unknown_product(client):
    """An order should not be created for a product that does not exist."""

    # Create a valid supplier, but use a product ID that does not exist.
    supplier = client.post("/suppliers", json={
        "name": "Campus Office Supplies",
        "contact_email": "orders@example.com"
    }).get_json()

    response = client.post("/purchase-orders", json={
        "supplier_id": supplier["id"],
        "product_id": 999999,
        "quantity_ordered": 4
    })

    assert response.status_code == 404
    assert response.get_json()["error"] == "Product not found"

    # A rejected request must not create a purchase order.
    orders = client.get("/purchase-orders")
    assert orders.status_code == 200
    assert orders.get_json() == []


def test_receive_nonexistent_purchase_order(client):
    """Receiving an unknown purchase order should not affect inventory."""

    response = client.put("/purchase-orders/999999/receive")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Purchase order not found"

    # No transactions or purchase orders should be created.
    assert client.get("/purchase-orders").get_json() == []
    assert client.get("/transactions").get_json() == []



def test_products_page_creates_and_displays_product(client):
    """Verify that the HTML product form creates a product and displays it."""

    # The products page should load successfully before adding anything.
    response = client.get("/ui/products")
    assert response.status_code == 200

    # Submit a new product through the HTML form.
    response = client.post("/ui/products", data={
        "name": "Wireless Mouse",
        "sku": "MOUSE-327",
        "unit_price": "24.99",
        "quantity_on_hand": "15",
    })

    # The form should redirect back to the products page.
    assert response.status_code == 302
    assert "/ui/products" in response.headers["Location"]

    # Confirm that the new product appears in the application.
    products = client.get("/products").get_json()
    assert len(products) == 1
    assert products[0]["name"] == "Wireless Mouse"
    assert products[0]["sku"] == "MOUSE-327"
    assert products[0]["quantity_on_hand"] == 15

    # The rendered HTML page should display the new product.
    page = client.get("/ui/products")
    assert b"Wireless Mouse" in page.data



def test_delete_product_through_html_page(client):
    """Verify that deleting a product through the UI removes it from inventory."""

    # Create a product to delete.
    created = client.post("/products", json={
        "name": "Laptop Stand",
        "sku": "STAND-327",
        "unit_price": 29.99,
        "quantity_on_hand": 8,
        "reorder_level": 3,
    }).get_json()

    product_id = created["id"]

    # Delete the product using the HTML interface.
    response = client.post(f"/ui/products/{product_id}/delete")

    assert response.status_code == 302
    assert "/ui/products" in response.headers["Location"]

    # Confirm the product was actually removed.
    check = client.get(f"/products/{product_id}")
    assert check.status_code == 404

    products = client.get("/products").get_json()
    assert products == []



def test_transactions_page_records_incoming_and_outgoing_stock(client):
    """Verify HTML transactions update inventory and record transaction history."""

    # Create a product and supplier for the transactions.
    product = client.post("/products", json={
        "name": "Portable Charger",
        "sku": "CHARGER-327",
        "unit_price": 19.99,
        "quantity_on_hand": 10,
        "reorder_level": 3,
    }).get_json()

    supplier = client.post("/suppliers", json={
        "name": "Campus Tech Supply",
        "contact_email": "orders@example.com",
    }).get_json()

    product_id = product["id"]
    supplier_id = supplier["id"]

    # Check that the transactions page loads.
    page = client.get("/ui/transactions")
    assert page.status_code == 200

    # Record 5 incoming units associated with the supplier.
    incoming = client.post("/ui/transactions", data={
        "product_id": str(product_id),
        "supplier_id": str(supplier_id),
        "type": "IN",
        "quantity": "5",
    })
    assert incoming.status_code == 302

    # Record 4 outgoing units without a supplier.
    outgoing = client.post("/ui/transactions", data={
        "product_id": str(product_id),
        "supplier_id": "",
        "type": "OUT",
        "quantity": "4",
    })
    assert outgoing.status_code == 302

    # Stock should be 10 + 5 - 4 = 11.
    stock = client.get(f"/products/{product_id}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 11

    # Both transactions should appear in history.
    history = client.get("/transactions").get_json()
    assert len(history) == 2
    assert history[0]["type"] == "IN"
    assert history[0]["supplier_id"] == supplier_id
    assert history[1]["type"] == "OUT"
    assert history[1]["supplier_id"] is None
