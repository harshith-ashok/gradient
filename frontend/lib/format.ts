import type { components } from "@/lib/api-client/schema";

type S = components["schemas"];
export type TaskType = S["TaskOut"]["type"];
export type SubStatus = S["SubtopicProgress"]["status"];
export type EnrStatus = S["EnrollmentSummary"]["status"];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Parse a YYYY-MM-DD plan date as a local calendar date (no timezone shift). */
const parse = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const localToday = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export const fmtDay = (iso: string) => {
  const d = parse(iso);
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}`;
};
export const fmtTs = (ts: string) => {
  const d = new Date(ts);
  return `${d.getDate()} ${MONTHS[d.getMonth()]}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};
/** "Today", "Tomorrow", or a short date. Pass the server's `today` so it matches the plan calendar. */
export const relDay = (iso: string, today: string = localToday()) => {
  const diff = Math.round((parse(iso).getTime() - parse(today).getTime()) / 864e5);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  return fmtDay(iso);
};
export const plural = (n: number, w: string, pl = `${w}s`) => `${n} ${n === 1 ? w : pl}`;
export const firstName = (name: string) => name.replace(/^(Dr|Prof)\.?\s+/, "").split(" ")[0];

export const TASK_LABEL: Record<TaskType, string> = {
  study: "Study", quiz: "Quiz", confirm: "Confirmation quiz", remediation: "Remediation",
  retake: "Retake", topic_quiz: "Topic quiz",
};
export const STATUS_LABEL: Record<SubStatus, string> = {
  new: "Not started", learning: "In progress", review: "Needs review", mastered: "Mastered",
};
export const STATUS_TONE: Record<SubStatus, string> = {
  new: "", learning: "badge-info", review: "badge-warn", mastered: "badge-ok",
};
export const ENR_STATUS: Record<EnrStatus, string> = {
  "on-track": "On track", attention: "Needs attention", completed: "Completed",
};
export const ENR_TONE: Record<EnrStatus, string> = {
  "on-track": "badge-info", attention: "badge-warn", completed: "badge-ok",
};
export const TASK_TONE: Partial<Record<TaskType, string>> = {
  remediation: "badge-warn", retake: "badge-warn", topic_quiz: "badge-crimson",
};

/** Mastery colour relative to the pass mark. */
export const masteryTone = (v: number, threshold: number) =>
  v >= threshold ? "ok" : v >= threshold - 25 ? "warn" : "bad";

/** Where a plan task opens. */
export function taskHref(courseId: string, t: { type: TaskType; subtopic_id?: string | null; topic_id?: string | null }) {
  const base = `/student/courses/${courseId}`;
  if (t.type === "study") return `${base}/subtopics/${t.subtopic_id}?tab=summary`;
  if (t.type === "remediation") return `${base}/subtopics/${t.subtopic_id}?tab=help`;
  if (t.type === "topic_quiz") return `${base}/quiz?kind=topic&topicId=${t.topic_id}`;
  return `${base}/quiz?kind=subtopic&subtopicId=${t.subtopic_id}`;
}

/** Timestamp in UTC with seconds ("12 Nov, 17:09:56"). Fixed zone so server and browser render the same text. */
export const fmtUtc = (ts: string) => {
  const d = new Date(ts);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
};
