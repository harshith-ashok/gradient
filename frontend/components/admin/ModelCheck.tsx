"use client";

import { useState } from "react";
import { api } from "@/lib/api";

/** Asking the model server can take seconds when it is down, so it is a button, not part of page load. */
export function ModelCheck() {
  const [state, setState] = useState<"idle" | "checking" | "up" | "down">("idle");
  async function check() {
    setState("checking");
    const { data } = await api.GET("/api/v1/faculty/ai/health");
    setState(data?.ok ? "up" : "down");
  }
  if (state === "up") return <span className="badge badge-ok">Up</span>;
  if (state === "down") return <button type="button" className="badge badge-bad" onClick={check}>Unreachable · retry</button>;
  return (
    <button type="button" className="btn btn-secondary btn-sm" onClick={check} disabled={state === "checking"}>
      {state === "checking" ? "Checking…" : "Check now"}
    </button>
  );
}
