"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";
import { useToast } from "../Toast";

type User = components["schemas"]["ManagedUser"];
type Role = User["role"];
const ROLES: Role[] = ["student", "faculty", "admin"];

export function UserManager({ users, meId }: { users: User[]; meId: string }) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [resetFor, setResetFor] = useState<User | null>(null);
  const [adding, setAdding] = useState(false);

  async function change(u: User, body: { role?: Role; is_active?: boolean }, done: string) {
    setBusy(u.id);
    const { error } = await api.PUT("/api/v1/admin/users/{user_id}", { params: { path: { user_id: u.id } }, body });
    setBusy(null);
    if (error) return toast(errorMessage(error), "error");
    toast(done, "success");
    router.refresh();
  }

  return (
    <div className="card">
      <div className="card-head">
        <h2 className="text-xl font-semibold">Accounts</h2>
        <button type="button" className="btn btn-sm" onClick={() => setAdding(!adding)} aria-expanded={adding}>
          {adding ? "Cancel" : "Add user"}
        </button>
      </div>
      {adding && <AddUser onDone={() => { setAdding(false); router.refresh(); }} />}
      <div className="overflow-x-auto">
        <table className="table">
          <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Last active</th><th className="text-right">Actions</th></tr></thead>
          <tbody>
            {users.map((u) => {
              const mine = u.id === meId;
              return (
                <tr key={u.id} className={u.is_active ? "" : "opacity-60"}>
                  <td>
                    <b>{u.name}</b>{mine && <span className="badge badge-crimson ml-2">You</span>}
                    <div className="text-xs text-muted">{u.email}{u.student_id ? ` · ${u.student_id}` : ""}</div>
                  </td>
                  <td>
                    <label className="sr-only" htmlFor={`role-${u.id}`}>Role for {u.name}</label>
                    <select
                      id={`role-${u.id}`} value={u.role} disabled={mine || busy === u.id} className="input !w-auto !py-1"
                      title={mine ? "You cannot change your own role" : undefined}
                      onChange={(e) => change(u, { role: e.target.value as Role }, `${u.name} is now ${e.target.value}.`)}
                    >
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td><span className={`badge ${u.is_active ? "badge-ok" : "badge-bad"}`}>{u.is_active ? "Active" : "Deactivated"}</span></td>
                  <td className="text-sm text-muted">{u.last_active ? fmtUtc(u.last_active) + " UTC" : "No activity logged"}</td>
                  <td className="text-right">
                    <div className="flex justify-end gap-2">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setResetFor(u)}>Reset password</button>
                      <button
                        type="button" className="btn btn-secondary btn-sm" disabled={mine || busy === u.id}
                        title={mine ? "You cannot deactivate yourself" : undefined}
                        onClick={() => change(u, { is_active: !u.is_active }, u.is_active ? `${u.name} was deactivated and signed out.` : `${u.name} can sign in again.`)}
                      >
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {!users.length && <tr><td colSpan={5} className="empty">No users match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      {resetFor && <ResetPassword user={resetFor} onClose={() => setResetFor(null)} />}
    </div>
  );
}

function AddUser({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setSaving(true);
    const { error } = await api.POST("/api/v1/admin/users", {
      body: { name: String(f.get("name")), email: String(f.get("email")), role: String(f.get("role")) as Role, password: String(f.get("password")) },
    });
    setSaving(false);
    if (error) return toast(errorMessage(error, "Check the details: the password needs at least 8 characters."), "error");
    toast("Account created.", "success");
    onDone();
  }
  return (
    <form onSubmit={submit} className="grid gap-3 border-b border-line-soft p-4 sm:grid-cols-2 lg:grid-cols-5">
      <input name="name" required className="input" placeholder="Full name" aria-label="Full name" />
      <input name="email" type="email" required className="input" placeholder="Email" aria-label="Email" />
      <select name="role" defaultValue="student" className="input" aria-label="Role">
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
      <input name="password" type="password" required minLength={8} autoComplete="new-password" className="input" placeholder="Temporary password" aria-label="Temporary password" />
      <button type="submit" className="btn btn-crimson" disabled={saving}>{saving ? "Creating…" : "Create account"}</button>
    </form>
  );
}

function ResetPassword({ user, onClose }: { user: User; onClose: () => void }) {
  const toast = useToast();
  const [pw, setPw] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    const { error } = await api.POST("/api/v1/admin/users/{user_id}/password", {
      params: { path: { user_id: user.id } }, body: { password: pw },
    });
    setSaving(false);
    if (error) return toast(errorMessage(error, "The password needs at least 8 characters."), "error");
    toast(`Password changed for ${user.name}. Tell them the new one in person.`, "success");
    onClose();
  }
  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-3 border-t border-line-soft bg-ink-50 p-4">
      <span className="text-sm">New password for <b>{user.name}</b></span>
      <input
        type="password" required minLength={8} autoComplete="new-password" value={pw} autoFocus
        onChange={(e) => setPw(e.target.value)} className="input !w-64" aria-label={`New password for ${user.name}`}
      />
      <button type="submit" className="btn btn-crimson btn-sm" disabled={saving || pw.length < 8}>{saving ? "Saving…" : "Set password"}</button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
    </form>
  );
}
