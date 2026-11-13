import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StudentProgress } from "@/components/StudentProgress";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Student progress" };

export default async function AdminDashboard({ searchParams }: PageProps<"/admin">) {
  return (
    <>
      <PageHeader
        eyebrow="Management"
        title="Student progress"
        lede="Overall progress, per-topic mastery and upcoming tasks for every student."
        actions={<Link href="/admin/settings" className={buttonVariants({ variant: "outline" })}>Quiz pass mark settings</Link>}
      />
      <StudentProgress scope="admin" sp={await searchParams} />
    </>
  );
}
