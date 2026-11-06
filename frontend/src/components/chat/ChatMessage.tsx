
import type { ChatMessageData } from "@/types/chat";
import MarkdownAnswer from "./MarkdownAnswer";
interface ChatMessageProps {
    message: ChatMessageData;
}

function isSafeUrl(url: string | null): url is string {
    if (!url) return false;

    try {
        const parsed = new URL(url);
        return (
            parsed.protocol === "http:" ||
            parsed.protocol === "https:"
        );
    } catch {
        return false;
    }
}

export default function ChatMessage({
    message,
}: ChatMessageProps) {
    const isUser = message.role === "user";
    const sources = message.sources ?? [];

    return (
        <div
            className={`message-row ${isUser ? "user-row" : "assistant-row"
                }`}
        >
            <div
                className={`message-bubble ${isUser ? "user-message" : "assistant-message"
                    }`}
            >
                <div className="message-author">
                    {isUser ? "YOU / SINH VIÊN" : "OU / ASSISTANT"}
                </div>

                <div className="message-content">
                    <MarkdownAnswer
                        content={message.content}
                        sources={message.sources ?? []}
                    />
                </div>

                {!isUser && sources.length > 0 && (
                    <div className="message-sources">
                        <div className="sources-heading">
                            <span>NGUỒN THAM KHẢO</span>
                            <span>
                                {String(sources.length).padStart(2, "0")}
                            </span>
                        </div>

                        <div className="sources-list">
                            {sources.map((source) => (
                                <div
                                    className="source-item"
                                    key={`${source.number}-${source.chunk_id}`}
                                >
                                    <span className="source-number">
                                        {String(source.number).padStart(2, "0")}
                                    </span>

                                    {isSafeUrl(source.url) ? (
                                        <a
                                            href={source.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            {source.title || "Tài liệu OU"}
                                            <span
                                                className="source-arrow"
                                                aria-hidden="true"
                                            >
                                                ↗
                                            </span>
                                        </a>
                                    ) : (
                                        <span>
                                            {source.title || "Tài liệu OU"}
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
