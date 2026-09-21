PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department TEXT    NOT NULL DEFAULT '',
    position   TEXT    NOT NULL DEFAULT 'преподаватель'
);

CREATE TABLE IF NOT EXISTS groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    course     INTEGER NOT NULL CHECK (course BETWEEN 1 AND 6),
    curator_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS students (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    group_id       INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    record_book_no TEXT    NOT NULL UNIQUE,
    email          TEXT,
    phone          TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    hours       INTEGER NOT NULL DEFAULT 0 CHECK (hours >= 0),
    teacher_id  INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- many-to-many: преподаватели <-> дисциплины
CREATE TABLE IF NOT EXISTS teacher_subject (
    teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (teacher_id, subject_id)
);

-- many-to-many: учебные группы <-> дисциплины (учебный план)
CREATE TABLE IF NOT EXISTS group_subject (
    group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, subject_id)
);

CREATE TABLE IF NOT EXISTS lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    teacher_id  INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    lesson_date TEXT    NOT NULL,
    topic       TEXT    NOT NULL DEFAULT '',
    homework    TEXT    NOT NULL DEFAULT '',
    lesson_type TEXT    NOT NULL DEFAULT 'practice'
                CHECK (lesson_type IN ('lecture', 'practice', 'lab', 'test')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- many-to-many: студенты <-> занятия (оценка является атрибутом связи)
CREATE TABLE IF NOT EXISTS grades (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    value      INTEGER NOT NULL CHECK (value BETWEEN 1 AND 5),
    comment    TEXT    NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    UNIQUE (student_id, lesson_id)
);

-- many-to-many: студенты <-> занятия (посещаемость)
CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    status     TEXT    NOT NULL DEFAULT 'present'
               CHECK (status IN ('present', 'absent', 'late', 'excused')),
    comment    TEXT    NOT NULL DEFAULT '',
    UNIQUE (student_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT    NOT NULL,
    entity     TEXT    NOT NULL,
    entity_id  INTEGER,
    details    TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_students_group   ON students(group_id);
CREATE INDEX IF NOT EXISTS idx_lessons_subject  ON lessons(subject_id);
CREATE INDEX IF NOT EXISTS idx_lessons_group    ON lessons(group_id);
CREATE INDEX IF NOT EXISTS idx_lessons_date     ON lessons(lesson_date);
CREATE INDEX IF NOT EXISTS idx_grades_student   ON grades(student_id);
CREATE INDEX IF NOT EXISTS idx_grades_lesson    ON grades(lesson_id);
CREATE INDEX IF NOT EXISTS idx_attendance_lesson ON attendance(lesson_id);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_log(created_at);
