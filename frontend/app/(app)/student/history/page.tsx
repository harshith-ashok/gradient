import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { fmtTs } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Quiz history" };

export default async function HistoryPage() {
  const api = await serverApi();
  const courses = unwrap(await api.GET("/api/v1/student/history"));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Progress", to: "/student/progress" }, { label: "Quiz history" }]}
        eyebrow="Every attempt"
        title="Quiz history"
        lede="All your quiz attempts, newest first, with the score for each sub-topic."
      />
      {courses.length === 0 && (
        <Card className="gap-0 py-0 empty"><h3>No attempts yet</h3><p>Your quiz results will appear here.</p><Link href="/student/courses" className={buttonVariants()}>Browse courses</Link></Card>
      )}
      <div className="space-y-8">
        {courses.map((c) => (
          <section key={c.course_id}>
            <h2 className="mb-3 text-xl font-semibold">{c.code} · {c.title} <span className="text-sm font-normal text-muted-foreground">({c.attempts.length} attempts)</span></h2>
            <Card className="gap-0 py-0 divide-y divide-border">
              {c.attempts.map((a) => (
                <details key={a.id} className="group px-6 py-3.5">
                  <summary className="flex cursor-pointer list-none flex-wrap items-center gap-3">
                    <span className="w-32 text-sm text-muted-foreground">{fmtTs(a.created_at)}</span>
                    <span className="min-w-0 flex-1 font-medium">{a.title}</span>
                    <span className="w-12 text-right tabular-nums">{Math.round(a.score)}%</span>
                    <Badge variant={a.passed == null ? "secondary" : a.passed ? "success" : "destructive"}>
                      {a.passed == null ? "Diagnostic" : a.passed ? "Passed" : "Below pass mark"}
                    </Badge>
                    <span className="text-muted-foreground group-open:rotate-45" aria-hidden="true">＋</span>
                  </summary>
                  <div className="mt-3 rounded-md bg-muted p-4 text-sm">
                    <p className="mb-2 text-muted-foreground">
                      {a.correct} of {a.total} correct{a.threshold != null ? ` · pass mark ${a.threshold}%` : ""}
                    </p>
                    <ul className="space-y-1">
                      {a.breakdown.map((b) => (
                        <li key={b.subtopic_id} className="flex justify-between gap-4">
                          <span>{b.title}</span>
                          <span className="tabular-nums text-muted-foreground">{b.correct}/{b.total} · {Math.round(b.score)}%</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </details>
              ))}
            </Card>
          </section>
        ))}
      </div>
    </>
  );
}
