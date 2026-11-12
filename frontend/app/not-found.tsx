import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-md px-6 py-32 text-center">
      <h1 className="text-4xl font-semibold">Page not found</h1>
      <p className="mt-3 text-muted">That page does not exist.</p>
      <Link href="/" className="mt-6 inline-block text-crimson underline">Go home</Link>
    </main>
  );
}
