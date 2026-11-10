import { createRouter, createWebHistory } from 'vue-router'
import { session, homeFor } from '../stores/session.js'

const S = ['student']
const F = ['faculty']
const A = ['admin']

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../components/AppShell.vue'),
    children: [
      { path: '', name: 'root', component: { render: () => null } },
      // Student
      { path: 'student', name: 'student-home', component: () => import('../views/student/StudentDashboard.vue'), meta: { roles: S } },
      { path: 'student/courses', name: 'catalog', component: () => import('../views/student/CourseCatalog.vue'), meta: { roles: S } },
      { path: 'student/courses/:courseId', name: 'course', component: () => import('../views/student/CourseView.vue'), meta: { roles: S } },
      { path: 'student/courses/:courseId/pretest', name: 'pretest', component: () => import('../views/student/QuizView.vue'), meta: { roles: S }, props: { pretest: true } },
      { path: 'student/courses/:courseId/quiz', name: 'quiz', component: () => import('../views/student/QuizView.vue'), meta: { roles: S } },
      { path: 'student/courses/:courseId/plan', name: 'plan', component: () => import('../views/student/PlanView.vue'), meta: { roles: S } },
      { path: 'student/courses/:courseId/subtopics/:subtopicId', name: 'subtopic', component: () => import('../views/student/SubtopicView.vue'), meta: { roles: S } },
      { path: 'student/practice', name: 'practice', component: () => import('../views/student/PracticeView.vue'), meta: { roles: S } },
      { path: 'student/progress', name: 'progress', component: () => import('../views/student/ProgressView.vue'), meta: { roles: S } },
      // Faculty
      { path: 'faculty', name: 'faculty-home', component: () => import('../views/faculty/FacultyCourses.vue'), meta: { roles: F } },
      { path: 'faculty/upload', name: 'upload', component: () => import('../views/faculty/SyllabusUpload.vue'), meta: { roles: F } },
      { path: 'faculty/courses/:courseId', name: 'editor', component: () => import('../views/faculty/CourseEditor.vue'), meta: { roles: F, wide: true } },
      // Management
      { path: 'admin', name: 'admin-home', component: () => import('../views/admin/AdminDashboard.vue'), meta: { roles: A } },
      { path: 'admin/students/:studentId', name: 'admin-student', component: () => import('../views/admin/StudentDetail.vue'), meta: { roles: A } },
      { path: 'admin/settings', name: 'admin-settings', component: () => import('../views/admin/AdminSettings.vue'), meta: { roles: A } },
    ],
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFound.vue'), meta: { public: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  await session.init()
  const user = session.user
  if (to.meta.public) {
    if (user && to.name === 'login') return homeFor(user)
    return true
  }
  if (!user) return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  if (to.name === 'root') return homeFor(user)
  if (to.meta.roles && !to.meta.roles.includes(user.role)) return homeFor(user)
  return true
})

export default router
