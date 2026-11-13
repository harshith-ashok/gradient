import type { Metadata } from "next";
import { EndpointTable } from "@/components/admin/EndpointTable";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Roles & endpoints" };

export default async function AccessPage() {
  const api = await serverApi();
  const data = unwrap(await api.GET("/api/v1/admin/access", { params: { query: { hours: 24 } } }));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "Roles & endpoints" }]}
        eyebrow="Management"
        title="Roles & endpoints"
        lede="Every API endpoint, who may call it, and how it behaved in the last 24 hours. The access column is read from the live route guards, so it cannot drift from what the server enforces."
      />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        {data.roles.map((r) => (
          <Card key={r.role} className="gap-0 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold capitalize">{r.role}</h2>
              <Badge variant="secondary">{r.endpoints} endpoints</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{r.description}</p>
            <p className="mt-3 text-sm">
              <b>{r.users}</b> {r.users === 1 ? "user" : "users"} · <b>{r.active_users}</b> active
            </p>
          </Card>
        ))}
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        The three roles are fixed. To change what someone can do, change their role on the Users page.
      </p>
      <EndpointTable endpoints={data.endpoints} />
    </>
  );
}
