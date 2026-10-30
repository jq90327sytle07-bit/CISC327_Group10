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

```bash
pytest
```
