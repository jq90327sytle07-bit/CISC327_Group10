from unittest.mock import patch


def _create_a3_supplier(client):
    response = client.post("/suppliers", json={
        "name": "A3 Supplier",
        "contact_email": "a3@example.com",
    })
    assert response.status_code == 201
    return response.get_json()


def test_update_unknown_supplier_preserves_existing_data(client):
    original = _create_a3_supplier(client)

    response = client.put("/suppliers/999999", json={
        "name": "Unexpected Change",
        "contact_email": "wrong@example.com",
    })

    assert response.status_code == 404
    assert response.get_json() == {"error": "Supplier not found"}

    suppliers = client.get("/suppliers").get_json()
    assert suppliers == [original]


def test_delete_unknown_supplier_preserves_existing_data(client):
    original = _create_a3_supplier(client)

    response = client.delete("/suppliers/999999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Supplier not found"}

    suppliers = client.get("/suppliers").get_json()
    assert suppliers == [original]


def test_unknown_supplier_products_returns_error(client):
    original = _create_a3_supplier(client)

    response = client.get("/suppliers/999999/products")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Supplier not found"}

    assert client.get("/suppliers").get_json() == [original]
    assert client.get("/transactions").get_json() == []

def test_home_page_displays_navigation(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Inventory Management System" in html
    assert "/ui/products" in html
    assert "/ui/suppliers" in html
    assert "/ui/transactions" in html


def test_suppliers_page_creates_and_displays_supplier(client):
    initial_page = client.get("/ui/suppliers")
    assert initial_page.status_code == 200

    response = client.post("/ui/suppliers", data={
        "name": "Campus Parts",
        "contact_email": "parts@example.com",
    })

    assert response.status_code == 302
    assert "/ui/suppliers" in response.headers["Location"]

    suppliers = client.get("/suppliers").get_json()
    assert len(suppliers) == 1
    assert suppliers[0]["name"] == "Campus Parts"
    assert suppliers[0]["contact_email"] == "parts@example.com"

    page = client.get("/ui/suppliers")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Campus Parts" in html
    assert "parts@example.com" in html


def test_delete_supplier_page_removes_supplier(client):
    supplier = _create_a3_supplier(client)

    response = client.post(
        f"/ui/suppliers/{supplier['id']}/delete"
    )

    assert response.status_code == 302
    assert "/ui/suppliers" in response.headers["Location"]

    missing = client.get(f"/suppliers/{supplier['id']}")
    assert missing.status_code == 404
    assert client.get("/suppliers").get_json() == []

    page = client.get("/ui/suppliers")
    assert page.status_code == 200
    assert supplier["name"] not in page.get_data(as_text=True)
def test_transaction_history_filters_by_supplier(client):
    supplier_a = _create_a3_supplier(client)

    supplier_response = client.post("/suppliers", json={
        "name": "Other A3 Supplier",
        "contact_email": "other@example.com",
    })
    assert supplier_response.status_code == 201
    supplier_b = supplier_response.get_json()

    product_response = client.post("/products", json={
        "name": "A3 Keyboard",
        "sku": "A3-FILTER-001",
        "unit_price": 20,
        "quantity_on_hand": 10,
        "reorder_level": 2,
    })
    assert product_response.status_code == 201
    product = product_response.get_json()

    transactions = []
    for supplier in (supplier_a, supplier_b):
        response = client.post("/transactions", json={
            "product_id": product["id"],
            "supplier_id": supplier["id"],
            "type": "IN",
            "quantity": 3,
        })
        assert response.status_code == 201
        transactions.append(response.get_json())

    filtered = client.get(
        f"/transactions?supplier_id={supplier_a['id']}"
    )
    assert filtered.status_code == 200
    assert filtered.get_json() == [transactions[0]]

    # Filtering must not remove records or change inventory.
    history = client.get("/transactions")
    assert history.status_code == 200
    assert history.get_json() == transactions

    stock = client.get(f"/products/{product['id']}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 16


def _create_notification_product(client, sku):
    response = client.post("/products", json={
        "name": "A3 Notification Product",
        "sku": sku,
        "unit_price": 10,
        "quantity_on_hand": 12,
        "reorder_level": 10,
    })
    assert response.status_code == 201
    return response.get_json()


def test_low_stock_notification_failure_stub(client, monkeypatch):
    """A failed notification must preserve the successful stock transaction."""
    product = _create_notification_product(client, "NOTIFY-FAIL-001")
    monkeypatch.setattr(
        "app.routes.transactions.send_notification",
        lambda recipient, subject, message: False,
    )

    response = client.post("/transactions", json={
        "product_id": product["id"],
        "type": "OUT",
        "quantity": 5,
    })

    assert response.status_code == 201
    transaction = response.get_json()
    assert transaction["notification_sent"] is False
    assert transaction["product_id"] == product["id"]
    assert transaction["type"] == "OUT"
    assert transaction["quantity"] == 5

    stock = client.get(f"/products/{product['id']}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 7

    history = client.get("/transactions").get_json()
    assert len(history) == 1
    assert history[0]["id"] == transaction["id"]
    assert history[0]["product_id"] == product["id"]
    assert history[0]["type"] == "OUT"
    assert history[0]["quantity"] == 5


def test_no_notification_above_reorder_level_mock(client):
    """Stock above the reorder level must not trigger a notification."""
    product = _create_notification_product(client, "NOTIFY-SKIP-001")

    with patch(
        "app.routes.transactions.send_notification", return_value=True
    ) as mock_send:
        response = client.post("/transactions", json={
            "product_id": product["id"],
            "type": "OUT",
            "quantity": 1,
        })

    mock_send.assert_not_called()
    assert response.status_code == 201
    transaction = response.get_json()
    assert transaction["product_id"] == product["id"]
    assert transaction["type"] == "OUT"
    assert transaction["quantity"] == 1

    stock = client.get(f"/products/{product['id']}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 11

    history = client.get("/transactions").get_json()
    assert len(history) == 1
    assert history[0]["id"] == transaction["id"]
    assert history[0]["product_id"] == product["id"]
    assert history[0]["type"] == "OUT"
    assert history[0]["quantity"] == 1
