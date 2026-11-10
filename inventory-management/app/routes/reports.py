from flask import Blueprint, jsonify

from app import store


reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/reports",
)


@reports_bp.route("/fast-moving-products", methods=["GET"])
def fast_moving_products():
    """Rank current products by total recorded outgoing quantity."""
    outgoing_totals = {}

    for transaction in store.transactions.values():
        if transaction.type == "OUT":
            product_id = transaction.product_id
            outgoing_totals[product_id] = (
                outgoing_totals.get(product_id, 0)
                + transaction.quantity
            )

    results = []

    for product_id, total in outgoing_totals.items():
        product = store.products.get(product_id)

        if product is not None:
            results.append({
                "product_id": product.id,
                "product_name": product.name,
                "total_outgoing": total,
            })

    results.sort(
        key=lambda item: (
            -item["total_outgoing"],
            item["product_id"],
        )
    )

    return jsonify(results)