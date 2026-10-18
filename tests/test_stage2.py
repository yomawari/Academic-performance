from __future__ import annotations


def _teachers(client) -> dict[str, dict]:
    response = client.get("/api/teachers")
    assert response.status_code == 200, response.text
    return {item["username"]: item for item in response.json()}


def _lesson_payload(group_id: int, teacher_id: int | None, topic: str) -> dict:
    return {
        "subject_id": 1,
        "group_id": group_id,
        "teacher_id": teacher_id,
        "lesson_date": "2026-11-02",
        "topic": topic,
        "homework": "Повторить материал",
        "lesson_type": "practice",
    }


def test_lessons_crud_and_student_visibility(client):
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    groups = client.get("/api/groups").json()
    group_id = groups[0]["id"]
    teacher_id = _teachers(client)["teacher"]["id"]

    created = client.post(
        "/api/lessons",
        json=_lesson_payload(group_id, teacher_id, "Тестовое занятие этапа 2"),
    )
    assert created.status_code == 201, created.text
    lesson = created.json()
    lesson_id = lesson["id"]
    assert lesson["group_id"] == group_id
    assert lesson["teacher_name"]
    assert lesson["grades_count"] == 0

    try:
        listed = client.get("/api/lessons", params={"group_id": group_id})
        assert listed.status_code == 200
        assert any(item["id"] == lesson_id for item in listed.json())

        updated = client.patch(
            f"/api/lessons/{lesson_id}",
            json={"topic": "Обновлённая тема", "lesson_type": "lecture"},
        )
        assert updated.status_code == 200
        assert updated.json()["topic"] == "Обновлённая тема"
        assert updated.json()["lesson_type"] == "lecture"

        _teacher_cannot_create_lesson(client, group_id)

        client.post(
            "/api/auth/login", json={"username": "student", "password": "student123"}
        )
        student_lessons = client.get("/api/lessons")
        assert student_lessons.status_code == 200
        me = client.get("/api/students").json()[0]
        assert all(item["group_id"] == me["group_id"] for item in student_lessons.json())
    finally:
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert client.delete(f"/api/lessons/{lesson_id}").status_code == 204


def _teacher_cannot_create_lesson(client, group_id: int) -> None:
    """Преподаватель не управляет расписанием, но может открыть журнал."""
    client.post("/api/auth/login", json={"username": "teacher", "password": "teacher123"})
    response = client.post(
        "/api/lessons",
        json=_lesson_payload(group_id, None, "Недоступное занятие"),
    )
    assert response.status_code == 403
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})


def test_journal_grade_attendance_and_access(admin_client):
    teachers = _teachers(admin_client)
    teacher_id = teachers["teacher"]["id"]
    groups = admin_client.get("/api/groups").json()
    students = admin_client.get("/api/students").json()
    group_id = groups[0]["id"]
    student = next(item for item in students if item["group_id"] == group_id)

    created = admin_client.post(
        "/api/lessons",
        json=_lesson_payload(group_id, teacher_id, "Занятие для журнала"),
    )
    assert created.status_code == 201, created.text
    lesson_id = created.json()["id"]

    try:
        journal = admin_client.get(f"/api/lessons/{lesson_id}/journal")
        assert journal.status_code == 200, journal.text
        assert len(journal.json()["entries"]) == len(
            [item for item in students if item["group_id"] == group_id]
        )

        # Преподаватель-владелец занятия сохраняет оценку и посещаемость.
        admin_client.post(
            "/api/auth/login", json={"username": "teacher", "password": "teacher123"}
        )
        saved = admin_client.put(
            f"/api/lessons/{lesson_id}/journal/{student['id']}",
            json={
                "grade_value": 5,
                "grade_comment": "Отличный ответ",
                "attendance_status": "present",
                "attendance_comment": "",
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["grade_value"] == 5
        assert saved.json()["attendance_status"] == "present"

        # Чужой преподаватель не получает доступ к журналу.
        admin_client.post(
            "/api/auth/login", json={"username": "petrov", "password": "teacher123"}
        )
        assert admin_client.get(f"/api/lessons/{lesson_id}/journal").status_code == 403
        assert (
            admin_client.put(
                f"/api/lessons/{lesson_id}/journal/{student['id']}",
                json={"grade_value": 2},
            ).status_code
            == 403
        )

        # Студенту журнал недоступен.
        admin_client.post(
            "/api/auth/login", json={"username": "student", "password": "student123"}
        )
        assert admin_client.get(f"/api/lessons/{lesson_id}/journal").status_code == 403

        # null удаляет оценку и отметку посещаемости.
        admin_client.post(
            "/api/auth/login", json={"username": "teacher", "password": "teacher123"}
        )
        cleared = admin_client.put(
            f"/api/lessons/{lesson_id}/journal/{student['id']}",
            json={"grade_value": None, "attendance_status": None},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["grade_id"] is None
        assert cleared.json()["attendance_status"] is None

        # Нельзя записать оценку студенту из другой группы.
        stranger = next(item for item in students if item["group_id"] != group_id)
        assert (
            admin_client.put(
                f"/api/lessons/{lesson_id}/journal/{stranger['id']}",
                json={"grade_value": 4},
            ).status_code
            == 404
        )
    finally:
        admin_client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert admin_client.delete(f"/api/lessons/{lesson_id}").status_code == 204


def test_group_report_export_and_student_report(admin_client):
    groups = admin_client.get("/api/groups").json()
    group = groups[0]
    students = admin_client.get("/api/students").json()
    own = next(item for item in students if item["group_id"] == group["id"])
    other = next(item for item in students if item["id"] != own["id"])

    report = admin_client.get(f"/api/reports/groups/{group['id']}")
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["group_id"] == group["id"]
    assert data["group_name"] == group["name"]
    assert data["students"]
    assert {"average_grade", "grades_count", "absences", "lates"} <= set(
        data["students"][0]
    )

    exported = admin_client.get(f"/api/reports/groups/{group['id']}/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "attachment" in exported.headers["content-disposition"]
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert "ФИО;Зачётная книжка" in exported.content.decode("utf-8-sig")

    student_report = admin_client.get(f"/api/reports/students/{own['id']}")
    assert student_report.status_code == 200, student_report.text
    assert student_report.json()["student"]["id"] == own["id"]
    assert "subjects" in student_report.json()
    assert "grades" in student_report.json()

    admin_client.post(
        "/api/auth/login", json={"username": "student", "password": "student123"}
    )
    my_students = admin_client.get("/api/students").json()
    assert len(my_students) == 1
    mine = my_students[0]
    assert admin_client.get(f"/api/reports/students/{mine['id']}").status_code == 200
    assert admin_client.get(f"/api/reports/students/{other['id']}").status_code == 403
    assert admin_client.get(f"/api/reports/groups/{group['id']}").status_code == 403
