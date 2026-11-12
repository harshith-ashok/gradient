import type { Metadata } from "next";

export const metadata: Metadata = { title: "My courses" };

export default function Page() {
  return (
    <>
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-crimson">Faculty portal</p>
      <h1 className="mt-2 text-4xl font-semibold">My courses</h1>
      <p className="mt-3 max-w-prose text-muted">You are signed in. Syllabus upload and the topic editor arrive in a later phase.</p>
    </>
  );
}
