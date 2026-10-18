// AUTO-GENERATED FILE. DO NOT EDIT.
// Source: api/openapi.yaml
// Generator: scripts/generate_client.py

export class ApiError extends Error {
  constructor(status, detail, code) {
    super(detail || 'Ошибка запроса');
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail || 'Ошибка запроса';
    this.code = code || 'error';
  }
}

export class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async request(method, path, { query, body } = {}) {
    const url = new URL(this.baseUrl + path, window.location.origin);
    if (query) {
      Object.entries(query).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, value);
        }
      });
    }
    const options = {
      method,
      credentials: 'include',
      headers: { Accept: 'application/json' },
    };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    if (response.status === 204) {
      return null;
    }
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json')
      ? await response.json().catch(() => null)
      : await response.text();
    if (!response.ok) {
      const detail = data && typeof data === 'object' ? data.detail : data;
      const code = data && typeof data === 'object' ? data.code : undefined;
      throw new ApiError(response.status, detail, code);
    }
    return data;
  }

  /** Проверка доступности сервера */
  health() {
    return this.request('GET', '/api/health');
  }

  /** Вход в систему */
  login(body) {
    return this.request('POST', '/api/auth/login', { body });
  }

  /** Текущий пользователь */
  getCurrentUser() {
    return this.request('GET', '/api/auth/me');
  }

  /** Выход из системы */
  logout() {
    return this.request('POST', '/api/auth/logout');
  }

  /** Список учебных групп */
  listGroups() {
    return this.request('GET', '/api/groups');
  }

  /** Создать учебную группу */
  createGroup(body) {
    return this.request('POST', '/api/groups', { body });
  }

  /** Изменить учебную группу */
  updateGroup(group_id, body) {
    return this.request('PATCH', `/api/groups/${encodeURIComponent(group_id)}`, { body });
  }

  /** Удалить учебную группу */
  deleteGroup(group_id) {
    return this.request('DELETE', `/api/groups/${encodeURIComponent(group_id)}`);
  }

  /** Список студентов */
  listStudents(query = {}) {
    return this.request('GET', '/api/students', { query });
  }

  /** Добавить студента */
  createStudent(body) {
    return this.request('POST', '/api/students', { body });
  }

  /** Студент по идентификатору */
  getStudent(student_id) {
    return this.request('GET', `/api/students/${encodeURIComponent(student_id)}`);
  }

  /** Изменить данные студента */
  updateStudent(student_id, body) {
    return this.request('PATCH', `/api/students/${encodeURIComponent(student_id)}`, { body });
  }

  /** Удалить студента */
  deleteStudent(student_id) {
    return this.request('DELETE', `/api/students/${encodeURIComponent(student_id)}`);
  }

  /** Список преподавателей */
  listTeachers() {
    return this.request('GET', '/api/teachers');
  }

  /** Добавить преподавателя */
  createTeacher(body) {
    return this.request('POST', '/api/teachers', { body });
  }

  /** Изменить данные преподавателя */
  updateTeacher(teacher_id, body) {
    return this.request('PATCH', `/api/teachers/${encodeURIComponent(teacher_id)}`, { body });
  }

  /** Удалить преподавателя */
  deleteTeacher(teacher_id) {
    return this.request('DELETE', `/api/teachers/${encodeURIComponent(teacher_id)}`);
  }

  /** Список дисциплин */
  listSubjects() {
    return this.request('GET', '/api/subjects');
  }

  /** Создать дисциплину */
  createSubject(body) {
    return this.request('POST', '/api/subjects', { body });
  }

  /** Изменить дисциплину */
  updateSubject(subject_id, body) {
    return this.request('PATCH', `/api/subjects/${encodeURIComponent(subject_id)}`, { body });
  }

  /** Удалить дисциплину */
  deleteSubject(subject_id) {
    return this.request('DELETE', `/api/subjects/${encodeURIComponent(subject_id)}`);
  }

  /** Список занятий */
  listLessons(query = {}) {
    return this.request('GET', '/api/lessons', { query });
  }

  /** Добавить занятие */
  createLesson(body) {
    return this.request('POST', '/api/lessons', { body });
  }

  /** Занятие по идентификатору */
  getLesson(lesson_id) {
    return this.request('GET', `/api/lessons/${encodeURIComponent(lesson_id)}`);
  }

  /** Изменить занятие */
  updateLesson(lesson_id, body) {
    return this.request('PATCH', `/api/lessons/${encodeURIComponent(lesson_id)}`, { body });
  }

  /** Удалить занятие */
  deleteLesson(lesson_id) {
    return this.request('DELETE', `/api/lessons/${encodeURIComponent(lesson_id)}`);
  }

  /** Журнал занятия */
  getLessonJournal(lesson_id) {
    return this.request('GET', `/api/lessons/${encodeURIComponent(lesson_id)}/journal`);
  }

  /** Сохранить оценку и посещаемость студента */
  saveJournalEntry(lesson_id, student_id, body) {
    return this.request('PUT', `/api/lessons/${encodeURIComponent(lesson_id)}/journal/${encodeURIComponent(student_id)}`, { body });
  }

  /** Сводная ведомость группы */
  getGroupReport(group_id) {
    return this.request('GET', `/api/reports/groups/${encodeURIComponent(group_id)}`);
  }

  /** Экспорт ведомости группы в CSV */
  exportGroupReport(group_id) {
    return this.request('GET', `/api/reports/groups/${encodeURIComponent(group_id)}/export`);
  }

  /** Успеваемость студента */
  getStudentReport(student_id) {
    return this.request('GET', `/api/reports/students/${encodeURIComponent(student_id)}`);
  }

  /** Сводные показатели для главного экрана */
  getDashboard() {
    return this.request('GET', '/api/dashboard');
  }

}

export const api = new ApiClient();
