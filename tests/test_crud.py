from __future__ import annotations


def test_reference_data_crud(admin_client):
    group = admin_client.post(
        "/api/groups",
        json={"name": "ТЕСТ-26-1-бзу", "course": 1, "curator_id": None},
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]
    assert group.json()["student_count"] == 0

    updated_group = admin_client.patch(
        f"/api/groups/{group_id}",
        json={"course": 2},
    )
    assert updated_group.status_code == 200
    assert updated_group.json()["course"] == 2

    teacher = admin_client.post(
        "/api/teachers",
        json={
            "username": "test.teacher",
            "password": "secret123",
            "full_name": "Тестов Тест Тестович",
            "department": "ИТАС",
            "position": "ассистент",
        },
    )
    assert teacher.status_code == 201, teacher.text
    teacher_id = teacher.json()["id"]
    assert teacher.json()["subject_count"] == 0

    subject = admin_client.post(
        "/api/subjects",
        json={
            "code": "TEST",
            "title": "Тестовая дисциплина",
            "description": "Дисциплина для автоматического теста",
            "hours": 72,
            "teacher_id": teacher_id,
        },
    )
    assert subject.status_code == 201, subject.text
    subject_id = subject.json()["id"]
    assert subject.json()["teacher_name"] == "Тестов Тест Тестович"
    assert subject.json()["teacher_count"] == 1

    student = admin_client.post(
        "/api/students",
        json={
            "username": "test.student",
            "password": "secret123",
            "full_name": "Студентов Студент Студентович",
            "group_id": group_id,
            "record_book_no": "26-999",
            "email": "test.student@example.com",
            "phone": "+7 (900) 000-00-00",
        },
    )
    assert student.status_code == 201, student.text
    student_id = student.json()["id"]
    assert student.json()["group_name"] == "ТЕСТ-26-1-бзу"

    students = admin_client.get("/api/students", params={"search": "Студентов"})
    assert students.status_code == 200
    assert any(item["id"] == student_id for item in students.json())

    # Удаление преподавателя обнуляет ссылку в дисциплине, но не удаляет её.
    assert admin_client.delete(f"/api/teachers/{teacher_id}").status_code == 204
    subjects = admin_client.get("/api/subjects").json()
    subject_after = next(item for item in subjects if item["id"] == subject_id)
    assert subject_after["teacher_id"] is None

    assert admin_client.delete(f"/api/students/{student_id}").status_code == 204
    assert admin_client.delete(f"/api/subjects/{subject_id}").status_code == 204
    assert admin_client.delete(f"/api/groups/{group_id}").status_code == 204

    groups = admin_client.get("/api/groups").json()
    assert all(item["id"] != group_id for item in groups)


def test_duplicate_group_returns_conflict(admin_client):
    first = admin_client.post("/api/groups", json={"name": "ДУБЛЬ-1", "course": 1})
    assert first.status_code == 201
    second = admin_client.post("/api/groups", json={"name": "ДУБЛЬ-1", "course": 1})
    assert second.status_code == 409
    assert second.json()["code"] == "duplicate"
    admin_client.delete(f"/api/groups/{first.json()['id']}")


def test_validation_error_has_uniform_format(admin_client):
    response = admin_client.post(
        "/api/groups",
        json={"name": "x", "course": 99},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "detail" in body


def test_dashboard_contains_seeded_statistics(admin_client):
    response = admin_client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["students"] >= 12
    assert data["groups"] >= 3
    assert data["subjects"] >= 5
    assert data["lessons"] >= 30
    assert data["grades"] >= 100
    assert data["average_grade"] is not None
