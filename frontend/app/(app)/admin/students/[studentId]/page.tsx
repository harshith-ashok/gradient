import type { Metadata } from "next";
import { EnrollmentProgress } from "@/components/EnrollmentProgress";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";
import { Card } from "@/components/ui/card";

type Props = PageProps<"/admin/students/[studentId]">;

async function load(studentId: string) {
  const api = await serverApi();
  return unwrap(await api.GET("/api/v1/admin/students/{student_id}", { params: { path: { student_id: studentId } } }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: (await load((await params).studentId)).student.name };
}

export default async function StudentDetailPage({ params }: Props) {
  const { student, enrollments } = await load((await params).studentId);
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Student progress", to: "/admin" }, { label: student.name }]}
        eyebrow="Student"
        title={student.name}
        lede={[student.student_id, student.program, student.year, student.email].filter(Boolean).join(" · ")}
      />
      {!enrollments.length && (
        <Card className="gap-0 py-0 empty"><h3>No enrolments</h3><p>This student has not enrolled in a course yet.</p></Card>
      )}
      <div className="space-y-10">
        {enrollments.map((e) => <EnrollmentProgress key={e.enrollment_id} e={e} readonly />)}
      </div>
    </>
  );
}
