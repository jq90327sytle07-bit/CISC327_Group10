
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
