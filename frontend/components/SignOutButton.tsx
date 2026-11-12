"use client";

import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function SignOutButton() {
  const router = useRouter();
  async function signOut() {
    await api.POST("/api/v1/auth/logout");
    router.replace("/login");
    router.refresh();
  }
  return (
    <button
      type="button"
      onClick={signOut}
      className="rounded-sm border border-line px-3 py-1.5 text-sm text-ink-700 hover:bg-ink-50"
    >
      Sign out
    </button>
  );
}
