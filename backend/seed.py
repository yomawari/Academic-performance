"""Демонстрационные данные для «Учёта успеваемости».

Запуск:
    python -m backend.seed          # заполнить пустую базу
    python -m backend.seed --force  # пересоздать демонстрационную базу
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from backend.app import config
from backend.app.db import init_db, session
from backend.app.security import hash_password

SUBJECTS = [
    ("TRPP", "Технологии разработки программного обеспечения", "Проектирование, разработка и сопровождение программных систем.", 144),
    ("DB", "Базы данных", "Реляционные и нереляционные СУБД, проектирование и оптимизация запросов.", 108),
    ("WEB", "Веб-программирование", "Клиент-серверная разработка, HTML, CSS, JavaScript и REST API.", 108),
    ("OOP", "Объектно-ориентированное программирование", "Принципы ООП, SOLID, паттерны проектирования.", 144),
    ("MATH", "Математический анализ", "Дифференциальное и интегральное исчисление, ряды.", 180),
]

TEACHERS = [
    ("teacher", "teacher123", "Иванова Мария Сергеевна", "ИТАС", "старший преподаватель"),
    ("petrov", "teacher123", "Петров Алексей Николаевич", "ИТАС", "доцент"),
    ("sokolova", "teacher123", "Соколова Елена Викторовна", "ВМиМ", "преподаватель"),
]

GROUPS = [
    ("РИС-23-1-бзу", 3, 1),
    ("РИС-23-2-бзу", 3, 2),
    ("ИВТ-24-1-бзу", 2, 3),
]

STUDENTS = [
    ("student", "student123", "Смирнов Даниил Алексеевич", 1, "23-001", "d.smirnov@example.com", "+7 (902) 111-01-01"),
    ("p.kuznetsova", "student123", "Кузнецова Полина Игоревна", 1, "23-002", "p.kuznetsova@example.com", "+7 (902) 111-01-02"),
    ("a.volkov", "student123", "Волков Артём Сергеевич", 1, "23-003", "a.volkov@example.com", "+7 (902) 111-01-03"),
    ("m.zakharova", "student123", "Захарова Мария Дмитриевна", 1, "23-004", "m.zakharova@example.com", "+7 (902) 111-01-04"),
    ("k.morozov", "student123", "Морозов Кирилл Андреевич", 2, "23-011", "k.morozov@example.com", "+7 (902) 111-02-01"),
    ("a.pavlova", "student123", "Павлова Анна Викторовна", 2, "23-012", "a.pavlova@example.com", "+7 (902) 111-02-02"),
    ("m.lebedev", "student123", "Лебедев Максим Олегович", 2, "23-013", "m.lebedev@example.com", "+7 (902) 111-02-03"),
    ("s.nikitina", "student123", "Никитина Софья Павловна", 2, "23-014", "s.nikitina@example.com", "+7 (902) 111-02-04"),
    ("i.fedorov", "student123", "Фёдоров Илья Романович", 3, "24-101", "i.fedorov@example.com", "+7 (902) 111-03-01"),
    ("d.egorova", "student123", "Егорова Дарья Алексеевна", 3, "24-102", "d.egorova@example.com", "+7 (902) 111-03-02"),
    ("n.solovev", "student123", "Соловьёв Никита Иванович", 3, "24-103", "n.solovev@example.com", "+7 (902) 111-03-03"),
    ("e.vinogradova", "student123", "Виноградова Елена Сергеевна", 3, "24-104", "e.vinogradova@example.com", "+7 (902) 111-03-04"),
]

# Учебный план: группа -> дисциплины
CURRICULUM = {
    1: ["TRPP", "DB", "WEB", "OOP", "MATH"],
    2: ["TRPP", "DB", "OOP", "MATH"],
    3: ["TRPP", "DB", "WEB", "MATH"],
}

GRADE_PATTERN = [5, 4, 4, 5, 3, 4, 5, 4, 3, 5, 4, 4]
LESSON_TYPES = ["lecture", "practice", "lab", "test"]
TOPICS = {
    "TRPP": ["Жизненный цикл ПО", "Требования и проектирование", "Тестирование и сопровождение"],
    "DB": ["Реляционная модель данных", "SQL и нормализация", "Транзакции и индексы"],
    "WEB": ["Семантика HTML и CSS", "JavaScript и DOM", "REST API и безопасность"],
    "OOP": ["Классы и инкапсуляция", "Наследование и полиморфизм", "SOLID и паттерны"],
    "MATH": ["Пределы и непрерывность", "Производная и интеграл", "Ряды и сходимость"],
}


def _clear(conn) -> None:
    for table in (
        "audit_log",
        "attendance",
        "grades",
        "lessons",
        "group_subject",
        "teacher_subject",
        "students",
        "subjects",
        "groups",
        "teachers",
        "users",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM sqlite_sequence")


def seed_data(path: Path | None = None, *, force: bool = False) -> bool:
    init_db(path)
    with session(path) as conn:
        if force:
            _clear(conn)
        elif conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return False

        now = "2026-09-01 09:00:00"
        admin_id = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, 'admin', ?)
            """,
            ("admin", hash_password("admin123"), "Администратор системы", now),
        ).lastrowid

        teacher_ids: dict[str, int] = {}
        for username, password, full_name, department, position in TEACHERS:
            user_id = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, 'teacher', ?)
                """,
                (username, hash_password(password), full_name, now),
            ).lastrowid
            teacher_id = conn.execute(
                "INSERT INTO teachers (user_id, department, position) VALUES (?, ?, ?)",
                (user_id, department, position),
            ).lastrowid
            teacher_ids[username] = int(teacher_id)

        group_ids: dict[int, int] = {}
        for index, (name, course, curator_number) in enumerate(GROUPS, start=1):
            curator_username = TEACHERS[curator_number - 1][0]
            group_ids[index] = int(
                conn.execute(
                    "INSERT INTO groups (name, course, curator_id) VALUES (?, ?, ?)",
                    (name, course, teacher_ids[curator_username]),
                ).lastrowid
            )

        student_ids: dict[int, list[int]] = {1: [], 2: [], 3: []}
        for username, password, full_name, group_no, record_book, email, phone in STUDENTS:
            user_id = conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, 'student', ?)
                """,
                (username, hash_password(password), full_name, now),
            ).lastrowid
            student_id = conn.execute(
                """
                INSERT INTO students (user_id, group_id, record_book_no, email, phone)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, group_ids[group_no], record_book, email, phone),
            ).lastrowid
            student_ids[group_no].append(int(student_id))

        subject_ids: dict[str, int] = {}
        main_teacher = {"TRPP": "teacher", "DB": "petrov", "WEB": "sokolova", "OOP": "petrov", "MATH": "sokolova"}
        for code, title, description, hours in SUBJECTS:
            subject_ids[code] = int(
                conn.execute(
                    """
                    INSERT INTO subjects (code, title, description, hours, teacher_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, title, description, hours, teacher_ids[main_teacher[code]]),
                ).lastrowid
            )

        # many-to-many: преподаватели и дисциплины
        teacher_links = [
            ("teacher", "TRPP"),
            ("teacher", "OOP"),
            ("petrov", "DB"),
            ("petrov", "OOP"),
            ("petrov", "TRPP"),
            ("sokolova", "WEB"),
            ("sokolova", "MATH"),
        ]
        conn.executemany(
            "INSERT INTO teacher_subject (teacher_id, subject_id) VALUES (?, ?)",
            [(teacher_ids[login], subject_ids[code]) for login, code in teacher_links],
        )

        # many-to-many: группы и дисциплины
        conn.executemany(
            "INSERT INTO group_subject (group_id, subject_id) VALUES (?, ?)",
            [
                (group_ids[group_no], subject_ids[code])
                for group_no, codes in CURRICULUM.items()
                for code in codes
            ],
        )

        start = date(2026, 9, 8)
        lesson_counter = 0
        for group_no, codes in CURRICULUM.items():
            for subject_index, code in enumerate(codes):
                teacher_id = teacher_ids[main_teacher[code]]
                for number in range(3):
                    lesson_date = start + timedelta(days=number * 14 + subject_index * 2)
                    lesson_id = int(
                        conn.execute(
                            """
                            INSERT INTO lessons
                                (subject_id, group_id, teacher_id, lesson_date, topic, homework, lesson_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                subject_ids[code],
                                group_ids[group_no],
                                teacher_id,
                                lesson_date.isoformat(),
                                TOPICS[code][number],
                                "Подготовить конспект и практическое задание.",
                                LESSON_TYPES[(subject_index + number) % len(LESSON_TYPES)],
                            ),
                        ).lastrowid
                    )
                    for student_index, student_id in enumerate(student_ids[group_no]):
                        key = lesson_counter * 5 + student_index * 3
                        if key % 11 == 0:
                            continue
                        value = GRADE_PATTERN[(lesson_counter + student_index) % len(GRADE_PATTERN)]
                        conn.execute(
                            """
                            INSERT INTO grades (student_id, lesson_id, value, comment, created_by)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                student_id,
                                lesson_id,
                                value,
                                "Работа на занятии" if value >= 4 else "Требуется доработка",
                                admin_id,
                            ),
                        )
                        status = "present"
                        if (lesson_counter + student_index) % 13 == 0:
                            status = "absent"
                        elif (lesson_counter + student_index) % 9 == 0:
                            status = "late"
                        elif (lesson_counter + student_index) % 17 == 0:
                            status = "excused"
                        conn.execute(
                            """
                            INSERT INTO attendance (student_id, lesson_id, status)
                            VALUES (?, ?, ?)
                            """,
                            (student_id, lesson_id, status),
                        )
                    lesson_counter += 1

        conn.execute(
            """
            INSERT INTO audit_log (user_id, action, entity, entity_id, details)
            VALUES (?, 'seed', 'database', NULL, 'Демонстрационные данные загружены')
            """,
            (admin_id,),
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Заполнение базы демонстрационными данными")
    parser.add_argument("--force", action="store_true", help="очистить и заполнить заново")
    args = parser.parse_args()
    created = seed_data(force=args.force)
    print(
        f"База данных: {config.db_path()}\n"
        + ("Демонстрационные данные загружены." if created else "База уже содержит данные, пропуск.")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
