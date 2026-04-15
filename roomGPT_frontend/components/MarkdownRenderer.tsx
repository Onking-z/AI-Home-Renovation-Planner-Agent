"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

interface MarkdownRendererProps {
  content: string;
}

function normalizeContent(rawContent: string): string {
  const normalizedInput = rawContent.replace(/\r\n/g, "\n");

  // Some model replies are accidentally wrapped with fenced code blocks.
  // Unwrap the outer fence so markdown can render normally.
  const wrappedFenceMatch = normalizedInput.match(/^(?:```|~~~)[a-zA-Z0-9_-]*\n([\s\S]*?)\n(?:```|~~~)\s*$/);
  let unwrapped = wrappedFenceMatch ? wrappedFenceMatch[1] : normalizedInput;

  // Remove accidental HTML code wrappers emitted by some model responses.
  unwrapped = unwrapped.replace(/<\/?pre[^>]*>/gi, "");
  unwrapped = unwrapped.replace(/<\/?code[^>]*>/gi, "");

  // Remove leaked fence lines (including malformed/odd fences) to avoid turning
  // regular markdown sections into full code blocks.
  unwrapped = unwrapped.replace(/^\s*(?:```|~~~)[a-zA-Z0-9_-]*\s*$/gm, "");
  unwrapped = unwrapped.replace(/^\s*`{3,}[^\n]*$/gm, "");
  unwrapped = unwrapped.replace(/^\s*~{3,}[^\n]*$/gm, "");

  const rawLines = unwrapped.split("\n");

  // If most non-empty lines are indented with 4+ spaces and look like prose/markdown,
  // it is usually a malformed model response accidentally rendered as indented code.
  const nonEmpty = rawLines.filter((line) => line.trim().length > 0);
  const heavilyIndented = nonEmpty.filter((line) => /^\s{4,}/.test(line));
  const likelyCode = nonEmpty.filter((line) => /^\s{4,}(const\s+|let\s+|var\s+|def\s+|class\s+|function\s+|if\s+|for\s+|while\s+|return\s+|import\s+|from\s+|\{|\}|\[|\]|\(|\)|<\/?[a-z])/i.test(line));
  const shouldGlobalDeindent =
    nonEmpty.length >= 6 &&
    heavilyIndented.length / nonEmpty.length >= 0.7 &&
    likelyCode.length / nonEmpty.length <= 0.25;

  const adjustedLines = shouldGlobalDeindent
    ? rawLines.map((line) => line.replace(/^\s{4}/, ""))
    : rawLines;

  const expanded: string[] = [];

  adjustedLines.forEach((line) => {
    const trimmed = line.trim();
    if (trimmed.includes("||") && trimmed.includes("|") && trimmed.split("|").length >= 6) {
      const parts = trimmed
        .split("||")
        .map((part) => part.trim())
        .filter(Boolean);
      if (parts.length > 1) {
        parts.forEach((part) => expanded.push(part.startsWith("|") ? part : `| ${part}`));
        return;
      }
    }
    // Drop standalone fence lines that occasionally leak into non-code responses.
    if (/^(?:```|~~~)[a-zA-Z0-9_-]*\s*$/.test(trimmed)) {
      return;
    }

    // If a markdown/prose line is accidentally indented by 4+ spaces,
    // de-indent it so it won't be treated as an indented code block.
    if (
      /^\s{4,}/.test(line) &&
      !/^\s{4,}(const\s+|let\s+|var\s+|def\s+|class\s+|function\s+|if\s+|for\s+|while\s+|return\s+|import\s+|from\s+|\{|\}|\[|\]|\(|\)|<\/?[a-z])/i.test(line)
    ) {
      expanded.push(line.replace(/^\s{4}/, ""));
      return;
    }

    expanded.push(line);
  });

  return expanded.join("\n");
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const normalized = normalizeContent(content || "");

  return (
    <div className="markdown-content min-w-0 text-sm [overflow-wrap:anywhere] sm:text-base">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          h1: ({ children }) => <h1 className="mb-3 mt-2 text-2xl font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-3 mt-2 text-xl font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-2 text-lg font-semibold">{children}</h3>,
          p: ({ children }) => <p className="mb-3 break-words [overflow-wrap:anywhere] leading-7">{children}</p>,
          ul: ({ children }) => <ul className="mb-3 list-disc pl-5 break-words [overflow-wrap:anywhere] leading-7">{children}</ul>,
          ol: ({ children }) => (
            <ol className="mb-3 list-decimal pl-5 break-words [overflow-wrap:anywhere] leading-7">{children}</ol>
          ),
          li: ({ children }) => <li className="break-words [overflow-wrap:anywhere]">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mb-3 break-words [overflow-wrap:anywhere] border-l-4 border-[#C8B28B] bg-[#FAF6EF] px-4 py-2 italic text-[#6B6459]">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="mb-3 overflow-x-auto rounded-xl border border-[#8B6F47]/15">
              <table className="min-w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-[#F7F1E7] text-[#2D2D2D]">{children}</thead>,
          th: ({ children }) => (
            <th className="border border-[#8B6F47]/15 px-3 py-2 text-left font-semibold">{children}</th>
          ),
          tbody: ({ children }) => <tbody className="bg-white/70">{children}</tbody>,
          td: ({ children }) => <td className="border border-[#8B6F47]/15 px-3 py-2 align-top">{children}</td>,
          pre: ({ children }) => (
            <pre className="mb-3 overflow-x-auto rounded-xl bg-[#2A241F] px-4 py-3 text-sm text-[#F6F1E8]">{children}</pre>
          ),
          code: ({ inline, children }) =>
            inline ? (
              <code className="rounded bg-[#F3EEE5] px-1.5 py-0.5 text-[0.95em] text-[#6C5533]">{children}</code>
            ) : (
              <code>{children}</code>
            ),
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

