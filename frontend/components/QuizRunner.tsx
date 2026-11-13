"use client";

import { useState } from "react";
import { Rich } from "./Rich";
import type { components } from "@/lib/api-client/schema";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

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
      <div className="mb-3 flex items-center gap-4 text-sm text-muted-foreground">
        <span>Question {i + 1} of {questions.length}</span>
        <div className="meter thin flex-1"><i style={{ width: `${((i + 1) / questions.length) * 100}%` }} /></div>
        <span>{answered} answered</span>
      </div>
      <Card className="gap-0 p-6">
        <div className="mb-5  text-xl leading-snug" data-question={q.text}><Rich>{q.text}</Rich></div>
        <div role="group" aria-label="Answer options">
          {q.options.map((o, idx) => (
            <button
              key={idx} type="button" className="opt" aria-pressed={answers[q.id] === idx}
              onClick={() => setAnswers({ ...answers, [q.id]: idx })}
            >
              <span className="key">{LETTERS[idx]}</span><span className="min-w-0" data-option={o}><Rich inline>{o}</Rich></span>
            </button>
          ))}
        </div>
        <div className="mt-5 flex justify-between">
          <Button type="button" disabled={i === 0} onClick={() => setI(i - 1)} variant="outline">Back</Button>
          {!last ? (
            <Button type="button" disabled={answers[q.id] === undefined} onClick={() => setI(i + 1)}>Next question</Button>
          ) : (
            <Button type="button" disabled={submitting || answers[q.id] === undefined} onClick={() => onSubmit(answers)}>
              {submitting ? "Submitting…" : "Submit answers"}
            </Button>
          )}
        </div>
        {last && unanswered > 0 && (
          <p className="mt-3.5 text-sm text-muted-foreground">
            {unanswered} unanswered question{unanswered === 1 ? "" : "s"} will be marked incorrect. Use Back to review.
          </p>
        )}
      </Card>
    </div>
  );
}
