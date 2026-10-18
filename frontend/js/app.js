import { api, ApiError } from "./api-client.js";

const ROLE_LABELS = {
  admin: "Администратор",
  teacher: "Преподаватель",
  student: "Студент",
};

const PAGES = {
  dashboard: { title: "Главная", roles: ["admin", "teacher", "student"] },
  lessons: { title: "Занятия", roles: ["admin", "teacher"] },
  journal: { title: "Журнал", roles: ["admin", "teacher"] },
  reports: { title: "Отчёты", roles: ["admin", "teacher"] },
  "my-grades": { title: "Моя успеваемость", roles: ["student"] },
  students: { title: "Студенты", roles: ["admin", "teacher"] },
  groups: { title: "Группы", roles: ["admin", "teacher"] },
  subjects: { title: "Дисциплины", roles: ["admin", "teacher"] },
  teachers: { title: "Преподаватели", roles: ["admin", "teacher"] },
};

const state = {
  user: null,
  page: "dashboard",
  form: null,
  students: [],
  groups: [],
  teachers: [],
  subjects: [],
  lessons: [],
  lessonId: null,
  reportGroupId: null,
};

const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character],
  );

const avg = (value) =>
  value === null || value === undefined ? "—" : Number(value).toFixed(2).replace(".", ",");

const fmtDate = (value) => (value ? String(value).split("-").reverse().join(".") : "—");

const LESSON_TYPE_LABELS = {
  lecture: "Лекция",
  practice: "Практика",
  lab: "Лабораторная",
  test: "Контрольная",
};

const ATTENDANCE_LABELS = {
  present: "Присутствовал",
  absent: "Отсутствовал",
  late: "Опоздал",
  excused: "Уважительная причина",
};

function currentTeacherId() {
  return state.teachers.find((teacher) => teacher.username === state.user?.username)?.id ?? null;
}

let flashTimer = null;

function flash(message, isError = false) {
  const element = $("#flash");
  element.textContent = message;
  element.className = isError ? "flash error" : "flash";
  element.hidden = false;
  window.clearTimeout(flashTimer);
  flashTimer = window.setTimeout(() => {
    element.hidden = true;
  }, 4000);
}

const isAdmin = () => state.user?.role === "admin";

function showLogin(message = "") {
  state.user = null;
  state.form = null;
  $("#app-screen").hidden = true;
  $("#login-screen").hidden = false;
  $("#login-password").value = "";
  document.title = "Вход · Учёт успеваемости";

  const error = $("#login-error");
  error.textContent = message;
  error.hidden = !message;
}

function showApp() {
  $("#login-screen").hidden = true;
  $("#app-screen").hidden = false;
  $("#user-name").textContent = state.user.full_name;
  $("#user-role").textContent = ROLE_LABELS[state.user.role] || state.user.role;
  document.title = "Учёт успеваемости";
  openPage(defaultPage());
}

function defaultPage() {
  return "dashboard";
}

function canOpen(page) {
  return Boolean(PAGES[page] && PAGES[page].roles.includes(state.user?.role));
}

function pageFromHash() {
  const page = window.location.hash.replace(/^#\/?/, "");
  return canOpen(page) ? page : defaultPage();
}

function openPage(page) {
  const target = `#/${page}`;
  if (window.location.hash === target) {
    renderPage(page);
  } else {
    window.location.hash = target;
  }
}

function navigate(page) {
  state.form = null;
  if (window.location.hash === `#/${page}`) {
    renderPage(page);
  } else {
    window.location.hash = `#/${page}`;
  }
}

function renderNav() {
  $("#nav").innerHTML = Object.entries(PAGES)
    .filter(([, meta]) => meta.roles.includes(state.user.role))
    .map(
      ([page, meta]) =>
        `<button type="button" class="nav-link ${page === state.page ? "active" : ""}" data-page="${page}">${meta.title}</button>`,
    )
    .join("");
}

function pageHead(title, action = "") {
  return `<div class="page-head"><h1>${esc(title)}</h1>${action}</div>`;
}

function emptyRow(columns) {
  return `<tr><td class="empty" colspan="${columns}">Записей нет</td></tr>`;
}

async function renderPage(page) {
  if (!state.user) return;
  if (!canOpen(page)) page = defaultPage();
  state.page = page;
  renderNav();
  document.title = `${PAGES[page].title} · Учёт успеваемости`;

  const content = $("#content");
  content.innerHTML = `<p class="muted">Загрузка…</p>`;

  try {
    if (page === "dashboard") await renderDashboard(content);
    else if (page === "lessons") await renderLessons(content);
    else if (page === "journal") await renderJournal(content);
    else if (page === "reports") await renderReports(content);
    else if (page === "my-grades") await renderMyGrades(content);
    else if (page === "students") await renderStudents(content);
    else if (page === "groups") await renderGroups(content);
    else if (page === "subjects") await renderSubjects(content);
    else if (page === "teachers") await renderTeachers(content);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      localStorage.removeItem("ap_session");
      showLogin("Сессия истекла. Войдите снова.");
      return;
    }
    content.innerHTML = `<div class="panel"><p class="error">${esc(error?.detail || "Не удалось загрузить данные")}</p></div>`;
  }
}

