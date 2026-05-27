"""
Tests for purchase order API endpoints.

Note: purchase orders live in-memory and backlog items are a small fixed set,
so each test uses a distinct backlog item id to stay independent.
"""


def _create_po(client, backlog_item_id, quantity=100, unit_cost=25.5):
    """Helper to create a purchase order for a backlog item."""
    return client.post(
        "/api/purchase-orders",
        json={
            "backlog_item_id": backlog_item_id,
            "supplier_name": "Acme Industrial Supply",
            "quantity": quantity,
            "unit_cost": unit_cost,
            "expected_delivery_date": "2026-06-15",
            "notes": "Expedited order",
        },
    )


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_get_purchase_order_before_creation(self, client):
        """Test that an item without a purchase order returns 404."""
        response = client.get("/api/purchase-orders/4")
        assert response.status_code == 404
        assert "no purchase order" in response.json()["detail"].lower()

    def test_create_purchase_order(self, client):
        """Test creating a purchase order for a backlog item."""
        response = _create_po(client, backlog_item_id="1", quantity=350, unit_cost=12.75)
        assert response.status_code == 200

        po = response.json()
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Industrial Supply"
        assert po["quantity"] == 350
        assert abs(po["unit_cost"] - 12.75) < 0.01
        assert po["expected_delivery_date"] == "2026-06-15"
        assert po["status"] == "Submitted"
        assert po["id"].startswith("PO-")
        assert po["created_date"]
        assert po["notes"] == "Expedited order"

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test fetching the purchase order for a backlog item."""
        created = _create_po(client, backlog_item_id="2").json()

        response = client.get("/api/purchase-orders/2")
        assert response.status_code == 200

        po = response.json()
        assert po["id"] == created["id"]
        assert po["backlog_item_id"] == "2"

    def test_duplicate_purchase_order_rejected(self, client):
        """Test that a backlog item can only have one purchase order."""
        first = _create_po(client, backlog_item_id="3")
        assert first.status_code == 200

        duplicate = _create_po(client, backlog_item_id="3")
        assert duplicate.status_code == 400
        assert "already exists" in duplicate.json()["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test creating a purchase order for a nonexistent backlog item."""
        response = _create_po(client, backlog_item_id="nonexistent-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_purchase_order_invalid_quantity(self, client):
        """Test that a non-positive quantity is rejected."""
        response = _create_po(client, backlog_item_id="4", quantity=0)
        assert response.status_code == 400
        assert "quantity" in response.json()["detail"].lower()

    def test_create_purchase_order_missing_fields(self, client):
        """Test that missing required fields fail validation."""
        response = client.post(
            "/api/purchase-orders",
            json={"backlog_item_id": "4", "supplier_name": "Acme"},
        )
        assert response.status_code == 422

    def test_backlog_reflects_purchase_orders(self, client):
        """Test that backlog items expose the purchase order linkage."""
        # Ensure item 1 has a purchase order regardless of test ordering
        # (returns 400 if an earlier test already created one — both are fine here)
        _create_po(client, backlog_item_id="1")

        response = client.get("/api/backlog")
        assert response.status_code == 200

        items = {item["id"]: item for item in response.json()}

        assert items["1"]["has_purchase_order"] is True
        assert items["1"]["purchase_order_id"] is not None

        assert items["4"]["has_purchase_order"] is False
        assert items["4"]["purchase_order_id"] is None

    def test_purchase_order_ids_unique(self, client):
        """Test that purchase orders get distinct ids."""
        response = client.get("/api/backlog")
        po_ids = [
            item["purchase_order_id"]
            for item in response.json()
            if item["purchase_order_id"]
        ]
        assert len(po_ids) == len(set(po_ids))
