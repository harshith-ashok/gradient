// Builds a lived-in demo: students who enrolled days ago, sat the pre-test,
// worked through their plans and (in a few cases) failed a quiz so the adaptive
// logic has already fired. It drives the same services the UI uses, with the
// clock shifted back in time.
import { db, save, clock } from './db.js'
import { startQuiz, submitQuiz, completeTask, peekAnswerKey } from './services/learning.js'

const answers = (quizId, questions, acc) => {
  const key = peekAnswerKey(quizId)
  const out = {}
  questions.forEach((q, i) => {
    const right = ((i * 7 + 3) % 10) / 10 < acc
    out[q.id] = right ? key[q.id] : (key[q.id] + 1) % q.options.length
  })
  return out
}

const sit = (user, req, acc) => {
  const quiz = startQuiz(user, req)
  return submitQuiz(user, quiz.quizId, answers(quiz.quizId, quiz.questions, acc))
}

function simulate(userId, courseId, { daysAgo, pre, quizAcc, todayTasks = null }) {
  const user = db().users.find((u) => u.id === userId)
  const queue = [...quizAcc]
  const nextAcc = () => (queue.length ? queue.shift() : 0.9)
  clock.setDaysAgo(daysAgo)
  sit(user, { courseId, kind: 'pretest' }, pre)
  for (let d = 0; d <= daysAgo; d++) {
    clock.setDaysAgo(daysAgo - d)
    const today = clock.todayISO()
    let budget = d === daysAgo && todayTasks != null ? todayTasks : Infinity
    for (let guard = 0; guard < 40 && budget > 0; guard++) {
      const enr = db().enrollments.find((e) => e.userId === userId && e.courseId === courseId)
      const t = enr.plan.tasks.find((x) => !x.done && x.date <= today)
      if (!t) break
      if (t.type === 'study' || t.type === 'remediation') completeTask(user, courseId, t.id)
      else if (t.type === 'topic-quiz') sit(user, { courseId, kind: 'topic', topicId: t.topicId }, nextAcc())
      else sit(user, { courseId, kind: 'subtopic', subtopicId: t.subtopicId }, nextAcc())
      budget--
    }
  }
  clock.reset()
}

export function runSeed() {
  const s = db()
  if (s.seeded) return
  simulate('u-meera', 'c-cs101', { daysAgo: 3, pre: 0.5, quizAcc: [1, 0.25, 1, 0.75, 1], todayTasks: 1 })
  simulate('u-daniel', 'c-cs101', { daysAgo: 6, pre: 0.8, quizAcc: [1, 1, 1, 1, 0.75], todayTasks: 1 })
  simulate('u-daniel', 'cpp-cs201', { daysAgo: 2, pre: 0.5, quizAcc: [1, 0.75], todayTasks: 0 })
  simulate('u-sofia', 'c-cs101', { daysAgo: 5, pre: 0.2, quizAcc: [0.5, 0.25, 0.5, 1, 0.25], todayTasks: 1 })
  simulate('u-kenji', 'econ-101', { daysAgo: 3, pre: 0.6, quizAcc: [1, 1, 0.75], todayTasks: 1 })
  simulate('u-priya', 'cpp-cs201', { daysAgo: 4, pre: 0.3, quizAcc: [0.75, 1, 0.5], todayTasks: 0 })
  simulate('u-lucas', 'econ-101', { daysAgo: 2, pre: 0.4, quizAcc: [0.75], todayTasks: 1 })
  simulate('u-lucas', 'c-cs101', { daysAgo: 1, pre: 0.5, quizAcc: [], todayTasks: 0 })
  s.seeded = true
  save()
}
