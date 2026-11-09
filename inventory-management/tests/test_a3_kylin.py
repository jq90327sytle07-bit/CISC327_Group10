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