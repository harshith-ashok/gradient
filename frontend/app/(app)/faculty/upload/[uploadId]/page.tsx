import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { UploadFlow } from "@/components/faculty/UploadFlow";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Analysing syllabus" };

export default async function UploadPage({ params }: PageProps<"/faculty/upload/[uploadId]">) {
  const { uploadId } = await params;
  const api = await serverApi();
  const upload = unwrap(await api.GET("/api/v1/faculty/syllabus/{upload_id}", { params: { path: { upload_id: uploadId } } }));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "My courses", to: "/faculty" }, { label: "New course" }]}
        eyebrow="Step 2 of 3"
        title="Choose the course topics"
        lede="Untick anything that is not part of this course. Sub-topics are drafted for the ones you keep."
      />
      <UploadFlow initial={upload} />
    </>
  );
}
