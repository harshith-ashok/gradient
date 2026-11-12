import type { Metadata } from "next";
import { CourseEditor } from "@/components/faculty/CourseEditor";
import { PageHeader } from "@/components/PageHeader";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Edit course" };

export default async function EditCourse({ params, searchParams }: PageProps<"/faculty/courses/[courseId]">) {
  const { courseId } = await params;
  const isNew = (await searchParams).new === "1";
  const api = await serverApi();
  const course = unwrap(await api.GET("/api/v1/faculty/courses/{course_id}", { params: { path: { course_id: courseId } } }));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "My courses", to: "/faculty" }, { label: course.code }]}
        eyebrow={isNew ? "Step 3 of 3" : "Review and edit"}
        title={course.title}
        lede="Everything the AI wrote is a draft. Edit anything, then publish when you are happy with it."
      />
      <CourseEditor initial={course} isNew={isNew} />
    </>
  );
}
