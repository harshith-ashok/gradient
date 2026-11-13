import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { StudentProgress } from "@/components/StudentProgress";

export const metadata: Metadata = { title: "Student progress" };

export default async function FacultyStudents({ searchParams }: PageProps<"/faculty/students">) {
  return (
    <>
      <PageHeader
        eyebrow="Faculty portal"
        title="Student progress"
        lede="How the students enrolled in your courses are doing: overall progress, per-topic mastery and upcoming tasks."
      />
      <StudentProgress scope="faculty" sp={await searchParams} />
    </>
  );
}
