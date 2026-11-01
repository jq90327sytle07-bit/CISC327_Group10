
def test_list_suppliers(client):
    """Verify that newly created suppliers appear in supplier list."""
    response = client.get("/suppliers")
    assert response.status_code == 200
    assert response.get_json() == []

    client.post("/suppliers", json={
        "name": "Harborview Electronics",
        "contact_email": "orders@harborview.com"
    })

    response = client.get("/suppliers")
    assert response.status_code == 200
    suppliers = response.get_json()
    assert len(suppliers) == 1
    assert suppliers[0]["name"] == "Harborview Electronics"


def test_create_supplier(client):
    """Verify supplier can be created with correct contact details."""
    response = client.post("/suppliers", json={
        "name": "Kingston Supplies",
        "contact_email": "contact@kingstonsupplies.com"
    })

    assert response.status_code == 201
    supplier = response.get_json()
    assert supplier["name"] == "Kingston Supplies"
    assert supplier["contact_email"] == "contact@kingstonsupplies.com"
    assert isinstance(supplier["id"], int)


def test_view_supplier(client):
    """Verify supplier details can be retrieved by ID."""
    created = client.post("/suppliers", json={
        "name": "Test Supplier",
        "contact_email": "test@example.com"
    }).get_json()

    response = client.get(f"/suppliers/{created['id']}")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Test Supplier"
    assert response.get_json()["contact_email"] == "test@example.com"

    # Boundary case: supplier does not exist.
    missing = client.get("/suppliers/999999")
    assert missing.status_code == 404


def test_update_supplier(client):
    """Verify supplier contact information can be updated."""
    created = client.post("/suppliers", json={
        "name": "Original Supplier",
        "contact_email": "old@example.com"
    }).get_json()

    supplier_id = created["id"]

    response = client.put(f"/suppliers/{supplier_id}", json={
        "name": "Updated Supplier",
        "contact_email": "new@example.com"
    })

    assert response.status_code == 200
    assert response.get_json()["name"] == "Updated Supplier"
    assert response.get_json()["contact_email"] == "new@example.com"

    # Confirm changes saved.
    check = client.get(f"/suppliers/{supplier_id}")
    assert check.get_json()["name"] == "Updated Supplier"


def test_delete_supplier(client):
    """Verify deleted supplier can no longer be retrieved."""
    created = client.post("/suppliers", json={
        "name": "Temporary Supplier",
        "contact_email": "temporary@example.com"
    }).get_json()

    supplier_id = created["id"]

    response = client.delete(f"/suppliers/{supplier_id}")
    assert response.status_code == 204

    # supplier should no longer exist.
    check = client.get(f"/suppliers/{supplier_id}")
    assert check.status_code == 404


def test_supplier_products(client):
    """Verify that products received from a supplier appear in its product list."""
    supplier = client.post("/suppliers", json={
        "name": "Electronics Supplier",
        "contact_email": "electronics@example.com"
    }).get_json()

    product = client.post("/products", json={
        "name": "Keyboard",
        "sku": "KEY-001",
        "unit_price": 25,
        "quantity_on_hand": 5,
        "reorder_level": 2
    }).get_json()

    supplier_id = supplier["id"]
    product_id = product["id"]

    # No products have been received from this supplier yet.
    response = client.get(f"/suppliers/{supplier_id}/products")
    assert response.status_code == 200
    assert response.get_json() == []

    # Record incoming stock associated with this supplier.
    transaction = client.post("/transactions", json={
        "product_id": product_id,
        "supplier_id": supplier_id,
        "type": "IN",
        "quantity": 10
    })
    assert transaction.status_code == 201

    # The product should now appear in the supplier's product list.
    response = client.get(f"/suppliers/{supplier_id}/products")
    assert response.status_code == 200

    products = response.get_json()
    assert len(products) == 1
    assert products[0]["id"] == product_id
    assert products[0]["name"] == "Keyboard"


def create_purchase_order_setup(client):
    """Create a supplier and product for purchase-order tests."""
    supplier = client.post("/suppliers", json={
        "name": "Office Supply Company",
        "contact_email": "orders@example.com"
    }).get_json()

    product = client.post("/products", json={
        "name": "Office Chair",
        "sku": "CHAIR-001",
        "unit_price": 75,
        "quantity_on_hand": 10,
        "reorder_level": 3
    }).get_json()

    return supplier["id"], product["id"]


