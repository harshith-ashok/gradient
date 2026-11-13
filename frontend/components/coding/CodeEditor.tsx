"use client";

import { cpp } from "@codemirror/lang-cpp";
import { python } from "@codemirror/lang-python";
import CodeMirror from "@uiw/react-codemirror";

export const LANG_LABEL = { c: "C", cpp: "C++", python: "Python" } as const;
export type Lang = keyof typeof LANG_LABEL;

/** A real code editor: syntax colours, indentation, brackets. Loaded lazily by `Editor` below. */
export default function CodeEditor({
  value, onChange, language, height = "380px", label,
}: { value: string; onChange: (v: string) => void; language: Lang; height?: string; label: string }) {
  return (
    <div className="overflow-hidden rounded-md border border-border text-[13.5px]" role="group" aria-label={label}>
      <CodeMirror
        value={value} height={height} onChange={onChange} theme="light"
        extensions={[language === "python" ? python() : cpp()]}
        basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true, indentOnInput: true, tabSize: 4 }}
      />
    </div>
  );
}
