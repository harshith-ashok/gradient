import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ProgressTabs } from "@/components/ProgressTabs";
import { serverApi, unwrap } from "@/lib/server-api";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Progress" };

export default async function ProgressPage() {
  const api = await serverApi();
  const { enrollments } = unwrap(await api.GET("/api/v1/student/progress"));
  return (
    <>
      <PageHeader eyebrow="Progress dashboard" title="My progress" lede="Mastery by topic, upcoming tasks, daily status and your full quiz history." />
      {enrollments.length === 0 ? (
        <Card className="gap-0 py-0 empty">
          <h3>Nothing to report yet</h3>
          <p>Progress appears after you enrol and take a pre-test.</p>
          <Link href="/student/courses" className={buttonVariants()}>Browse courses</Link>
        </Card>
      ) : <ProgressTabs enrollments={enrollments} />}
    </>
  );
}
