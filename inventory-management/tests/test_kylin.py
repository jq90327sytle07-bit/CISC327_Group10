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
