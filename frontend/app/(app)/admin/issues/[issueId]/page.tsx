import type { Metadata } from "next";
import Link from "next/link";
import { IssueActions } from "@/components/admin/IssueActions";
import { PageHeader } from "@/components/PageHeader";
import { fmtUtc } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Issue" };

export default async function IssuePage({ params }: PageProps<"/admin/issues/[issueId]">) {
  const { issueId } = await params;
  const api = await serverApi();
  const issue = unwrap(await api.GET("/api/v1/admin/issues/{issue_id}", { params: { path: { issue_id: issueId } } }));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Issues", to: "/admin/issues" }, { label: issue.exc_type }]}
        eyebrow={`${issue.source} · ${issue.count} ${issue.count === 1 ? "time" : "times"}`}
        title={issue.title}
        lede={`Raised in ${issue.culprit}. First seen ${fmtUtc(issue.first_seen)} UTC, last seen ${fmtUtc(issue.last_seen)} UTC.`}
      />
      <IssueActions issue={issue} />
      <h2 className="mb-3 mt-8 text-xl font-semibold">Occurrences</h2>
      <p className="mb-4 text-sm text-muted-foreground">The latest {issue.events.length}. Newest first.</p>
      <div className="space-y-4">
        {issue.events.map((e, n) => (
          <details key={e.id} open={n === 0} className="rounded-xl bg-card text-card-foreground ring-1 ring-foreground/10">
            <summary className="flex cursor-pointer flex-wrap items-center gap-3 px-4 py-3 text-sm">
              <b>{fmtUtc(e.ts)} UTC</b>
              {e.method && <span><b>{e.method}</b> <code>{e.path}</code></span>}
              <span className="text-muted-foreground">{e.user_name ?? (e.user_id ? e.user_id : "anonymous or background job")}</span>
              {e.request_id && (
                <Link href={`/admin/logs?request_id=${e.request_id}`} className="ml-auto text-primary hover:underline">
                  Logs for this request
                </Link>
              )}
            </summary>
            <div className="border-t border-border p-4">
              <p className="mb-3 whitespace-pre-wrap break-words text-sm">{e.message}</p>
              <pre className="max-h-[480px] overflow-auto rounded-md bg-primary p-4 text-xs leading-relaxed text-white">{e.stack_trace}</pre>
            </div>
          </details>
        ))}
      </div>
    </>
  );
}
