import { masteryTone } from "@/lib/format";

export function MeterBar({
  value, threshold, thin = false, label = "Progress",
}: { value: number; threshold?: number | null; thin?: boolean; label?: string }) {
  const tone = threshold == null ? "" : masteryTone(value, threshold);
  return (
    <div className={`meter ${tone} ${thin ? "thin" : ""}`} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <i style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      {threshold != null && <span className="mark" style={{ left: `${threshold}%` }} title={`Pass mark ${threshold}%`} />}
    </div>
  );
}
