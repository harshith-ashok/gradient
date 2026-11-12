export const TABS = ["summary", "cards", "help"] as const;
export type Tab = (typeof TABS)[number];

export function parseTab(v: string | string[] | undefined): Tab {
  return TABS.find((t) => t === v) ?? "summary";
}
