
def test_list_suppliers(client):
    """Verify that newly created suppliers appear in the supplier list."""
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
    """Verify that a supplier can be created with correct contact details."""
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
