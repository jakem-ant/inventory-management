"""
Tests for reports API endpoints (quarterly performance, monthly trends).
"""


class TestQuarterlyReportsEndpoint:
    """Test suite for the /api/reports/quarterly endpoint."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify structure of each quarter entry
        for quarter in data:
            assert "quarter" in quarter
            assert "total_orders" in quarter
            assert "total_revenue" in quarter
            assert "avg_order_value" in quarter
            assert "fulfillment_rate" in quarter
            assert isinstance(quarter["total_orders"], int)
            assert isinstance(quarter["total_revenue"], (int, float))
            assert isinstance(quarter["avg_order_value"], (int, float))
            assert isinstance(quarter["fulfillment_rate"], (int, float))

    def test_quarterly_reports_sorted_by_quarter(self, client):
        """Test that quarterly reports are sorted chronologically."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that average order value matches revenue / order count."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            if quarter["total_orders"] > 0:
                expected_avg = quarter["total_revenue"] / quarter["total_orders"]
                assert abs(quarter["avg_order_value"] - expected_avg) < 0.01

    def test_quarterly_fulfillment_rate_range(self, client):
        """Test that fulfillment rates are valid percentages."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            assert 0 <= quarter["fulfillment_rate"] <= 100

    def test_quarterly_reports_match_orders_totals(self, client):
        """Test that quarterly aggregates match the raw orders data."""
        orders_response = client.get("/api/orders")
        all_orders = orders_response.json()
        # The quarterly report only covers orders dated in 2025
        orders_2025 = [o for o in all_orders if o.get("order_date", "").startswith("2025-")]

        response = client.get("/api/reports/quarterly")
        data = response.json()

        total_orders = sum(q["total_orders"] for q in data)
        total_revenue = sum(q["total_revenue"] for q in data)

        assert total_orders == len(orders_2025)
        expected_revenue = sum(o["total_value"] for o in orders_2025)
        assert abs(total_revenue - expected_revenue) < 0.01

    def test_quarterly_reports_filter_by_warehouse(self, client):
        """Test filtering quarterly reports by warehouse."""
        warehouse = "Tokyo"
        orders_response = client.get(f"/api/orders?warehouse={warehouse}")
        warehouse_orders = [
            o for o in orders_response.json()
            if o.get("order_date", "").startswith("2025-")
        ]

        response = client.get(f"/api/reports/quarterly?warehouse={warehouse}")
        assert response.status_code == 200
        data = response.json()

        total_orders = sum(q["total_orders"] for q in data)
        assert total_orders == len(warehouse_orders)

    def test_quarterly_reports_filter_by_status(self, client):
        """Test that filtering by delivered status yields 100% fulfillment."""
        response = client.get("/api/reports/quarterly?status=delivered")
        assert response.status_code == 200
        data = response.json()

        # Every remaining order is delivered, so each quarter is fully fulfilled
        for quarter in data:
            assert quarter["fulfillment_rate"] == 100.0

    def test_quarterly_reports_filter_by_month(self, client):
        """Test that a single month filter restricts results to its quarter."""
        response = client.get("/api/reports/quarterly?month=2025-01")
        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 1
        if data:
            assert data[0]["quarter"] == "Q1-2025"

    def test_quarterly_reports_filter_by_quarter(self, client):
        """Test filtering quarterly reports by quarter period."""
        response = client.get("/api/reports/quarterly?month=Q2-2025")
        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 1
        if data:
            assert data[0]["quarter"] == "Q2-2025"

    def test_quarterly_reports_all_filter_values(self, client):
        """Test that 'all' filter values behave like no filters."""
        unfiltered = client.get("/api/reports/quarterly").json()
        filtered = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()

        assert filtered == unfiltered

    def test_quarterly_reports_no_matching_orders(self, client):
        """Test that a filter matching nothing returns an empty list."""
        response = client.get("/api/reports/quarterly?warehouse=Nonexistent Warehouse")
        assert response.status_code == 200
        assert response.json() == []


class TestMonthlyTrendsEndpoint:
    """Test suite for the /api/reports/monthly-trends endpoint."""

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        for month in data:
            assert "month" in month
            assert "order_count" in month
            assert "revenue" in month
            assert "delivered_count" in month
            assert isinstance(month["order_count"], int)
            assert isinstance(month["revenue"], (int, float))
            assert isinstance(month["delivered_count"], int)
            # Month should be in YYYY-MM format
            assert len(month["month"]) == 7
            assert month["month"][4] == "-"

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that monthly trends are sorted chronologically."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [m["month"] for m in data]
        assert months == sorted(months)

    def test_monthly_trends_match_orders_totals(self, client):
        """Test that monthly aggregates match the raw orders data."""
        orders_response = client.get("/api/orders")
        all_orders = orders_response.json()
        orders_with_dates = [o for o in all_orders if o.get("order_date")]

        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        total_orders = sum(m["order_count"] for m in data)
        total_revenue = sum(m["revenue"] for m in data)

        assert total_orders == len(orders_with_dates)
        expected_revenue = sum(o["total_value"] for o in orders_with_dates)
        assert abs(total_revenue - expected_revenue) < 0.01

    def test_monthly_trends_delivered_count_valid(self, client):
        """Test that delivered counts never exceed total order counts."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for month in data:
            assert 0 <= month["delivered_count"] <= month["order_count"]

    def test_monthly_trends_filter_by_month(self, client):
        """Test filtering monthly trends to a single month."""
        response = client.get("/api/reports/monthly-trends?month=2025-03")
        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 1
        if data:
            assert data[0]["month"] == "2025-03"

    def test_monthly_trends_filter_by_quarter(self, client):
        """Test filtering monthly trends by quarter period."""
        response = client.get("/api/reports/monthly-trends?month=Q1-2025")
        assert response.status_code == 200
        data = response.json()

        assert len(data) <= 3
        for month in data:
            assert month["month"] in ["2025-01", "2025-02", "2025-03"]

    def test_monthly_trends_filter_by_warehouse(self, client):
        """Test filtering monthly trends by warehouse."""
        warehouse = "London"
        orders_response = client.get(f"/api/orders?warehouse={warehouse}")
        warehouse_orders = [o for o in orders_response.json() if o.get("order_date")]

        response = client.get(f"/api/reports/monthly-trends?warehouse={warehouse}")
        assert response.status_code == 200
        data = response.json()

        total_orders = sum(m["order_count"] for m in data)
        assert total_orders == len(warehouse_orders)

    def test_monthly_trends_multiple_filters(self, client):
        """Test monthly trends with multiple filters combined."""
        query = "warehouse=San Francisco&category=sensors&status=delivered"
        orders_response = client.get(f"/api/orders?{query}")
        matching_orders = [o for o in orders_response.json() if o.get("order_date")]

        response = client.get(f"/api/reports/monthly-trends?{query}")
        assert response.status_code == 200
        data = response.json()

        total_orders = sum(m["order_count"] for m in data)
        assert total_orders == len(matching_orders)

        # Everything is delivered, so delivered counts equal order counts
        for month in data:
            assert month["delivered_count"] == month["order_count"]

    def test_monthly_trends_no_matching_orders(self, client):
        """Test that a filter matching nothing returns an empty list."""
        response = client.get("/api/reports/monthly-trends?warehouse=Nonexistent Warehouse")
        assert response.status_code == 200
        assert response.json() == []
