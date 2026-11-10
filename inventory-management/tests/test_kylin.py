"""Tests for Kylin's assigned product, stock, and transaction features."""


def create_product(
    client,
    *,
    name="Widget A",
    sku="WGT-001",
    unit_price=9.99,
    quantity_on_hand=20,
    reorder_level=5,
):
    """Create a product and return its JSON representation."""
    response = client.post(
        "/products",
        json={
            "name": name,
            "sku": sku,
            "unit_price": unit_price,
            "quantity_on_hand": quantity_on_hand,
            "reorder_level": reorder_level,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def create_transaction(client, *, product_id, transaction_type, quantity, supplier_id=None):
    """Record a stock transaction and return the response."""
    payload = {
        "product_id": product_id,
        "type": transaction_type,
        "quantity": quantity,
    }
    if supplier_id is not None:
        payload["supplier_id"] = supplier_id
    return client.post("/transactions", json=payload)


def test_product_lifecycle_persists_and_updates_expected_fields(client):
    """A created product can be listed, viewed, updated, and queried for stock."""
    product = create_product(client)
    product_id = product["id"]

    assert product == {
        "id": product_id,
        "name": "Widget A",
        "sku": "WGT-001",
        "unit_price": 9.99,
        "quantity_on_hand": 20,
        "reorder_level": 5,
    }

    list_response = client.get("/products")
    assert list_response.status_code == 200
    assert list_response.get_json() == [product]

    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 200
    assert get_response.get_json() == product

    update_response = client.put(
        f"/products/{product_id}",
        json={
            "name": "Widget A Plus",
            "unit_price": 12.50,
            "quantity_on_hand": 14,
            "reorder_level": 7,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["name"] == "Widget A Plus"
    assert updated["sku"] == "WGT-001"
    assert updated["unit_price"] == 12.50
    assert updated["quantity_on_hand"] == 14
    assert updated["reorder_level"] == 7

    stock_response = client.get(f"/products/{product_id}/stock-level")
    assert stock_response.status_code == 200
    assert stock_response.get_json() == {
        "product_id": product_id,
        "quantity_on_hand": 14,
    }


def test_delete_product_removes_it_from_subsequent_requests(client):
    """Deleting a product removes it from both list and item endpoints."""
    product = create_product(client)
    product_id = product["id"]

    delete_response = client.delete(f"/products/{product_id}")
    assert delete_response.status_code == 204

    list_response = client.get("/products")
    assert list_response.status_code == 200
    assert list_response.get_json() == []

    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404
    assert get_response.get_json() == {"error": "Product not found"}


def test_unknown_product_operations_return_clear_not_found_errors(client):
    """Product operations reject an ID that is not present in the store."""
    get_response = client.get("/products/999")
    assert get_response.status_code == 404
    assert get_response.get_json() == {"error": "Product not found"}

    update_response = client.put("/products/999", json={"name": "Missing"})
    assert update_response.status_code == 404
    assert update_response.get_json() == {"error": "Product not found"}

    stock_response = client.get("/products/999/stock-level")
    assert stock_response.status_code == 404
    assert stock_response.get_json() == {"error": "Product not found"}

    delete_response = client.delete("/products/999")
    assert delete_response.status_code == 404
    assert delete_response.get_json() == {"error": "Product not found"}


def test_low_stock_list_includes_boundary_and_excludes_healthy_stock(client):
    """Products at or below the reorder level are identified as low stock."""
    below = create_product(
        client,
        name="Below Threshold",
        sku="LOW-001",
        quantity_on_hand=2,
        reorder_level=5,
    )
    at_boundary = create_product(
        client,
        name="At Threshold",
        sku="LOW-002",
        quantity_on_hand=5,
        reorder_level=5,
    )
    healthy = create_product(
        client,
        name="Healthy Stock",
        sku="OK-001",
        quantity_on_hand=6,
        reorder_level=5,
    )

    response = client.get("/products/low-stock")
    assert response.status_code == 200
    low_stock_products = response.get_json()
    returned_ids = {product["id"] for product in low_stock_products}

    assert returned_ids == {below["id"], at_boundary["id"]}
    assert healthy["id"] not in returned_ids


def test_incoming_and_outgoing_transactions_update_stock_and_history(client):
    """A sequence of IN and OUT transactions produces the expected final stock."""
    product = create_product(client, quantity_on_hand=10)
    product_id = product["id"]

    incoming_response = create_transaction(
        client,
        product_id=product_id,
        transaction_type="IN",
        quantity=7,
    )
    assert incoming_response.status_code == 201
    incoming = incoming_response.get_json()
    assert incoming["product_id"] == product_id
    assert incoming["type"] == "IN"
    assert incoming["quantity"] == 7

    stock_after_in = client.get(f"/products/{product_id}/stock-level")
    assert stock_after_in.status_code == 200
    assert stock_after_in.get_json()["quantity_on_hand"] == 17

    outgoing_response = create_transaction(
        client,
        product_id=product_id,
        transaction_type="OUT",
        quantity=4,
    )
    assert outgoing_response.status_code == 201
    outgoing = outgoing_response.get_json()
    assert outgoing["product_id"] == product_id
    assert outgoing["type"] == "OUT"
    assert outgoing["quantity"] == 4

    final_stock = client.get(f"/products/{product_id}/stock-level")
    assert final_stock.status_code == 200
    assert final_stock.get_json()["quantity_on_hand"] == 13

    history_response = client.get("/transactions")
    assert history_response.status_code == 200
    history = history_response.get_json()
    assert [transaction["type"] for transaction in history] == ["IN", "OUT"]
    assert [transaction["quantity"] for transaction in history] == [7, 4]


def test_transaction_for_unknown_product_is_rejected_without_history(client):
    """A transaction cannot be recorded for a product that does not exist."""
    response = create_transaction(
        client,
        product_id=999,
        transaction_type="IN",
        quantity=5,
    )
    assert response.status_code == 404
    assert response.get_json() == {"error": "Product not found"}

    history_response = client.get("/transactions")
    assert history_response.status_code == 200
    assert history_response.get_json() == []


def test_invalid_transaction_type_preserves_stock_and_history(client):
    """An unsupported movement type is rejected without changing inventory."""
    product = create_product(client, quantity_on_hand=10)
    product_id = product["id"]

    response = create_transaction(
        client,
        product_id=product_id,
        transaction_type="TRANSFER",
        quantity=3,
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "type must be IN or OUT"}

    stock_response = client.get(f"/products/{product_id}/stock-level")
    assert stock_response.status_code == 200
    assert stock_response.get_json()["quantity_on_hand"] == 10

    history_response = client.get("/transactions")
    assert history_response.status_code == 200
    assert history_response.get_json() == []


def test_transaction_filter_by_product_returns_only_matching_history(client):
    """The product_id query parameter should select that product's transactions."""
    first_product = create_product(client, name="First", sku="FIRST-001")
    second_product = create_product(client, name="Second", sku="SECOND-001")

    first_transaction = create_transaction(
        client,
        product_id=first_product["id"],
        transaction_type="IN",
        quantity=5,
    ).get_json()
    create_transaction(
        client,
        product_id=second_product["id"],
        transaction_type="OUT",
        quantity=2,
    )

    response = client.get(f"/transactions?product_id={first_product['id']}")
    assert response.status_code == 200
    assert response.get_json() == [first_transaction]


def _create_report_product(client, name, sku):
    response = client.post("/products", json={
        "name": name,
        "sku": sku,
        "unit_price": 10,
        "quantity_on_hand": 20,
        "reorder_level": 2,
    })
    assert response.status_code == 201
    return response.get_json()


def _record_report_transaction(client, product_id, tx_type, quantity):
    response = client.post("/transactions", json={
        "product_id": product_id,
        "type": tx_type,
        "quantity": quantity,
    })
    assert response.status_code == 201


def test_fast_moving_report_aggregates_and_sorts(client):
    """Sum outgoing quantities and rank by quantity, not transaction count."""
    product_a = _create_report_product(client, "Keyboard", "REPORT-A")
    product_b = _create_report_product(client, "Mouse", "REPORT-B")

    _record_report_transaction(client, product_a["id"], "OUT", 3)
    _record_report_transaction(client, product_a["id"], "OUT", 5)
    _record_report_transaction(client, product_b["id"], "OUT", 10)

    response = client.get("/reports/fast-moving-products")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "product_id": product_b["id"],
            "product_name": "Mouse",
            "total_outgoing": 10,
        },
        {
            "product_id": product_a["id"],
            "product_name": "Keyboard",
            "total_outgoing": 8,
        },
    ]


def test_fast_moving_report_excludes_incoming(client):
    """Incoming quantities must not contribute to outgoing totals."""
    product = _create_report_product(client, "Monitor", "REPORT-C")

    _record_report_transaction(client, product["id"], "IN", 50)
    _record_report_transaction(client, product["id"], "OUT", 2)

    response = client.get("/reports/fast-moving-products")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "product_id": product["id"],
            "product_name": "Monitor",
            "total_outgoing": 2,
        },
    ]


def test_fast_moving_report_returns_empty_list(client):
    """Return an empty report when no transactions exist."""
    response = client.get("/reports/fast-moving-products")

    assert response.status_code == 200
    assert response.get_json() == []