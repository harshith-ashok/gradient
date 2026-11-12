export function Crest({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect width="40" height="40" rx="11" fill="#3a1119" />
      <path d="M8 29C14 29 15 14 21 14S28 11 32 11" stroke="#f1c9b5" strokeWidth="3" strokeLinecap="round" />
      <path d="M8 20.5h24" stroke="#fff" strokeOpacity=".28" strokeDasharray="2 3" />
      <circle cx="32" cy="11" r="2.6" fill="#fff" />
    </svg>
  );
}
