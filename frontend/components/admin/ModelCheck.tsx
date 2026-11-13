"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/** Asking the model server can take seconds when it is down, so it is a button, not part of page load. */
export function ModelCheck() {
  const [state, setState] = useState<"idle" | "checking" | "up" | "down">("idle");
  async function check() {
    setState("checking");
    const { data } = await api.GET("/api/v1/faculty/ai/health");
    setState(data?.ok ? "up" : "down");
  }
  if (state === "up") return <Badge variant="success">Up</Badge>;
  if (state === "down") return <Button type="button" onClick={check} variant="destructive" size="sm">Unreachable · retry</Button>;
  return (
    <Button type="button" onClick={check} disabled={state === "checking"} variant="outline" size="sm">
      {state === "checking" ? "Checking…" : "Check now"}
    </Button>
  );
}
