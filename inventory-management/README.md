# Inventory Management System (IMS)

A small Flask REST API for tracking products, suppliers, and stock transactions.
Data is stored **in memory** (plain Python objects, no database) and is reset
every time the app restarts — this project is meant to run before you've
covered databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete products and suppliers, and
record stock transactions:

| Page | Path |
|---|---|
| Home | `/` |
| Products | `/ui/products` |
| Suppliers | `/ui/suppliers` |
| Transactions | `/ui/transactions` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.

## Entities

- **Product**: `id, name, sku, unit_price, quantity_on_hand`
- **Supplier**: `id, name, contact_email`
- **Transaction**: `id, product_id, supplier_id, type (IN/OUT), quantity, transaction_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/products` | List all products |
| POST | `/products` | Create a product |
| GET | `/products/<id>` | Get one product |
| PUT | `/products/<id>` | Update a product |
| DELETE | `/products/<id>` | Delete a product |
| GET | `/products/<id>/stock-level` | Current quantity on hand |
| GET | `/suppliers` | List all suppliers |
| POST | `/suppliers` | Create a supplier |
| GET | `/suppliers/<id>` | Get one supplier |
| PUT | `/suppliers/<id>` | Update a supplier |
| DELETE | `/suppliers/<id>` | Delete a supplier |
| POST | `/transactions` | Record a stock movement (`product_id`, `type`: IN/OUT, `quantity`, optional `supplier_id`) |
| GET | `/transactions?product_id=&supplier_id=` | Look up transactions |
| GET | `/reports/fast-moving-products` | Rank current products by total outgoing quantity |
| GET | `/purchase-orders` | List all purchase orders |
| POST | `/purchase-orders` | Create a purchase order for a supplier and product |
| GET | `/purchase-orders/<id>` | Get one purchase order |
| PUT | `/purchase-orders/<id>/receive` | Receive a purchase order, record an incoming transaction, and automatically increase the product's stock quantity (FR-04); prevents duplicate receiving |

## Fast-Moving Products Report

GET /reports/fast-moving-products

Returns current products with recorded OUT transactions, ranked by total
outgoing quantity in descending order. Multiple OUT transactions for the
same product are combined. IN transactions are excluded. Ties are ordered
by product ID in ascending order.

Each result contains product_id, product_name, and total_outgoing.
Returns an empty list when no qualifying outgoing transactions exist.

The report uses all transactions currently held in memory. Application
data is cleared when the application restarts.

## Tests

Run the application regression tests and their existing coverage check:

```bash
python -m pytest -v --ignore=tests/e2e --cov=app --cov-report=term-missing --cov-fail-under=90
```

### A4 browser E2E tests

Prerequisites: Python 3.11, the dependencies in `requirements.txt`, and Chromium
installed for Playwright:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

From `inventory-management`, start Flask in one terminal:

```bash
python -m flask --app run:app run --host 127.0.0.1 --port 5000
```

Keep it running and execute the browser tests in a second terminal, using the
same Python environment:

```bash
python -m pytest tests/e2e -v --headed
```

The tests open Chromium, interact with the existing HTML forms, and check the
visible transaction history and inventory. Each member contributes a separate
`tests/e2e/test_a4_<name>.py` file. To run Kylin's two scenarios:

```bash
python -m pytest tests/e2e/test_a4_kylin.py -v --headed
```

`pytest.ini` defaults to `http://127.0.0.1:5000`. Override the target without
changing the test code when using another host port:

```bash
python -m pytest tests/e2e -v --headed --base-url http://127.0.0.1:5001
```

Each Kylin test creates its own product through the UI, using a unique SKU, and
removes that product during teardown. Transaction assertions use that product's
ID, so unrelated records and test order do not affect the expected result.
Transaction history remains in memory until the server restarts. The invalid
quantity scenario tests the existing browser validation; it does not claim
that the JSON API rejects zero quantities.

Optional debugging outputs:

```bash
python -m pytest tests/e2e -v --headed --screenshot only-on-failure --tracing retain-on-failure
```

Generated outputs in `test-results/` are ignored by Git and excluded from the
Docker build context. For the assignment video, use a screen recording that
shows both the headed browser automation and terminal results.

GitHub Actions runs regression tests and browser E2E tests in separate jobs.
The regression job retains the 90% `app/` coverage threshold. The browser job
installs Chromium and starts a real Flask HTTP server before running E2E tests.

### Docker build, run, test, and stop

Prerequisites: a running Docker Desktop/Engine and the final A4 `Dockerfile`
and `.dockerignore` in `inventory-management`. The Dockerfile must start Flask
on `0.0.0.0:5000` inside the container. The Playwright tests run on the host,
against the container's published HTTP port.

Stop the local Flask server with Ctrl+C before reusing host port 5000. From
`inventory-management`, build and run the image:

```bash
docker build -t cisc327-a4 .
docker run --rm --name cisc327-a4-app -p 5000:5000 cisc327-a4
```

Leave the container running. In a second terminal, inspect the container and
verify HTTP access, then run the unchanged browser suite:

```bash
docker ps
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').status)"
python -m pytest tests/e2e -v --headed
```

Open `http://127.0.0.1:5000/` to inspect the HTML interface. Stop the named
container when finished:

```bash
docker stop cisc327-a4-app
```

Both members must independently perform and record the final build, run, HTTP
check, and browser tests. Data is in memory: stopping or restarting the
application/container clears all records. No database, volume, or Docker
Compose configuration is required.

### Publish and use the public Docker Hub image

Replace `<dockerhub-user>` and `<tag>` with the actual public repository owner
and the tag identifying the final tested image before running these commands:

```bash
docker login
docker tag cisc327-a4 <dockerhub-user>/cisc327-a4:<tag>
docker push <dockerhub-user>/cisc327-a4:<tag>
```

Record the public Docker Hub repository URL and exact image tag in the group
report. Each member records their publication and independent verification.
The TA can use the published image without building from source:

```bash
docker pull <dockerhub-user>/cisc327-a4:<tag>
docker run --rm --name cisc327-a4-app -p 5000:5000 <dockerhub-user>/cisc327-a4:<tag>
```

Then run the same browser suite from the host. Docker credentials, local
environment files, virtual environments, browser outputs, and recordings must
not be included in the image.
