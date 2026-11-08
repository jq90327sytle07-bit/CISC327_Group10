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

