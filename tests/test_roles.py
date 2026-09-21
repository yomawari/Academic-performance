from __future__ import annotations


def test_student_cannot_create_teacher(student_client):
    response = student_client.post(
        "/api/teachers",
        json={
            "username": "forbidden.teacher",
            "password": "secret123",
            "full_name": "Запрещённый Преподаватель",
            "department": "ИТАС",
            "position": "Ассистент",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_teacher_cannot_create_group(teacher_client):
    response = teacher_client.post(
        "/api/groups",
        json={"name": "Запрещённая группа", "course": 1},
    )
    assert response.status_code == 403


def test_student_sees_only_own_card(student_client):
    response = student_client.get("/api/students")
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 1
    assert students[0]["username"] == "student"

    other = student_client.get(f"/api/students/{students[0]['id'] + 1}")
    assert other.status_code == 403


def test_teacher_can_read_reference_data(teacher_client):
    assert teacher_client.get("/api/groups").status_code == 200
    assert teacher_client.get("/api/students").status_code == 200
    assert teacher_client.get("/api/subjects").status_code == 200
    assert teacher_client.get("/api/teachers").status_code == 200
    assert teacher_client.get("/api/dashboard").status_code == 200
