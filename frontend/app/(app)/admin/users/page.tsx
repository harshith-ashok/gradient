import type { Metadata } from "next";
import Link from "next/link";
import { UserManager } from "@/components/admin/UserManager";
import { Pager, Stat, one, qs } from "@/components/admin/ui";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Users" };
const ROLES = ["student", "faculty", "admin"] as const;
const PAGE_SIZE = 15;

export default async function UsersPage({ searchParams }: PageProps<"/admin/users">) {
  const sp = await searchParams;
  const q = one(sp.q) ?? "";
  const role = ROLES.find((r) => r === one(sp.role));
  const active = one(sp.active) === "yes" ? true : one(sp.active) === "no" ? false : undefined;
  const page = Math.max(1, Number(one(sp.page)) || 1);

  const api = await serverApi();
  const data = unwrap(
    await api.GET("/api/v1/admin/users", { params: { query: { q, role, active, page, page_size: PAGE_SIZE } } }),
  );
  const me = unwrap(await api.GET("/api/v1/auth/me"));
  const href = (p: number) => `/admin/users${qs({ q, role, active: one(sp.active), page: p })}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "Users" }]}
        eyebrow="Management"
        title="Users"
        lede="Create accounts, change roles, switch accounts off and reset passwords. Every change is written to the audit log."
      />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat value={data.by_role.student ?? 0} label="Students" />
        <Stat value={data.by_role.faculty ?? 0} label="Faculty" />
        <Stat value={data.by_role.admin ?? 0} label="Admins" />
        <Stat value={data.inactive} label="Deactivated accounts" tone={data.inactive ? "warn" : undefined} />
      </div>

      <div className="card mb-6">
        <form method="get" className="flex flex-wrap items-center gap-3 p-4">
          <label className="sr-only" htmlFor="q">Search users</label>
          <input id="q" name="q" defaultValue={q} className="input !w-72" placeholder="Search by name, email or ID" />
          <label className="sr-only" htmlFor="role">Role</label>
          <select id="role" name="role" defaultValue={role ?? ""} className="input !w-auto">
            <option value="">All roles</option>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <label className="sr-only" htmlFor="active">Account state</label>
          <select id="active" name="active" defaultValue={one(sp.active) ?? ""} className="input !w-auto">
            <option value="">Active and deactivated</option>
            <option value="yes">Active only</option>
            <option value="no">Deactivated only</option>
          </select>
          <button type="submit" className="btn btn-sm">Apply</button>
          {(q || role || one(sp.active)) && <Link href="/admin/users" className="text-sm text-crimson hover:underline">Clear</Link>}
          <span className="ml-auto text-sm text-muted">{data.total} {data.total === 1 ? "user" : "users"}</span>
        </form>
      </div>

      <UserManager users={data.items} meId={me.id} />
      <div className="card -mt-px rounded-t-none border-t-0">
        <Pager page={page} size={PAGE_SIZE} total={data.total} href={href} />
      </div>
    </>
  );
}
