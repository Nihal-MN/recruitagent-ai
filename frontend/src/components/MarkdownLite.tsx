"use client";

import type { ReactNode } from "react";

/**
 * A deliberately small, SAFE markdown subset renderer for agent answers.
 * Supports: paragraphs, bullet lists ("- " / "• "), numbered lists ("1. "),
 * headings ("#".."###"), **bold** and `code`. It builds React elements —
 * never dangerouslySetInnerHTML, never raw HTML from model output.
 */

type Block =
  | { type: "p"; content: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "h"; level: number; content: string };

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const lines = text.split("\n");
  let paragraph: string[] = [];
  let list: { type: "ul" | "ol"; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "p", content: paragraph.join(" ") });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list) {
      blocks.push(list);
      list = null;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const heading = line.match(/^(#{1,3})\s+(.*)$/);

    if (/^\s*$/.test(line)) {
      flushParagraph();
      flushList();
      continue;
    }
    if (bullet) {
      flushParagraph();
      if (!list || list.type !== "ul") {
        flushList();
        list = { type: "ul", items: [] };
      }
      list.items.push(bullet[1]);
      continue;
    }
    if (numbered) {
      flushParagraph();
      if (!list || list.type !== "ol") {
        flushList();
        list = { type: "ol", items: [] };
      }
      list.items.push(numbered[1]);
      continue;
    }
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h", level: heading[1].length, content: heading[2] });
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();
  return blocks;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${index++}`;
    if (token.startsWith("**")) {
      nodes.push(
        <strong key={key} className="font-semibold text-slate-900">
          {token.slice(2, -2)}
        </strong>,
      );
    } else {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export function MarkdownLite({ text, className = "" }: { text: string; className?: string }) {
  const blocks = parseBlocks(text);
  return (
    <div className={`chat-md text-sm text-slate-700 ${className}`}>
      {blocks.map((block, index) => {
        const key = `b-${index}`;
        if (block.type === "ul") {
          return (
            <ul key={key} className="my-1 list-disc space-y-0.5 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{renderInline(item, `${key}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "ol") {
          return (
            <ol key={key} className="my-1 list-decimal space-y-0.5 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{renderInline(item, `${key}-${itemIndex}`)}</li>
              ))}
            </ol>
          );
        }
        if (block.type === "h") {
          const size = block.level === 1 ? "text-base" : "text-sm";
          return (
            <p key={key} className={`mt-2 mb-1 font-semibold text-slate-900 ${size}`}>
              {renderInline(block.content, key)}
            </p>
          );
        }
        return <p key={key}>{renderInline(block.content, key)}</p>;
      })}
    </div>
  );
}
