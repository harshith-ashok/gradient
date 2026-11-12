import type { Metadata } from "next";
import { LogViewer } from "@/components/admin/LogViewer";
import { PageHeader } from "@/components/PageHeader";
import { one } from "@/components/admin/ui";

export const metadata: Metadata = { title: "Logs" };

export default async function LogsPage({ searchParams }: PageProps<"/admin/logs">) {
  const sp = await searchParams;
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "Logs" }]}
        eyebrow="Management"
        title="Logs"
        lede="API requests, warnings and errors from the web server and the AI worker, plus an audit trail of admin changes. Request bodies, cookies and passwords are never stored."
      />
      <LogViewer initialRequestId={one(sp.request_id) ?? ""} />
    </>
  );
}
