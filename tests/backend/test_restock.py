"""
Tests for restocking API endpoints (recommendations and restock orders).
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clean_restock_orders():
    """Reset the in-memory restock orders list around each test.

    Order numbers and IDs derive from list length, so leftover state from a
    previous test would change generated values and break assertions.
    """
    main.restock_orders.clear()
    yield
    main.restock_orders.clear()


@pytest.fixture
def sample_restock_items():
    """Sample line items for creating a restock order."""
    return [
        {
            "sku": "PCB-001",
            "name": "Single Layer PCB Assembly",
            "quantity": 50,
            "unit_cost": 24.99
        },
        {
            "sku": "PSU-501",
            "name": "5V 10A Switching Power Supply",
            "quantity": 10,
            "unit_cost": 18.99
        }
    ]


class TestRestockRecommendationsEndpoint:
    """Test suite for GET /api/restock/recommendations."""

    def test_get_recommendations(self, client):
        """Test getting recommendations with a large budget."""
        response = client.get("/api/restock/recommendations?budget=1000000")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure of first recommendation
        rec = data[0]
        assert "item_sku" in rec
        assert "item_name" in rec
        assert "category" in rec
        assert "unit_cost" in rec
        assert "current_demand" in rec
        assert "forecasted_demand" in rec
        assert "trend" in rec
        assert "recommended_quantity" in rec
        assert "line_total" in rec

    def test_recommendations_fit_within_budget(self, client):
        """Test that total recommended cost never exceeds the budget."""
        budget = 50000
        response = client.get(f"/api/restock/recommendations?budget={budget}")
        assert response.status_code == 200

        data = response.json()
        total = sum(rec["line_total"] for rec in data)
        assert total <= budget

    def test_recommendations_tiny_budget_returns_empty(self, client):
        """Test that a budget too small for any item returns an empty list."""
        response = client.get("/api/restock/recommendations?budget=1")
        assert response.status_code == 200
        assert response.json() == []

    def test_recommendations_zero_budget_returns_empty(self, client):
        """Test that a zero budget returns an empty list."""
        response = client.get("/api/restock/recommendations?budget=0")
        assert response.status_code == 200
        assert response.json() == []

    def test_recommendations_missing_budget_fails(self, client):
        """Test that the budget query param is required."""
        response = client.get("/api/restock/recommendations")
        assert response.status_code == 422

    def test_recommendations_increasing_trend_first(self, client):
        """Test that increasing-trend items are ranked before other trends."""
        response = client.get("/api/restock/recommendations?budget=1000000")
        data = response.json()

        trends = [rec["trend"].lower() for rec in data]
        if "increasing" in trends:
            last_increasing = max(i for i, t in enumerate(trends) if t == "increasing")
            first_other = next((i for i, t in enumerate(trends) if t != "increasing"), None)
            if first_other is not None:
                assert last_increasing < first_other

    def test_recommendations_quantity_and_totals(self, client):
        """Test that recommended quantity matches the demand gap and line totals are correct."""
        response = client.get("/api/restock/recommendations?budget=1000000")
        data = response.json()

        for rec in data:
            gap = rec["forecasted_demand"] - rec["current_demand"]
            assert rec["recommended_quantity"] == gap
            assert rec["recommended_quantity"] > 0
            assert abs(rec["line_total"] - rec["recommended_quantity"] * rec["unit_cost"]) < 0.01

    def test_recommendations_skus_exist_in_inventory(self, client):
        """Test that every recommended SKU has a matching inventory record (pricing source)."""
        inventory_response = client.get("/api/inventory")
        inventory_skus = {item["sku"] for item in inventory_response.json()}

        response = client.get("/api/restock/recommendations?budget=1000000")
        data = response.json()

        for rec in data:
            assert rec["item_sku"] in inventory_skus


class TestRestockOrdersEndpoints:
    """Test suite for POST/GET /api/restock/orders."""

    def test_create_restock_order(self, client, sample_restock_items):
        """Test creating a restock order."""
        response = client.post("/api/restock/orders", json={"items": sample_restock_items})
        assert response.status_code == 200

        order = response.json()
        assert order["id"] == "1"
        assert order["order_number"] == "RST-2025-0001"
        assert order["status"].lower() == "submitted"
        assert len(order["items"]) == 2
        assert "order_date" in order
        assert "expected_delivery" in order
        assert "T" in order["expected_delivery"]  # Has time component

    def test_create_restock_order_total_value(self, client, sample_restock_items):
        """Test that the order total matches the sum of its line items."""
        response = client.post("/api/restock/orders", json={"items": sample_restock_items})
        order = response.json()

        expected_total = sum(item["quantity"] * item["unit_cost"] for item in sample_restock_items)
        assert abs(order["total_value"] - expected_total) < 0.01

    def test_create_restock_order_lead_time(self, client, sample_restock_items):
        """Test that lead time uses the slowest category in the order."""
        response = client.post("/api/restock/orders", json={"items": sample_restock_items})
        order = response.json()

        # PCB-001 is Circuit Boards (14 days), PSU-501 is Power Supplies (default 14 days)
        assert order["lead_time_days"] == 14
        # Expected delivery date should be after the order date
        assert order["expected_delivery"] > order["order_date"]

    def test_create_restock_order_empty_items_rejected(self, client):
        """Test that an order with no items returns 400."""
        response = client.post("/api/restock/orders", json={"items": []})
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_create_restock_order_invalid_body_rejected(self, client):
        """Test that a malformed request body returns a validation error."""
        response = client.post("/api/restock/orders", json={"items": [{"sku": "PCB-001"}]})
        assert response.status_code == 422

    def test_get_restock_orders_empty(self, client):
        """Test listing restock orders when none have been created."""
        response = client.get("/api/restock/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_restock_orders_after_create(self, client, sample_restock_items):
        """Test that created orders appear in the list with sequential order numbers."""
        client.post("/api/restock/orders", json={"items": sample_restock_items})
        client.post("/api/restock/orders", json={"items": sample_restock_items})

        response = client.get("/api/restock/orders")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["order_number"] == "RST-2025-0001"
        assert data[1]["order_number"] == "RST-2025-0002"

    def test_recommendations_can_be_submitted_as_order(self, client):
        """Test the end-to-end flow: recommendations feed directly into order creation."""
        rec_response = client.get("/api/restock/recommendations?budget=100000")
        recommendations = rec_response.json()
        assert len(recommendations) > 0

        items = [
            {
                "sku": rec["item_sku"],
                "name": rec["item_name"],
                "quantity": rec["recommended_quantity"],
                "unit_cost": rec["unit_cost"]
            }
            for rec in recommendations
        ]

        order_response = client.post("/api/restock/orders", json={"items": items})
        assert order_response.status_code == 200

        order = order_response.json()
        expected_total = sum(rec["line_total"] for rec in recommendations)
        assert abs(order["total_value"] - expected_total) < 0.01
