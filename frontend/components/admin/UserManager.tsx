"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { components } from "@/lib/api-client/schema";
import { fmtUtc } from "@/lib/format";
import { useToast } from "../Toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
    <Card className="gap-0 py-0">
      <div className="flex items-center justify-between gap-4 border-b px-6 py-4">
        <h2 className="text-xl font-semibold">Accounts</h2>
        <Button type="button" onClick={() => setAdding(!adding)} aria-expanded={adding} size="sm">
          {adding ? "Cancel" : "Add user"}
        </Button>
      </div>
      {adding && <AddUser onDone={() => { setAdding(false); router.refresh(); }} />}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow><TableHead>User</TableHead><TableHead>Role</TableHead><TableHead>Status</TableHead><TableHead>Last active</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {users.map((u) => {
              const mine = u.id === meId;
              return (
                <TableRow key={u.id} className={u.is_active ? "" : "opacity-60"}>
                  <TableCell>
                    <b>{u.name}</b>{mine && <Badge variant="default" className="ml-2">You</Badge>}
                    <div className="text-xs text-muted-foreground">{u.email}{u.student_id ? ` · ${u.student_id}` : ""}</div>
                  </TableCell>
                  <TableCell>
                    <label className="sr-only" htmlFor={`role-${u.id}`}>Role for {u.name}</label>
                    <NativeSelect id={`role-${u.id}`} value={u.role} disabled={mine || busy === u.id} title={mine ? "You cannot change your own role" : undefined} onChange={(e) => change(u, { role: e.target.value as Role }, `${u.name} is now ${e.target.value}.`)} className="!w-auto !py-1">
                      {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </NativeSelect>
                  </TableCell>
                  <TableCell><Badge variant={u.is_active ? "success" : "destructive"}>{u.is_active ? "Active" : "Deactivated"}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{u.last_active ? fmtUtc(u.last_active) + " UTC" : "No activity logged"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button type="button" onClick={() => setResetFor(u)} variant="outline" size="sm">Reset password</Button>
                      <Button type="button" disabled={mine || busy === u.id} title={mine ? "You cannot deactivate yourself" : undefined} onClick={() => change(u, { is_active: !u.is_active }, u.is_active ? `${u.name} was deactivated and signed out.` : `${u.name} can sign in again.`)} variant="outline" size="sm">
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
            {!users.length && <TableRow><TableCell colSpan={5} className="empty">No users match these filters.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
      {resetFor && <ResetPassword user={resetFor} onClose={() => setResetFor(null)} />}
    </Card>
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
    <form onSubmit={submit} className="grid gap-3 border-b border-border p-4 sm:grid-cols-2 lg:grid-cols-5">
      <Input name="name" required placeholder="Full name" aria-label="Full name" />
      <Input name="email" type="email" required placeholder="Email" aria-label="Email" />
      <NativeSelect name="role" defaultValue="student" aria-label="Role" className="w-full">
        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
      </NativeSelect>
      <Input name="password" type="password" required minLength={8} autoComplete="new-password" placeholder="Temporary password" aria-label="Temporary password" />
      <Button type="submit" disabled={saving}>{saving ? "Creating…" : "Create account"}</Button>
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
    <form onSubmit={submit} className="flex flex-wrap items-center gap-3 border-t border-border bg-muted p-4">
      <span className="text-sm">New password for <b>{user.name}</b></span>
      <Input type="password" required minLength={8} autoComplete="new-password" value={pw} autoFocus onChange={(e) => setPw(e.target.value)} aria-label={`New password for ${user.name}`} className="!w-64" />
      <Button type="submit" disabled={saving || pw.length < 8} size="sm">{saving ? "Saving…" : "Set password"}</Button>
      <Button type="button" onClick={onClose} variant="outline" size="sm">Cancel</Button>
    </form>
  );
}
