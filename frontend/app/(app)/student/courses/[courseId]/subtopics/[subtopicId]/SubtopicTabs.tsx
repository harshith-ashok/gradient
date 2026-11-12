"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useToast } from "@/components/Toast";
import { api, errorMessage } from "@/lib/api";
import { FlashcardDeck } from "@/components/FlashcardDeck";
import type { components } from "@/lib/api-client/schema";
import { TABS, type Tab } from "./tabs";

type Content = components["schemas"]["SubtopicContent"];
type Props = {
  content: Content; initialTab: Tab; courseId: string; subtopicId: string;
  enrolled: boolean; studied: boolean; pendingStudy: boolean; pendingHelp: boolean;
};

export function SubtopicTabs({ content, initialTab, courseId, subtopicId, enrolled, studied, pendingStudy, pendingHelp }: Props) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>(initialTab);
  const quizHref = `/student/courses/${courseId}/quiz?kind=subtopic&subtopicId=${subtopicId}`;

  async function complete(type: "study" | "remediation") {
    setBusy(true);
    const { data, error } = await api.POST("/api/v1/student/courses/{course_id}/subtopics/{subtopic_id}/complete", {
      params: { path: { course_id: courseId, subtopic_id: subtopicId } },
      body: { type },
    });
    setBusy(false);
    if (error) return toast(errorMessage(error), "error");
    toast(type === "study" ? "Marked as studied." : "Remediation material marked as reviewed.", "success");
    if (data?.day_status) toast(data.day_status.message, "success", 6500);
    router.refresh();
  }

  const select = (t: Tab) => {
    setTab(t);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", t);
    window.history.replaceState(null, "", url);
  };
  const label: Record<Tab, string> = {
    summary: "Summary",
    cards: `Flashcards (${content.flashcards.length})`,
    help: "Extra help",
  };

  return (
    <div>
      <div role="tablist" className="mb-4 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => select(t)}
            className="-mb-px border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted hover:text-ink-900 aria-selected:border-crimson aria-selected:text-crimson"
          >
            {label[t]}
          </button>
        ))}
      </div>
      <div className="rounded-md border border-line bg-surface p-7">
        {tab === "summary" && (
          <>
            {content.summary.map((p, i) => (
              <p key={i} className="mb-4 text-base leading-[1.7]">{p}</p>
            ))}
            <h3 className="mb-2 mt-6 font-sans text-sm font-semibold">Key points</h3>
            <ul className="list-disc space-y-1 pl-5 leading-relaxed">
              {content.points.map((p) => <li key={p}>{p}</li>)}
            </ul>
            <hr className="my-6 border-line-soft" />
            <div className="flex flex-wrap items-center gap-3">
              {enrolled && pendingStudy && (
                <button type="button" className="btn btn-crimson" disabled={busy} onClick={() => complete("study")}>Mark as studied</button>
              )}
              {enrolled && !pendingStudy && studied && <span className="badge badge-ok">Studied</span>}
              <button type="button" className="btn btn-secondary" onClick={() => select("cards")}>Practise with flashcards</button>
            </div>
          </>
        )}
        {tab === "cards" && <FlashcardDeck cards={content.flashcards} />}
        {tab === "help" &&
          (content.remediation ? (
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-semibold">A different way to think about it</h3>
                <p className="mt-2 text-base leading-[1.7]">{content.remediation.explanation}</p>
              </div>
              <div>
                <h3 className="text-xl font-semibold">Try this</h3>
                <ol className="mt-2 list-decimal space-y-1 pl-5 leading-relaxed">
                  {content.remediation.steps.map((s) => <li key={s}>{s}</li>)}
                </ol>
              </div>
              {enrolled && (
                <div className="flex flex-wrap gap-3">
                  {pendingHelp && (
                    <button type="button" className="btn btn-crimson" disabled={busy} onClick={() => complete("remediation")}>Mark remediation as reviewed</button>
                  )}
                  <Link href={quizHref} className="btn btn-secondary">Retake the quiz</Link>
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted">No extra material for this sub-topic yet.</p>
          ))}
      </div>
    </div>
  );
}
