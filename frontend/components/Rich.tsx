import type { ComponentProps, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";

/**
 * Text written by faculty or the AI: Markdown with fenced code blocks (```c ... ```), `inline code`,
 * **bold** and lists. Raw HTML is never rendered, images are dropped, and links only keep http(s) and
 * mailto, so the text cannot inject markup or scripts.
 *
 * `inline` is for places that sit inside a button or a sentence (quiz options): paragraphs become spans,
 * and code blocks stay on their own lines without block elements that a button may not contain.
 */

/** Models and spreadsheets sometimes glue a fence onto a sentence. A fence must start its own line. */
export function fixFences(text: string): string {
  return text.replace(/([^\n`])(```)/g, "$1\n$2").replace(/(```[^\n`]*)\n?(?<=```)(?=[^\n`])/g, "$1");
}

const SAFE_URL = /^(https?:|mailto:|#|\/)/i;

function codeBlock({ children, className, ...rest }: ComponentProps<"code">) {
  return <code className={className} {...rest}>{children}</code>;
}

const blockComponents = { code: codeBlock };
const inlineComponents = {
  code: codeBlock,
  p: ({ children }: { children?: ReactNode }) => <span className="block">{children}</span>,
  pre: ({ children }: { children?: ReactNode }) => <span className="block whitespace-pre">{children}</span>,
  ul: ({ children }: { children?: ReactNode }) => <span className="block">{children}</span>,
  ol: ({ children }: { children?: ReactNode }) => <span className="block">{children}</span>,
  li: ({ children }: { children?: ReactNode }) => <span className="block">• {children}</span>,
};

export function Rich({ children, inline = false, className = "" }: { children: string; inline?: boolean; className?: string }) {
  const Wrapper = inline ? "span" : "div";
  return (
    <Wrapper className={`rich ${inline ? "rich-inline" : ""} ${className}`}>
      <ReactMarkdown
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        disallowedElements={["img"]}
        urlTransform={(url) => (SAFE_URL.test(url) ? url : "")}
        components={inline ? inlineComponents : blockComponents}
      >
        {fixFences(children)}
      </ReactMarkdown>
    </Wrapper>
  );
}
