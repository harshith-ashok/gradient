const COLORS: Record<string, string> = { ok: "var(--success)", warn: "var(--warning)", bad: "var(--destructive)" };

export function RingProgress({
  value, size = 64, stroke = 6, tone = "",
}: { value: number; size?: number; stroke?: number; tone?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, value));
  return (
    <span className="relative inline-flex flex-none items-center justify-center" style={{ width: size, height: size }} role="img" aria-label={`${value}%`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#ebe6d8" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={COLORS[tone] ?? "var(--foreground)"}
          strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)}
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.22,0.8,0.24,1)" }}
        />
      </svg>
      <b className="absolute font-semibold tabular-nums" style={{ fontSize: size * 0.28 }}>{Math.round(value)}%</b>
    </span>
  );
}