/* Главная */

async function renderDashboard(content) {
  const data = await api.getDashboard();

  if (state.user.role === "student") {
    const students = await api.listStudents();
    const me = students[0];
    const stats = [
      ["Моя группа", me?.group_name || "—"],
      ["Дисциплин", data.subjects],
      ["Занятий", data.lessons],
      ["Средний балл", avg(data.average_grade)],
    ];

    content.innerHTML = `
      ${pageHead("Главная")}
      <div class="stat-grid">
        ${stats.map(([label, value]) => `<div class="stat"><small>${label}</small><strong>${esc(value)}</strong></div>`).join("")}
      </div>
      <div class="panel">
        <h2>Моя карточка</h2>
        <table>
          <tr><th>ФИО</th><td>${esc(me?.full_name || "—")}</td></tr>
          <tr><th>Группа</th><td>${esc(me?.group_name || "—")}</td></tr>
          <tr><th>Зачётная книжка</th><td>${esc(me?.record_book_no || "—")}</td></tr>
          <tr><th>Email</th><td>${esc(me?.email || "—")}</td></tr>
          <tr><th>Телефон</th><td>${esc(me?.phone || "—")}</td></tr>
        </table>
      </div>`;
    return;
  }

  const groups = await api.listGroups();
  const stats = [
    ["Студентов", data.students],
    ["Групп", data.groups],
    ["Дисциплин", data.subjects],
    ["Преподавателей", data.teachers],
  ];

  content.innerHTML = `
    ${pageHead("Главная")}
    <div class="stat-grid">
      ${stats.map(([label, value]) => `<div class="stat"><small>${label}</small><strong>${value}</strong></div>`).join("")}
    </div>
    <div class="panel">
      <h2>Сводка</h2>
      <p>Занятий: <b>${data.lessons}</b>. Оценок: <b>${data.grades}</b>. Средний балл: <b>${avg(data.average_grade)}</b>.</p>
    </div>
    <div class="panel">
      <h2>Учебные группы</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Группа</th><th>Курс</th><th>Куратор</th><th>Студентов</th></tr></thead>
          <tbody>
            ${
              groups.length
                ? groups
                    .map(
                      (group) => `
                  <tr>
                    <td>${esc(group.name)}</td>
                    <td>${group.course}</td>
                    <td>${esc(group.curator_name || "—")}</td>
                    <td>${group.student_count}</td>
                  </tr>`,
                    )
                    .join("")
                : emptyRow(4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

/* Занятия */

async function renderLessons(content) {
  const [lessons, groups, subjects, teachers] = await Promise.all([
    api.listLessons(),
    api.listGroups(),
    api.listSubjects(),
    api.listTeachers(),
  ]);
  state.lessons = lessons;
  state.groups = groups;
  state.subjects = subjects;
  state.teachers = teachers;

  const form =
    state.form?.entity === "lesson" ? lessonForm(lessons.find((item) => item.id === state.form.id)) : "";
  const action = isAdmin()
    ? `<button type="button" class="btn" data-action="new-lesson">Добавить занятие</button>`
    : "";
  const teacherId = currentTeacherId();

  content.innerHTML = `
    ${pageHead("Занятия", action)}
    ${form}
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Дата</th><th>Группа</th><th>Дисциплина</th><th>Преподаватель</th><th>Вид</th><th>Тема</th><th>Действия</th></tr>
          </thead>
          <tbody>
            ${
              lessons.length
                ? lessons
                    .map((lesson) => {
                      const canJournal =
                        isAdmin() || (teacherId !== null && lesson.teacher_id === teacherId);
                      const actions = [
                        canJournal
                          ? `<button type="button" class="btn btn-secondary btn-small" data-action="open-journal" data-id="${lesson.id}">Журнал</button>`
                          : "",
                        isAdmin()
                          ? `<button type="button" class="btn btn-secondary btn-small" data-action="edit-lesson" data-id="${lesson.id}">Изменить</button>
                             <button type="button" class="btn btn-danger btn-small" data-action="delete-lesson" data-id="${lesson.id}">Удалить</button>`
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" ");
                      return `
                        <tr>
                          <td>${fmtDate(lesson.lesson_date)}</td>
                          <td>${esc(lesson.group_name)}</td>
                          <td>${esc(lesson.subject_title)}</td>
                          <td>${esc(lesson.teacher_name || "—")}</td>
                          <td>${esc(LESSON_TYPE_LABELS[lesson.lesson_type] || lesson.lesson_type)}</td>
                          <td>${esc(lesson.topic)}</td>
                          <td class="actions">${actions || '<span class="muted">—</span>'}</td>
                        </tr>`;
                    })
                    .join("")
                : emptyRow(7)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

function lessonForm(lesson) {
  const editing = Boolean(lesson);
  const subjectOptions = state.subjects
    .map(
      (subject) =>
        `<option value="${subject.id}" ${lesson?.subject_id === subject.id ? "selected" : ""}>${esc(subject.title)}</option>`,
    )
    .join("");
  const groupOptions = state.groups
    .map(
      (group) =>
        `<option value="${group.id}" ${lesson?.group_id === group.id ? "selected" : ""}>${esc(group.name)}</option>`,
    )
    .join("");
  const teacherOptions = state.teachers
    .map(
      (teacher) =>
        `<option value="${teacher.id}" ${lesson?.teacher_id === teacher.id ? "selected" : ""}>${esc(teacher.full_name)}</option>`,
    )
    .join("");
  const typeOptions = Object.entries(LESSON_TYPE_LABELS)
    .map(
      ([value, label]) =>
        `<option value="${value}" ${lesson?.lesson_type === value ? "selected" : ""}>${label}</option>`,
    )
    .join("");

  return `
    <form class="panel" data-entity="lesson">
      <h2>${editing ? "Изменить занятие" : "Новое занятие"}</h2>
      <div class="fields">
        <label class="field">Дата
          <input name="lesson_date" type="date" required value="${esc(lesson?.lesson_date || new Date().toISOString().slice(0, 10))}" />
        </label>
        <label class="field">Вид занятия
          <select name="lesson_type">${typeOptions}</select>
        </label>
        <label class="field field-wide">Дисциплина
          <select name="subject_id" required>${subjectOptions}</select>
        </label>
        <label class="field">Группа
          <select name="group_id" required>${groupOptions}</select>
        </label>
        <label class="field">Преподаватель
          <select name="teacher_id">
            <option value="">Не назначен</option>
            ${teacherOptions}
          </select>
        </label>
        <label class="field field-wide">Тема
          <input name="topic" required minlength="2" maxlength="200" value="${esc(lesson?.topic)}" />
        </label>
        <label class="field field-wide">Домашнее задание
          <textarea name="homework" maxlength="500">${esc(lesson?.homework)}</textarea>
        </label>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">${editing ? "Сохранить" : "Добавить"}</button>
        <button type="button" class="btn btn-secondary" data-action="cancel-form">Отмена</button>
      </div>
    </form>`;
}

/* Журнал */

async function renderJournal(content) {
  const allLessons = await api.listLessons();
  const teachers = await api.listTeachers();
  state.teachers = teachers;

  let lessons = allLessons;
  if (state.user.role === "teacher") {
    const teacherId = currentTeacherId();
    lessons = teacherId === null ? [] : allLessons.filter((lesson) => lesson.teacher_id === teacherId);
  }

  if (!lessons.length) {
    content.innerHTML = `
      ${pageHead("Журнал")}
      <div class="panel"><p class="muted">Для ваших занятий журнал пока недоступен.</p></div>`;
    return;
  }

  if (!lessons.some((lesson) => lesson.id === state.lessonId)) {
    state.lessonId = lessons[0].id;
  }
  const journal = await api.getLessonJournal(state.lessonId);
  const lesson = journal.lesson;
  const lessonOptions = lessons
    .map(
      (item) =>
        `<option value="${item.id}" ${item.id === state.lessonId ? "selected" : ""}>${fmtDate(item.lesson_date)} · ${esc(item.group_name)} · ${esc(item.subject_title)}</option>`,
    )
    .join("");

  content.innerHTML = `
    ${pageHead("Журнал")}
    <div class="panel">
      <label class="field">Занятие
        <select data-role="lesson-select">${lessonOptions}</select>
      </label>
      <p class="muted">${esc(lesson.group_name)} · ${esc(lesson.subject_title)} · ${esc(lesson.teacher_name || "преподаватель не назначен")} · ${fmtDate(lesson.lesson_date)}</p>
    </div>
    <div class="panel">
      <div class="table-wrap">
        <table class="journal-table">
          <thead>
            <tr><th>Студент</th><th>Зачётка</th><th>Оценка</th><th>Комментарий</th><th>Посещаемость</th><th>Комментарий</th><th></th></tr>
          </thead>
          <tbody>
            ${
              journal.entries.length
                ? journal.entries
                    .map(
                      (entry) => `
                  <tr data-student="${entry.student_id}">
                    <td>${esc(entry.full_name)}</td>
                    <td>${esc(entry.record_book_no)}</td>
                    <td>
                      <select data-field="grade">
                        <option value="">—</option>
                        ${[5, 4, 3, 2]
                          .map(
                            (value) =>
                              `<option value="${value}" ${entry.grade_value === value ? "selected" : ""}>${value}</option>`,
                          )
                          .join("")}
                      </select>
                    </td>
                    <td><input data-field="grade-comment" maxlength="300" value="${esc(entry.grade_comment)}" /></td>
                    <td>
                      <select data-field="attendance">
                        <option value="">—</option>
                        ${Object.entries(ATTENDANCE_LABELS)
                          .map(
                            ([value, label]) =>
                              `<option value="${value}" ${entry.attendance_status === value ? "selected" : ""}>${label}</option>`,
                          )
                          .join("")}
                      </select>
                    </td>
                    <td><input data-field="attendance-comment" maxlength="300" value="${esc(entry.attendance_comment)}" /></td>
                    <td class="actions"><button type="button" class="btn btn-small" data-action="save-entry">Сохранить</button></td>
                  </tr>`,
                    )
                    .join("")
                : emptyRow(7)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

async function saveJournalRow(button) {
  const row = button.closest("tr[data-student]");
  if (!row) return;
  const grade = row.querySelector('[data-field="grade"]').value;
  const attendance = row.querySelector('[data-field="attendance"]').value;
  try {
    await api.saveJournalEntry(state.lessonId, Number(row.dataset.student), {
      grade_value: grade === "" ? null : Number(grade),
      grade_comment: row.querySelector('[data-field="grade-comment"]').value.trim(),
      attendance_status: attendance === "" ? null : attendance,
      attendance_comment: row.querySelector('[data-field="attendance-comment"]').value.trim(),
    });
    flash("Запись журнала сохранена");
    await renderPage("journal");
  } catch (error) {
    flash(error?.detail || "Не удалось сохранить запись", true);
  }
}

/* Отчёты */

async function renderReports(content) {
  const groups = await api.listGroups();
  state.groups = groups;

  if (!groups.length) {
    content.innerHTML = `
      ${pageHead("Отчёты")}
      <div class="panel"><p class="muted">Учебные группы не найдены.</p></div>`;
    return;
  }

  if (!groups.some((group) => group.id === state.reportGroupId)) {
    state.reportGroupId = groups[0].id;
  }
  const report = await api.getGroupReport(state.reportGroupId);
  const groupOptions = groups
    .map(
      (group) =>
        `<option value="${group.id}" ${group.id === state.reportGroupId ? "selected" : ""}>${esc(group.name)}</option>`,
    )
    .join("");
  const averages = report.students
    .map((student) => student.average_grade)
    .filter((value) => value !== null);
  const overall = averages.length
    ? averages.reduce((sum, value) => sum + value, 0) / averages.length
    : null;
  const download = `<a class="btn btn-secondary" href="/api/reports/groups/${state.reportGroupId}/export" download>Скачать CSV</a>`;

  content.innerHTML = `
    ${pageHead("Отчёты", download)}
    <div class="panel">
      <label class="field">Учебная группа
        <select data-role="report-group">${groupOptions}</select>
      </label>
    </div>
    <div class="stat-grid">
      <div class="stat"><small>Группа</small><strong>${esc(report.group_name)}</strong></div>
      <div class="stat"><small>Студентов</small><strong>${report.students.length}</strong></div>
      <div class="stat"><small>Средний балл</small><strong>${avg(overall)}</strong></div>
    </div>
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>ФИО</th><th>Зачётная книжка</th><th>Средний балл</th><th>Оценок</th><th>Пропусков</th><th>Опозданий</th></tr></thead>
          <tbody>
            ${
              report.students.length
                ? report.students
                    .map(
                      (student) => `
                  <tr>
                    <td>${esc(student.full_name)}</td>
                    <td>${esc(student.record_book_no)}</td>
                    <td>${avg(student.average_grade)}</td>
                    <td>${student.grades_count}</td>
                    <td>${student.absences}</td>
                    <td>${student.lates}</td>
                  </tr>`,
                    )
                    .join("")
                : emptyRow(6)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

/* Моя успеваемость */

async function renderMyGrades(content) {
  const students = await api.listStudents();
  const me = students[0];
  if (!me) {
    content.innerHTML = `
      ${pageHead("Моя успеваемость")}
      <div class="panel"><p class="muted">Карточка студента не найдена.</p></div>`;
    return;
  }

  const report = await api.getStudentReport(me.id);
  const totalGrades = report.subjects.reduce((sum, subject) => sum + subject.grades_count, 0);
  const weighted = report.subjects.reduce(
    (sum, subject) => sum + (subject.average_grade || 0) * subject.grades_count,
    0,
  );
  const overall = totalGrades ? weighted / totalGrades : null;

  content.innerHTML = `
    ${pageHead("Моя успеваемость")}
    <div class="stat-grid">
      <div class="stat"><small>Группа</small><strong>${esc(me.group_name || "—")}</strong></div>
      <div class="stat"><small>Дисциплин</small><strong>${report.subjects.length}</strong></div>
      <div class="stat"><small>Оценок</small><strong>${totalGrades}</strong></div>
      <div class="stat"><small>Средний балл</small><strong>${avg(overall)}</strong></div>
    </div>
    <div class="panel">
      <h2>По дисциплинам</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Дисциплина</th><th>Средний балл</th><th>Оценок</th></tr></thead>
          <tbody>
            ${
              report.subjects.length
                ? report.subjects
                    .map(
                      (subject) => `
                  <tr>
                    <td>${esc(subject.title)}</td>
                    <td>${avg(subject.average_grade)}</td>
                    <td>${subject.grades_count}</td>
                  </tr>`,
                    )
                    .join("")
                : emptyRow(3)
            }
          </tbody>
        </table>
      </div>
    </div>
    <div class="panel">
      <h2>Последние оценки</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Дата</th><th>Дисциплина</th><th>Оценка</th><th>Комментарий</th></tr></thead>
          <tbody>
            ${
              report.grades.length
                ? report.grades
                    .map(
                      (grade) => `
                  <tr>
                    <td>${fmtDate(grade.lesson_date)}</td>
                    <td>${esc(grade.subject_title)}</td>
                    <td>${grade.value}</td>
                    <td>${esc(grade.comment || "—")}</td>
                  </tr>`,
                    )
                    .join("")
                : emptyRow(4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

/* Студенты */

async function renderStudents(content) {
  const [students, groups] = await Promise.all([api.listStudents(), api.listGroups()]);
  state.students = students;
  state.groups = groups;

  const form =
    state.form?.entity === "student" ? studentForm(students.find((item) => item.id === state.form.id)) : "";
  const action = isAdmin()
    ? `<button type="button" class="btn" data-action="new-student">Добавить студента</button>`
    : "";

  content.innerHTML = `
    ${pageHead("Студенты", action)}
    ${form}
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>ФИО</th><th>Группа</th><th>Зачётная книжка</th><th>Email</th>${isAdmin() ? "<th></th>" : ""}</tr>
          </thead>
          <tbody>
            ${
              students.length
                ? students
                    .map(
                      (student) => `
                  <tr>
                    <td>${esc(student.full_name)}</td>
                    <td>${esc(student.group_name || "—")}</td>
                    <td>${esc(student.record_book_no)}</td>
                    <td>${esc(student.email || "—")}</td>
                    ${
                      isAdmin()
                        ? `<td class="actions">
                             <button type="button" class="btn btn-secondary btn-small" data-action="edit-student" data-id="${student.id}">Изменить</button>
                             <button type="button" class="btn btn-danger btn-small" data-action="delete-student" data-id="${student.id}">Удалить</button>
                           </td>`
                        : ""
                    }
                  </tr>`,
                    )
                    .join("")
                : emptyRow(isAdmin() ? 5 : 4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

function studentForm(student) {
  const editing = Boolean(student);
  const groupOptions = state.groups
    .map(
      (group) =>
        `<option value="${group.id}" ${student?.group_id === group.id ? "selected" : ""}>${esc(group.name)}</option>`,
    )
    .join("");

  return `
    <form class="panel" data-entity="student">
      <h2>${editing ? "Изменить студента" : "Новый студент"}</h2>
      <div class="fields">
        <label class="field field-wide">ФИО
          <input name="full_name" required minlength="3" maxlength="120" value="${esc(student?.full_name)}" />
        </label>
        ${
          editing
            ? ""
            : `<label class="field">Логин
                 <input name="username" required minlength="3" maxlength="32" value="" />
               </label>
               <label class="field">Пароль
                 <input name="password" type="password" required minlength="6" value="" />
               </label>`
        }
        <label class="field">Группа
          <select name="group_id">
            <option value="">Без группы</option>
            ${groupOptions}
          </select>
        </label>
        <label class="field">Зачётная книжка
          <input name="record_book_no" required minlength="2" maxlength="30" value="${esc(student?.record_book_no)}" />
        </label>
        <label class="field">Email
          <input name="email" type="email" value="${esc(student?.email)}" />
        </label>
        <label class="field">Телефон
          <input name="phone" maxlength="30" value="${esc(student?.phone)}" />
        </label>
        ${
          editing
            ? `<label class="field">Учётная запись активна
                 <input name="is_active" type="checkbox" ${student.is_active ? "checked" : ""} />
               </label>`
            : ""
        }
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">${editing ? "Сохранить" : "Добавить"}</button>
        <button type="button" class="btn btn-secondary" data-action="cancel-form">Отмена</button>
      </div>
    </form>`;
}

/* Группы */

async function renderGroups(content) {
  const [groups, teachers] = await Promise.all([api.listGroups(), api.listTeachers()]);
  state.groups = groups;
  state.teachers = teachers;

  const form = state.form?.entity === "group" ? groupForm(groups.find((item) => item.id === state.form.id)) : "";
  const action = isAdmin() ? `<button type="button" class="btn" data-action="new-group">Добавить группу</button>` : "";

  content.innerHTML = `
    ${pageHead("Группы", action)}
    ${form}
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Группа</th><th>Курс</th><th>Куратор</th><th>Студентов</th>${isAdmin() ? "<th></th>" : ""}</tr></thead>
          <tbody>
            ${
              groups.length
                ? groups
                    .map(
                      (group) => `
                  <tr>
                    <td>${esc(group.name)}</td>
                    <td>${group.course}</td>
                    <td>${esc(group.curator_name || "—")}</td>
                    <td>${group.student_count}</td>
                    ${
                      isAdmin()
                        ? `<td class="actions">
                             <button type="button" class="btn btn-secondary btn-small" data-action="edit-group" data-id="${group.id}">Изменить</button>
                             <button type="button" class="btn btn-danger btn-small" data-action="delete-group" data-id="${group.id}">Удалить</button>
                           </td>`
                        : ""
                    }
                  </tr>`,
                    )
                    .join("")
                : emptyRow(isAdmin() ? 5 : 4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

function groupForm(group) {
  const editing = Boolean(group);
  const curatorOptions = state.teachers
    .map(
      (teacher) =>
        `<option value="${teacher.id}" ${group?.curator_id === teacher.id ? "selected" : ""}>${esc(teacher.full_name)}</option>`,
    )
    .join("");

  return `
    <form class="panel" data-entity="group">
      <h2>${editing ? "Изменить группу" : "Новая группа"}</h2>
      <div class="fields">
        <label class="field">Название
          <input name="name" required minlength="2" maxlength="40" value="${esc(group?.name)}" />
        </label>
        <label class="field">Курс
          <select name="course">
            ${[1, 2, 3, 4, 5, 6].map((course) => `<option value="${course}" ${group?.course === course ? "selected" : ""}>${course}</option>`).join("")}
          </select>
        </label>
        <label class="field">Куратор
          <select name="curator_id">
            <option value="">Не назначен</option>
            ${curatorOptions}
          </select>
        </label>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">${editing ? "Сохранить" : "Добавить"}</button>
        <button type="button" class="btn btn-secondary" data-action="cancel-form">Отмена</button>
      </div>
    </form>`;
}

/* Дисциплины */

async function renderSubjects(content) {
  const [subjects, teachers] = await Promise.all([api.listSubjects(), api.listTeachers()]);
  state.subjects = subjects;
  state.teachers = teachers;

  const form =
    state.form?.entity === "subject" ? subjectForm(subjects.find((item) => item.id === state.form.id)) : "";
  const action = isAdmin() ? `<button type="button" class="btn" data-action="new-subject">Добавить дисциплину</button>` : "";

  content.innerHTML = `
    ${pageHead("Дисциплины", action)}
    ${form}
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Код</th><th>Название</th><th>Часы</th><th>Преподаватель</th>${isAdmin() ? "<th></th>" : ""}</tr></thead>
          <tbody>
            ${
              subjects.length
                ? subjects
                    .map(
                      (subject) => `
                  <tr>
                    <td>${esc(subject.code)}</td>
                    <td>${esc(subject.title)}</td>
                    <td>${subject.hours}</td>
                    <td>${esc(subject.teacher_name || "—")}</td>
                    ${
                      isAdmin()
                        ? `<td class="actions">
                             <button type="button" class="btn btn-secondary btn-small" data-action="edit-subject" data-id="${subject.id}">Изменить</button>
                             <button type="button" class="btn btn-danger btn-small" data-action="delete-subject" data-id="${subject.id}">Удалить</button>
                           </td>`
                        : ""
                    }
                  </tr>`,
                    )
                    .join("")
                : emptyRow(isAdmin() ? 5 : 4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

function subjectForm(subject) {
  const editing = Boolean(subject);
  const teacherOptions = state.teachers
    .map(
      (teacher) =>
        `<option value="${teacher.id}" ${subject?.teacher_id === teacher.id ? "selected" : ""}>${esc(teacher.full_name)}</option>`,
    )
    .join("");

  return `
    <form class="panel" data-entity="subject">
      <h2>${editing ? "Изменить дисциплину" : "Новая дисциплина"}</h2>
      <div class="fields">
        <label class="field">Код
          <input name="code" required minlength="2" maxlength="20" value="${esc(subject?.code)}" />
        </label>
        <label class="field">Часы
          <input name="hours" type="number" min="0" max="1000" required value="${subject?.hours ?? 72}" />
        </label>
        <label class="field field-wide">Название
          <input name="title" required minlength="3" maxlength="120" value="${esc(subject?.title)}" />
        </label>
        <label class="field field-wide">Преподаватель
          <select name="teacher_id">
            <option value="">Не назначен</option>
            ${teacherOptions}
          </select>
        </label>
        <label class="field field-wide">Описание
          <textarea name="description" maxlength="1000">${esc(subject?.description)}</textarea>
        </label>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">${editing ? "Сохранить" : "Добавить"}</button>
        <button type="button" class="btn btn-secondary" data-action="cancel-form">Отмена</button>
      </div>
    </form>`;
}

/* Преподаватели */

async function renderTeachers(content) {
  const teachers = await api.listTeachers();
  state.teachers = teachers;

  const form =
    state.form?.entity === "teacher" ? teacherForm(teachers.find((item) => item.id === state.form.id)) : "";
  const action = isAdmin() ? `<button type="button" class="btn" data-action="new-teacher">Добавить преподавателя</button>` : "";

  content.innerHTML = `
    ${pageHead("Преподаватели", action)}
    ${form}
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>ФИО</th><th>Кафедра</th><th>Должность</th><th>Дисциплин</th>${isAdmin() ? "<th></th>" : ""}</tr></thead>
          <tbody>
            ${
              teachers.length
                ? teachers
                    .map(
                      (teacher) => `
                  <tr>
                    <td>${esc(teacher.full_name)}</td>
                    <td>${esc(teacher.department)}</td>
                    <td>${esc(teacher.position)}</td>
                    <td>${teacher.subject_count}</td>
                    ${
                      isAdmin()
                        ? `<td class="actions">
                             <button type="button" class="btn btn-secondary btn-small" data-action="edit-teacher" data-id="${teacher.id}">Изменить</button>
                             <button type="button" class="btn btn-danger btn-small" data-action="delete-teacher" data-id="${teacher.id}">Удалить</button>
                           </td>`
                        : ""
                    }
                  </tr>`,
                    )
                    .join("")
                : emptyRow(isAdmin() ? 5 : 4)
            }
          </tbody>
        </table>
      </div>
    </div>`;
}

function teacherForm(teacher) {
  const editing = Boolean(teacher);

  return `
    <form class="panel" data-entity="teacher">
      <h2>${editing ? "Изменить преподавателя" : "Новый преподаватель"}</h2>
      <div class="fields">
        <label class="field field-wide">ФИО
          <input name="full_name" required minlength="3" maxlength="120" value="${esc(teacher?.full_name)}" />
        </label>
        ${
          editing
            ? ""
            : `<label class="field">Логин
                 <input name="username" required minlength="3" maxlength="32" value="" />
               </label>
               <label class="field">Пароль
                 <input name="password" type="password" required minlength="6" value="" />
               </label>`
        }
        <label class="field">Кафедра
          <input name="department" required minlength="2" maxlength="80" value="${esc(teacher?.department)}" />
        </label>
        <label class="field">Должность
          <input name="position" required minlength="2" maxlength="80" value="${esc(teacher?.position)}" />
        </label>
        ${
          editing
            ? `<label class="field">Учётная запись активна
                 <input name="is_active" type="checkbox" ${teacher.is_active ? "checked" : ""} />
               </label>`
            : ""
        }
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">${editing ? "Сохранить" : "Добавить"}</button>
        <button type="button" class="btn btn-secondary" data-action="cancel-form">Отмена</button>
      </div>
    </form>`;
}

/* Действия */

function formValue(form, name) {
  return form.elements[name].value.trim();
}

function nullable(form, name) {
  const value = formValue(form, name);
  return value === "" ? null : value;
}

function studentPayload(form, editing) {
  const payload = {
    full_name: formValue(form, "full_name"),
    group_id: nullable(form, "group_id") ? Number(formValue(form, "group_id")) : null,
    record_book_no: formValue(form, "record_book_no"),
    email: nullable(form, "email"),
    phone: nullable(form, "phone"),
  };
  if (editing) {
    payload.is_active = form.elements.is_active.checked;
  } else {
    payload.username = formValue(form, "username");
    payload.password = formValue(form, "password");
  }
  return payload;
}

async function submitForm(form) {
  const entity = form.dataset.entity;
  const editing = Boolean(state.form?.id);

  let payload;
  let method;
  if (entity === "student") {
    payload = studentPayload(form, editing);
    method = editing ? "updateStudent" : "createStudent";
  } else if (entity === "group") {
    payload = {
      name: formValue(form, "name"),
      course: Number(formValue(form, "course")),
      curator_id: nullable(form, "curator_id") ? Number(formValue(form, "curator_id")) : null,
    };
    method = editing ? "updateGroup" : "createGroup";
  } else if (entity === "subject") {
    payload = {
      code: formValue(form, "code"),
      title: formValue(form, "title"),
      description: formValue(form, "description"),
      hours: Number(formValue(form, "hours")),
      teacher_id: nullable(form, "teacher_id") ? Number(formValue(form, "teacher_id")) : null,
    };
    method = editing ? "updateSubject" : "createSubject";
  } else if (entity === "lesson") {
    payload = {
      subject_id: Number(formValue(form, "subject_id")),
      group_id: Number(formValue(form, "group_id")),
      teacher_id: nullable(form, "teacher_id") ? Number(formValue(form, "teacher_id")) : null,
      lesson_date: formValue(form, "lesson_date"),
      topic: formValue(form, "topic"),
      homework: formValue(form, "homework"),
      lesson_type: formValue(form, "lesson_type"),
    };
    method = editing ? "updateLesson" : "createLesson";
  } else {
    payload = {
      full_name: formValue(form, "full_name"),
      department: formValue(form, "department"),
      position: formValue(form, "position"),
    };
    if (editing) {
      payload.is_active = form.elements.is_active.checked;
    } else {
      payload.username = formValue(form, "username");
      payload.password = formValue(form, "password");
    }
    method = editing ? "updateTeacher" : "createTeacher";
  }

  try {
    if (editing) {
      await api[method](state.form.id, payload);
    } else {
      await api[method](payload);
    }
    state.form = null;
    flash(editing ? "Изменения сохранены" : "Запись добавлена");
    await renderPage(state.page);
  } catch (error) {
    flash(error?.detail || "Не удалось сохранить запись", true);
  }
}

const DELETE_NAMES = {
  student: "студента",
  group: "группу",
  subject: "дисциплину",
  teacher: "преподавателя",
  lesson: "занятие",
};

async function deleteEntity(entity, id) {
  if (!window.confirm(`Удалить ${DELETE_NAMES[entity]}?`)) return;
  try {
    await api[`delete${entity[0].toUpperCase()}${entity.slice(1)}`](id);
    flash("Запись удалена");
    await renderPage(state.page);
  } catch (error) {
    flash(error?.detail || "Не удалось удалить запись", true);
  }
}

function onContentClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = button.dataset.id ? Number(button.dataset.id) : null;

  if (action === "cancel-form") {
    state.form = null;
    renderPage(state.page);
    return;
  }
  if (action.startsWith("new-")) {
    state.form = { entity: action.slice(4), id: null };
    renderPage(state.page);
    return;
  }
  if (action.startsWith("edit-")) {
    state.form = { entity: action.slice(5), id };
    renderPage(state.page);
    return;
  }
  if (action.startsWith("delete-")) {
    deleteEntity(action.slice(7), id);
    return;
  }
  if (action === "open-journal") {
    state.lessonId = id;
    navigate("journal");
    return;
  }
  if (action === "save-entry") {
    saveJournalRow(button);
  }
}

function bindEvents() {
  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $("#login-submit");
    $("#login-error").hidden = true;
    button.disabled = true;
    try {
      state.user = await api.login({
        username: form.elements.username.value.trim(),
        password: form.elements.password.value,
      });
      localStorage.setItem("ap_session", "1");
      form.reset();
      showApp();
    } catch (error) {
      $("#login-error").textContent = error?.detail || "Не удалось выполнить вход";
      $("#login-error").hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  $("#logout").addEventListener("click", async () => {
    try {
      await api.logout();
    } catch {
      /* сессия могла уже истечь */
    }
    localStorage.removeItem("ap_session");
    window.location.hash = "";
    showLogin();
  });

  $("#nav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (button) navigate(button.dataset.page);
  });

  $("#content").addEventListener("click", onContentClick);

  $("#content").addEventListener("change", (event) => {
    const lessonSelect = event.target.closest("[data-role='lesson-select']");
    const reportSelect = event.target.closest("[data-role='report-group']");
    if (lessonSelect && state.page === "journal") {
      state.lessonId = Number(lessonSelect.value);
      renderPage("journal");
    }
    if (reportSelect && state.page === "reports") {
      state.reportGroupId = Number(reportSelect.value);
      renderPage("reports");
    }
  });

  $("#content").addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-entity]");
    if (!form) return;
    event.preventDefault();
    submitForm(form);
  });

  window.addEventListener("hashchange", () => {
    if (state.user) renderPage(pageFromHash());
  });
}

async function init() {
  bindEvents();

  if (localStorage.getItem("ap_session") !== "1") {
    showLogin();
    return;
  }

  try {
    state.user = await api.getCurrentUser();
    showApp();
  } catch {
    localStorage.removeItem("ap_session");
    showLogin();
  }
}

init();