def test_list_purchase_orders(client):
    """Verify that created purchase orders appear in the list."""
    assert client.get("/purchase-orders").get_json() == []

    supplier_id, product_id = create_purchase_order_setup(client)

    response = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 5
    })
    assert response.status_code == 201

    orders = client.get("/purchase-orders")
    assert orders.status_code == 200
    assert len(orders.get_json()) == 1
    assert orders.get_json()[0]["quantity_ordered"] == 5


def test_create_purchase_order(client):
    """Verify a purchase order stores its supplier, product, and quantity."""
    supplier_id, product_id = create_purchase_order_setup(client)

    response = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 8
    })

    assert response.status_code == 201
    order = response.get_json()
    assert order["supplier_id"] == supplier_id
    assert order["product_id"] == product_id
    assert order["quantity_ordered"] == 8
    assert order["status"] == "pending"

    # An unknown supplier should be rejected.
    invalid = client.post("/purchase-orders", json={
        "supplier_id": 999999,
        "product_id": product_id,
        "quantity_ordered": 8
    })
    assert invalid.status_code == 404


def test_view_purchase_order(client):
    """Verify an order can be retrieved using its ID."""
    supplier_id, product_id = create_purchase_order_setup(client)

    created = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 6
    }).get_json()

    response = client.get(f"/purchase-orders/{created['id']}")

    assert response.status_code == 200
    assert response.get_json()["quantity_ordered"] == 6
    assert response.get_json()["status"] == "pending"

    # An unknown order should return 404.
    missing = client.get("/purchase-orders/999999")
    assert missing.status_code == 404


def test_receive_purchase_order_updates_stock(client):
    """Verify receiving an order records incoming stock and updates inventory."""
    supplier_id, product_id = create_purchase_order_setup(client)

    created = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 5
    }).get_json()

    order_id = created["id"]

    response = client.put(f"/purchase-orders/{order_id}/receive")
    assert response.status_code == 200
    assert response.get_json()["status"] == "received"
    assert response.get_json()["received_date"] is not None

    # Check that receiving the order creates an incoming transaction.
    transactions = client.get("/transactions").get_json()
    assert any(
        t["product_id"] == product_id
        and t["supplier_id"] == supplier_id
        and t["type"] == "IN"
        and t["quantity"] == 5
        for t in transactions
    )

    # Stock should increase from 10 to 15 after receiving 5 units.
    stock = client.get(f"/products/{product_id}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 15


def test_receiving_purchase_order_twice_does_not_duplicate_stock(client):
    """Verify receiving the same order twice does not add stock twice."""
    supplier_id, product_id = create_purchase_order_setup(client)

    order = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 5
    }).get_json()

    order_id = order["id"]

    # First receipt should increase stock from 10 to 15.
    first = client.put(f"/purchase-orders/{order_id}/receive")
    assert first.status_code == 200

    # Receiving the same order again should be rejected.
    second = client.put(f"/purchase-orders/{order_id}/receive")
    assert second.status_code == 400

    # Stock must not increase a second time.
    stock = client.get(f"/products/{product_id}/stock-level")
    assert stock.status_code == 200
    assert stock.get_json()["quantity_on_hand"] == 15

    # Only one incoming transaction should have been recorded.
    transactions = client.get("/transactions").get_json()
    assert len(transactions) == 1
    assert transactions[0]["type"] == "IN"
    assert transactions[0]["quantity"] == 5


def test_receiving_multiple_purchase_orders_accumulates_stock(client):
    """Verify separate purchase orders correctly accumulate inventory."""
    supplier_id, product_id = create_purchase_order_setup(client)

    first_order = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 5
    }).get_json()

    second_order = client.post("/purchase-orders", json={
        "supplier_id": supplier_id,
        "product_id": product_id,
        "quantity_ordered": 8
    }).get_json()

    # Creating pending orders must not change stock.
    before = client.get(f"/products/{product_id}/stock-level")
    assert before.get_json()["quantity_on_hand"] == 10

    # Receive the first order: 10 + 5 = 15.
    first = client.put(f"/purchase-orders/{first_order['id']}/receive")
    assert first.status_code == 200

    middle = client.get(f"/products/{product_id}/stock-level")
    assert middle.get_json()["quantity_on_hand"] == 15

    # Receive the second order: 15 + 8 = 23.
    second = client.put(f"/purchase-orders/{second_order['id']}/receive")
    assert second.status_code == 200

    after = client.get(f"/products/{product_id}/stock-level")
    assert after.get_json()["quantity_on_hand"] == 23

    # Each received order should create its own incoming transaction.
    transactions = client.get("/transactions").get_json()
    assert len(transactions) == 2
    assert sorted(t["quantity"] for t in transactions) == [5, 8]
