"use client";

import dynamic from "next/dynamic";

/** The editor is a few hundred KB, so it loads only on pages that need it. */
export const Editor = dynamic(() => import("./CodeEditor"), {
  ssr: false,
  loading: () => <div className="h-[380px] animate-pulse rounded-md border border-border bg-muted" aria-busy="true" />,
});
export { LANG_LABEL, type Lang } from "./CodeEditor";
