import type { Metadata } from "next";
import { Crest } from "@/components/Crest";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { redirect } = await searchParams;
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-deep p-12 text-white lg:flex">
        <div className="flex items-center gap-3.5">
          <Crest size={46} />
          <div>
            <div className="font-serif text-[26px] font-bold leading-none text-white">Gradient</div>
            <div className="mt-1.5 text-[10px] font-medium uppercase tracking-[0.16em] text-[#c9a9a0]">
              Learning Portal
            </div>
          </div>
        </div>
        <div className="max-w-md">
          <h1 className="font-serif text-[42px] font-semibold leading-[1.1] text-white">
            A study plan that <em className="text-crimson-bright">adapts</em> to every learner.
          </h1>
          <p className="mt-5 text-[#e6d3cd]">
            Faculty publish the syllabus. Students sit a short pre-test and receive a personal plan
            that reschedules itself when a topic needs more time.
          </p>
        </div>
        <p className="text-xs text-[#c9a9a0]">Demo data · sign in with one of the sample accounts.</p>
      </aside>
      <section className="flex items-center justify-center px-6 py-12">
        <LoginForm redirectTo={typeof redirect === "string" ? redirect : null} />
      </section>
    </div>
  );
}
