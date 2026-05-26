from datetime import datetime, timedelta
from itertools import count
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

# Hardcoded delivery lead times (days) by inventory category.
# Used when creating restock orders; the slowest category in the order sets overall lead time.
CATEGORY_LEAD_TIMES_DAYS = {
    "Circuit Boards": 14,
    "Sensors": 10,
    "Actuators": 21,
    "Controllers": 7,
}
DEFAULT_LEAD_TIME_DAYS = 14

# Restock orders live in-memory only — they reset on server restart,
# matching the rest of the mock-data approach in this demo app.
restock_orders: list = []

# User tasks (from the "My Tasks" modal) also live in-memory only.
# The id counter is monotonic so ids stay unique even after deletions.
tasks: list = []
task_id_counter = count(1)

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockRecommendation(BaseModel):
    item_sku: str
    item_name: str
    category: str
    unit_cost: float
    current_demand: int
    forecasted_demand: int
    trend: str
    recommended_quantity: int
    line_total: float

class RestockOrderLineItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockOrderLineItem]
    total_value: float
    lead_time_days: int
    order_date: str
    expected_delivery: str
    status: str

class CreateRestockOrderRequest(BaseModel):
    items: List[RestockOrderLineItem]

# Task fields use camelCase (dueDate) to match the payload the frontend already sends
class Task(BaseModel):
    id: str
    title: str
    priority: str
    dueDate: str
    status: str

class CreateTaskRequest(BaseModel):
    title: str
    priority: str = "medium"
    dueDate: str

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports with optional filtering"""
    # Apply the same global filters used by the other endpoints so the
    # Reports page stays consistent with the filter bar
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    # Calculate quarterly statistics from orders
    quarters = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    months = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

def _build_sku_inventory_map() -> dict:
    """Collapse multi-warehouse inventory rows to a single SKU→{category, unit_cost} record.
    First occurrence wins; in the demo data unit_cost is consistent within a SKU."""
    mapping: dict = {}
    for item in inventory_items:
        sku = item["sku"]
        if sku not in mapping:
            mapping[sku] = {
                "category": item["category"],
                "unit_cost": item["unit_cost"],
            }
    return mapping


@app.get("/api/restock/recommendations", response_model=List[RestockRecommendation])
def get_restock_recommendations(budget: float):
    """Items to restock that fit the given budget.
    Ranks trend='increasing' first, then by demand gap descending. Greedy-fills to budget.
    Demand rows without a matching inventory SKU are skipped (no unit_cost to price them)."""
    if budget <= 0:
        return []

    sku_map = _build_sku_inventory_map()

    candidates = []
    for forecast in demand_forecasts:
        sku = forecast["item_sku"]
        inv = sku_map.get(sku)
        if inv is None:
            continue  # can't price it → can't budget it
        gap = forecast["forecasted_demand"] - forecast["current_demand"]
        if gap <= 0:
            continue  # demand not rising → nothing to restock
        line_total = round(gap * inv["unit_cost"], 2)
        candidates.append({
            "item_sku": sku,
            "item_name": forecast["item_name"],
            "category": inv["category"],
            "unit_cost": inv["unit_cost"],
            "current_demand": forecast["current_demand"],
            "forecasted_demand": forecast["forecasted_demand"],
            "trend": forecast["trend"],
            "recommended_quantity": gap,
            "line_total": line_total,
        })

    # Sort: increasing-trend first (False<True, so invert via not-equal), then bigger gap first.
    candidates.sort(key=lambda c: (c["trend"] != "increasing", -c["recommended_quantity"]))

    # Greedy fill to budget.
    picked = []
    running = 0.0
    for c in candidates:
        if running + c["line_total"] <= budget:
            picked.append(c)
            running += c["line_total"]

    return picked


@app.post("/api/restock/orders", response_model=RestockOrder)
def create_restock_order(req: CreateRestockOrderRequest):
    """Create a restock order. Lead time = slowest per-category lead time across line items."""
    if not req.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    sku_map = _build_sku_inventory_map()

    # Slowest category drives the whole-order lead time — one truck, arrives when the last item does.
    lead_time = DEFAULT_LEAD_TIME_DAYS
    for line in req.items:
        inv = sku_map.get(line.sku)
        category = inv["category"] if inv else None
        days = CATEGORY_LEAD_TIMES_DAYS.get(category, DEFAULT_LEAD_TIME_DAYS)
        if days > lead_time:
            lead_time = days

    now = datetime.now()
    total_value = round(sum(line.quantity * line.unit_cost for line in req.items), 2)
    next_id = len(restock_orders) + 1

    new_order = {
        "id": str(next_id),
        "order_number": f"RST-2025-{next_id:04d}",
        "items": [line.model_dump() for line in req.items],
        "total_value": total_value,
        "lead_time_days": lead_time,
        "order_date": now.isoformat(timespec="seconds"),
        "expected_delivery": (now + timedelta(days=lead_time)).isoformat(timespec="seconds"),
        "status": "Submitted",
    }
    restock_orders.append(new_order)
    return new_order


@app.get("/api/restock/orders", response_model=List[RestockOrder])
def list_restock_orders():
    """Return all submitted restock orders in insertion order."""
    return restock_orders


@app.get("/api/tasks", response_model=List[Task])
def get_tasks():
    """Get all user-created tasks"""
    return tasks


@app.post("/api/tasks", response_model=Task)
def create_task(req: CreateTaskRequest):
    """Create a new task"""
    new_task = {
        # Prefixed id avoids colliding with the numeric ids of the mock tasks bundled in the frontend
        "id": f"task-{next(task_id_counter)}",
        "title": req.title,
        "priority": req.priority,
        "dueDate": req.dueDate,
        "status": "pending",
    }
    tasks.append(new_task)
    return new_task


@app.patch("/api/tasks/{task_id}", response_model=Task)
def toggle_task(task_id: str):
    """Toggle a task between pending and completed"""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    task["status"] = "completed" if task["status"] == "pending" else "pending"
    return task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete a task"""
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.remove(task)
    return {"message": f"Task {task_id} deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
