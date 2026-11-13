"use client";

import { Rich } from "@/components/Rich";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useToast } from "@/components/Toast";
import { api, errorMessage } from "@/lib/api";
import { FlashcardDeck } from "@/components/FlashcardDeck";
import type { components } from "@/lib/api-client/schema";
import { TABS, type Tab } from "./tabs";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";

type Content = components["schemas"]["SubtopicContent"];
type Props = {
  content: Content; initialTab: Tab; courseId: string; subtopicId: string;
  enrolled: boolean; studied: boolean; pendingStudy: boolean; pendingHelp: boolean;
};

const LEVEL_LABEL = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced", expert: "Expert" } as const;

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
      <div role="tablist" className="mb-4 flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => select(t)}
            className="-mb-px border-b-2 border-transparent px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground aria-selected:border-primary aria-selected:text-primary"
          >
            {label[t]}
          </button>
        ))}
      </div>
      <div className="rounded-md border border-border bg-card p-7">
        {tab === "summary" && (
          <>
            <p className="mb-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="default">{LEVEL_LABEL[content.summary_level]} summary</Badge>
              {enrolled
                ? "Written for your current level in this sub-topic. It moves up as you pass quizzes."
                : "Enrol to get summaries matched to your level."}
            </p>
            {content.summary.map((p, i) => (
              <div key={i} className="mb-4 text-base leading-[1.7]"><Rich>{p}</Rich></div>
            ))}
            <h3 className="mb-2 mt-6 font-sans text-sm font-semibold">Key points</h3>
            <ul className="list-disc space-y-1 pl-5 leading-relaxed">
              {content.points.map((p) => <li key={p}><Rich inline>{p}</Rich></li>)}
            </ul>
            <hr className="my-6 border-border" />
            <div className="flex flex-wrap items-center gap-3">
              {enrolled && pendingStudy && (
                <Button type="button" disabled={busy} onClick={() => complete("study")}>Mark as studied</Button>
              )}
              {enrolled && !pendingStudy && studied && <Badge variant="success">Studied</Badge>}
              <Button type="button" onClick={() => select("cards")} variant="outline">Practise with flashcards</Button>
            </div>
          </>
        )}
        {tab === "cards" && <FlashcardDeck cards={content.flashcards} />}
        {tab === "help" &&
          (content.remediation ? (
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-semibold">A different way to think about it</h3>
                <div className="mt-2 text-base leading-[1.7]"><Rich>{content.remediation.explanation}</Rich></div>
              </div>
              <div>
                <h3 className="text-xl font-semibold">Try this</h3>
                <ol className="mt-2 list-decimal space-y-1 pl-5 leading-relaxed">
                  {content.remediation.steps.map((s) => <li key={s}><Rich inline>{s}</Rich></li>)}
                </ol>
              </div>
              {enrolled && (
                <div className="flex flex-wrap gap-3">
                  {pendingHelp && (
                    <Button type="button" disabled={busy} onClick={() => complete("remediation")}>Mark remediation as reviewed</Button>
                  )}
                  <Link href={quizHref} className={buttonVariants({ variant: "outline" })}>Retake the quiz</Link>
                </div>
              )}
            </div>
          ) : (
            <p className="text-muted-foreground">No extra material for this sub-topic yet.</p>
          ))}
      </div>
    </div>
  );
}
