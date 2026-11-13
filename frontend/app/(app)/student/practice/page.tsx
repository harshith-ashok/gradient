import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { PracticeSearch } from "@/components/PracticeSearch";
import { serverApi, unwrap } from "@/lib/server-api";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Practice" };

export default async function PracticePage() {
  const api = await serverApi();
  const courses = unwrap(await api.GET("/api/v1/student/practice"));
  return (
    <>
      <PageHeader
        eyebrow="On-demand practice"
        title="Quiz me on…"
        lede="Pick any sub-topic from your courses for a quick quiz. Results update your mastery and, if you score below the pass mark, your plan."
      />
      {courses.length === 0 ? (
        <Card className="gap-0 py-0 empty">
          <h3>No courses yet</h3>
          <p>Enrol in a course to practise its sub-topics.</p>
          <Link href="/student/courses" className={buttonVariants()}>Browse courses</Link>
        </Card>
      ) : <PracticeSearch courses={courses} />}
    </>
  );
}
