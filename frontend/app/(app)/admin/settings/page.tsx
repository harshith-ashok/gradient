import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { SettingsForm } from "@/components/SettingsForm";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Quiz pass mark" };

export default async function SettingsPage() {
  const api = await serverApi();
  const settings = unwrap(await api.GET("/api/v1/admin/settings"));
  return (
    <>
      <PageHeader
        crumbs={[{ label: "Student progress", to: "/admin" }, { label: "Pass mark" }]}
        eyebrow="Management"
        title="Quiz pass mark"
        lede="The pass mark decides when a quiz result is good enough. A lower score reschedules the topic, adds remediation material and recalculates the plan."
      />
      <SettingsForm initial={settings} />
    </>
  );
}
