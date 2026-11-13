import { Crest } from "@/components/Crest";
import { NavLinks } from "@/components/NavLinks";
import { SignOutButton } from "@/components/SignOutButton";
import { ToastProvider } from "@/components/Toast";
import { homeFor } from "@/lib/auth";
import { currentUser } from "@/lib/session-server";

const ROLE_LABEL = { student: "Student", faculty: "Faculty", admin: "Management" } as const;

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await currentUser();
  return (
    <ToastProvider>
    <div className="min-h-screen">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-[68px] max-w-[1200px] items-center gap-6 px-6">
          <a href={homeFor(user.role)} className="flex items-center gap-3">
            <Crest size={32} />
            <span className=" text-xl font-bold text-foreground">Gradient</span>
          </a>
          <NavLinks role={user.role} />
          <div className="text-right text-sm leading-tight">
            <div className="font-medium text-foreground">{user.name}</div>
            <div className="text-xs text-muted-foreground">{ROLE_LABEL[user.role]}</div>
          </div>
          <SignOutButton />
        </div>
      </header>
      <main className="mx-auto max-w-[1200px] px-6 py-10">{children}</main>
    </div>
    </ToastProvider>
  );
}
