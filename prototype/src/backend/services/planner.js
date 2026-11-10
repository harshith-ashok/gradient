// Pure scheduling logic for study plans. No database access in here.
import { dayDiff, addDaysISO, uid } from '../util.js'

export const MINUTES = { study: 25, confirm: 15, quiz: 15, remediation: 20, retake: 15, 'topic-quiz': 20 }
export const QUIZ_LIKE = ['quiz', 'confirm', 'retake']

const task = (type, topic, subtopic, title, minutes) => ({
  id: uid('task'),
  type,
  topicId: topic.id,
  subtopicId: subtopic ? subtopic.id : null,
  title,
  minutes,
  day: null,
  date: null,
  done: false,
  doneAt: null,
  result: null,
})

/**
 * Build the ordered list of tasks from pre-test results.
 *  - Topics stay in syllabus order (later ideas build on earlier ones).
 *  - Within a topic the weakest sub-topics come first.
 *  - Sub-topics the student already knows only get a short confirmation quiz.
 *  - Each topic with several sub-topics ends with a topic quiz.
 */
export function buildTasks(course, preBySub, threshold) {
  const tasks = []
  for (const topic of course.topics) {
    const ordered = topic.subtopics
      .map((s, i) => ({ s, i, score: preBySub[s.id]?.score ?? 0 }))
      .sort((a, b) => a.score - b.score || a.i - b.i)
    for (const { s, score } of ordered) {
      if (score >= threshold) {
        tasks.push(task('confirm', topic, s, `Confirm mastery: ${s.title}`, MINUTES.confirm))
      } else {
        tasks.push(task('study', topic, s, `Study: ${s.title}`, score === 0 ? 30 : MINUTES.study))
        tasks.push(task('quiz', topic, s, `Quiz: ${s.title}`, MINUTES.quiz))
      }
    }
    if (topic.subtopics.length > 1) tasks.push(task('topic-quiz', topic, null, `Topic quiz: ${topic.title}`, MINUTES['topic-quiz']))
  }
  return tasks
}

/**
 * Assign calendar days to every unfinished task, in list order, starting today
 * and honouring the daily time budget. Finished tasks keep the day they had.
 * Returns how many unfinished tasks moved to a later day.
 */
export function repack(tasks, startISO, todayISO, minutesPerDay) {
  const todayIdx = Math.max(0, dayDiff(startISO, todayISO))
  const used = {}
  for (const t of tasks) if (t.done && t.day != null) used[t.day] = (used[t.day] || 0) + t.minutes
  let day = todayIdx
  let moved = 0
  for (const t of tasks) {
    if (t.done) continue
    while ((used[day] || 0) > 0 && (used[day] || 0) + t.minutes > minutesPerDay) day++
    if (t.day != null && day > t.day) moved++
    t.day = day
    t.date = addDaysISO(startISO, day)
    used[day] = (used[day] || 0) + t.minutes
  }
  return moved
}

/**
 * Insert follow-up tasks after `skip` unfinished tasks, but never after the
 * unfinished topic quiz of the same topic (it must come last).
 */
export function insertLater(tasks, extra, topicId, skip) {
  let seen = 0
  let at = tasks.length
  for (let i = 0; i < tasks.length; i++) {
    if (tasks[i].done) continue
    seen++
    if (seen === skip) {
      at = i + 1
      break
    }
  }
  const tq = tasks.findIndex((t) => !t.done && t.type === 'topic-quiz' && t.topicId === topicId)
  if (tq !== -1 && tq < at) at = tq
  tasks.splice(at, 0, ...extra)
}

export const makeTask = task
