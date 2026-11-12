"use client";

import { useState } from "react";
import type { components } from "@/lib/api-client/schema";

type Question = components["schemas"]["QuizQuestion"];
const LETTERS = ["A", "B", "C", "D", "E", "F"];

export function QuizRunner({
  questions, submitting, onSubmit,
}: { questions: Question[]; submitting: boolean; onSubmit: (answers: Record<string, number>) => void }) {
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const q = questions[i];
  const last = i === questions.length - 1;
  const answered = Object.keys(answers).length;
  const unanswered = questions.length - answered;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center gap-4 text-sm text-muted">
        <span>Question {i + 1} of {questions.length}</span>
        <div className="meter thin flex-1"><i style={{ width: `${((i + 1) / questions.length) * 100}%` }} /></div>
        <span>{answered} answered</span>
      </div>
      <div className="card card-pad">
        <p className="mb-5 font-serif text-xl leading-snug">{q.text}</p>
        <div role="group" aria-label="Answer options">
          {q.options.map((o, idx) => (
            <button
              key={idx} type="button" className="opt" aria-pressed={answers[q.id] === idx}
              onClick={() => setAnswers({ ...answers, [q.id]: idx })}
            >
              <span className="key">{LETTERS[idx]}</span><span>{o}</span>
            </button>
          ))}
        </div>
        <div className="mt-5 flex justify-between">
          <button type="button" className="btn btn-secondary" disabled={i === 0} onClick={() => setI(i - 1)}>Back</button>
          {!last ? (
            <button type="button" className="btn" disabled={answers[q.id] === undefined} onClick={() => setI(i + 1)}>Next question</button>
          ) : (
            <button type="button" className="btn btn-crimson" disabled={submitting || answers[q.id] === undefined} onClick={() => onSubmit(answers)}>
              {submitting ? "Submitting…" : "Submit answers"}
            </button>
          )}
        </div>
        {last && unanswered > 0 && (
          <p className="mt-3.5 text-sm text-muted">
            {unanswered} unanswered question{unanswered === 1 ? "" : "s"} will be marked incorrect. Use Back to review.
          </p>
        )}
      </div>
    </div>
  );
}
