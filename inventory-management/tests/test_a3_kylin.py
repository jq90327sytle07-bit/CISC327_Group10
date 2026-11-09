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