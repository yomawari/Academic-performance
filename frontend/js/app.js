import { api, ApiError } from "./api-client.js";

const ROLE_LABELS = {
  admin: "Администратор",
  teacher: "Преподаватель",
  student: "Студент",
};

const PAGES = {
  dashboard: { title: "Главная", roles: ["admin", "teacher", "student"] },
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
