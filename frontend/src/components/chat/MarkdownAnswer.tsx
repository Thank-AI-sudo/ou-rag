"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatSource } from "@/types/chat";

type MarkdownAnswerProps = {
    content: string;
    sources?: ChatSource[];
};

export default function MarkdownAnswer({
    content,
    sources = [],
}: MarkdownAnswerProps) {
    const sourceMap = new Map(
        sources.map((source) => [source.number, source])
    );

    // Chuyển [1], [2] thành Markdown links
    const markdown = content.replace(
        /\[(\d+)\](?!\()/g,
        (match, number) => {
            const source = sourceMap.get(Number(number));

            if (!source?.url) return match;

            try {
                const url = new URL(source.url);

                if (
                    url.protocol !== "https:" &&
                    url.protocol !== "http:"
                ) {
                    return match;
                }

                return `[${number}](${url.toString()})`;
            } catch {
                return match;
            }
        }
    );

    return (
        <div className="markdown-answer">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ href, children }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="citation-link"
                        >
                            {children}
                        </a>
                    ),
                }}
            >
                {markdown}
            </ReactMarkdown>
        </div>
    );
}
