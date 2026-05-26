"""
Tests for tasks API endpoints (the "My Tasks" modal backend).
"""


def _create_task(client, title="Test task", priority="high", due_date="2025-11-30"):
    """Helper to create a task and return the response JSON."""
    response = client.post(
        "/api/tasks",
        json={"title": title, "priority": priority, "dueDate": due_date},
    )
    assert response.status_code == 200
    return response.json()


class TestTasksEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks(self, client):
        """Test getting all tasks returns a list."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_task(self, client):
        """Test creating a task returns it with an id and pending status."""
        task = _create_task(client, title="Review supplier contracts")

        assert "id" in task
        assert task["title"] == "Review supplier contracts"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2025-11-30"
        assert task["status"] == "pending"

    def test_created_task_appears_in_list(self, client):
        """Test that a created task is returned by the list endpoint."""
        task = _create_task(client, title="Check loading dock schedule")

        response = client.get("/api/tasks")
        task_ids = [t["id"] for t in response.json()]
        assert task["id"] in task_ids

    def test_create_task_default_priority(self, client):
        """Test that priority defaults to medium when not provided."""
        response = client.post(
            "/api/tasks",
            json={"title": "Task without priority", "dueDate": "2025-12-01"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "medium"

    def test_create_task_missing_title(self, client):
        """Test that creating a task without a title fails validation."""
        response = client.post("/api/tasks", json={"dueDate": "2025-12-01"})
        assert response.status_code == 422

    def test_task_ids_are_unique(self, client):
        """Test that consecutively created tasks get distinct ids."""
        first = _create_task(client, title="First task")
        second = _create_task(client, title="Second task")
        assert first["id"] != second["id"]

    def test_toggle_task_status(self, client):
        """Test that PATCH toggles a task between pending and completed."""
        task = _create_task(client, title="Toggle me")

        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        # Toggling again flips it back to pending
        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist."""
        response = client.patch("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_task(self, client):
        """Test deleting a task removes it from the list."""
        task = _create_task(client, title="Delete me")

        response = client.delete(f"/api/tasks/{task['id']}")
        assert response.status_code == 200

        task_ids = [t["id"] for t in client.get("/api/tasks").json()]
        assert task["id"] not in task_ids

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist."""
        response = client.delete("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_deleted_task_id_not_reused(self, client):
        """Test that ids stay unique even after a deletion."""
        first = _create_task(client, title="Will be deleted")
        client.delete(f"/api/tasks/{first['id']}")

        second = _create_task(client, title="Created after deletion")
        assert second["id"] != first["id"]
