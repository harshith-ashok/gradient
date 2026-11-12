import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { UploadForm } from "@/components/faculty/UploadForm";

export const metadata: Metadata = { title: "New course" };

export default function NewCourse() {
  return (
    <>
      <PageHeader
        crumbs={[{ label: "My courses", to: "/faculty" }, { label: "New course" }]}
        eyebrow="Step 1 of 3"
        title="Upload a syllabus"
        lede="The AI reads it and proposes the course topics. Scanned and handwritten pages are read with the vision model."
      />
      <UploadForm />
    </>
  );
}
