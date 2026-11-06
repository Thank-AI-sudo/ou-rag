
"use client";

import { useEffect, useRef, useState } from "react";
import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";

import { sendChatMessage } from "@/lib/api";
import type { ChatMessageData } from "@/types/chat";

type Theme = "light" | "dark";

const suggestions = [
    {
        title: "Học bổng",
        description: "Điều kiện và quy định",
        question: "Điều kiện xét học bổng OU là gì?",
    },
    {
        title: "Đăng ký học phần",
        description: "Thủ tục và hướng dẫn",
        question: "Cố vấn học tập có trách nhiệm gì trong việc đăng ký học phần?",
    },
    {
        title: "Quy chế sinh viên",
        description: "Quyền và nghĩa vụ",
        question: "Sinh viên có những quyền và nghĩa vụ gì?",
    },
];

export default function ChatWindow() {
    const [messages, setMessages] = useState<ChatMessageData[]>([]);
    const [theme, setTheme] = useState<Theme>("light");
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const bottomRef = useRef<HTMLDivElement>(null);
    const requestActiveRef = useRef(false);
    const sessionRef = useRef(0);

    // Đọc theme đã lưu khi frontend được mở.
    useEffect(() => {
        const saved = localStorage.getItem("ou-theme");
        const selected: Theme =
            saved === "dark" ? "dark" : "light";

        setTheme(selected);
        document.documentElement.dataset.theme = selected;
    }, []);

    // Cuộn đến câu trả lời mới.
    useEffect(() => {
        bottomRef.current?.scrollIntoView({
            behavior: "smooth",
        });
    }, [messages, loading]);

    function toggleTheme() {
        const next: Theme =
            theme === "light" ? "dark" : "light";

        setTheme(next);
        document.documentElement.dataset.theme = next;
        localStorage.setItem("ou-theme", next);
    }

    function newConversation() {
        // Không để response cũ xuất hiện trong hội thoại mới.
        sessionRef.current += 1;
        requestActiveRef.current = false;

        setMessages([]);
        setError("");
        setLoading(false);
        setSidebarOpen(false);
    }

    async function handleSend(question: string) {
        const trimmed = question.trim();

        if (!trimmed || requestActiveRef.current) return;

        const currentSession = sessionRef.current;

        requestActiveRef.current = true;
        setLoading(true);
        setError("");
        setSidebarOpen(false);

        const userMessage: ChatMessageData = {
            id: crypto.randomUUID(),
            role: "user",
            content: trimmed,
        };

        setMessages((prev) => [...prev, userMessage]);

        try {
            const result = await sendChatMessage(trimmed);

            // Bỏ qua response nếu đã tạo hội thoại mới.
            if (currentSession !== sessionRef.current) return;

            const assistantMessage: ChatMessageData = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: result.answer,
                sources: result.sources,
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (err) {
            if (currentSession !== sessionRef.current) return;

            setError(
                err instanceof Error
                    ? err.message
                    : "Đã xảy ra lỗi. Vui lòng thử lại."
            );
        } finally {
            if (currentSession === sessionRef.current) {
                requestActiveRef.current = false;
                setLoading(false);
            }
        }
    }

    return (
        <div className="app-shell">
            {sidebarOpen && (
                <button
                    className="sidebar-overlay"
                    aria-label="Đóng menu"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* SIDEBAR */}
            <aside
                className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}
            >
                <div className="sidebar-brand">
                    <div className="brand-mark">OU</div>
                    <div className="brand-identity">
                        <span className="brand-name">Open University</span>
                        <span className="brand-subtitle">
                            Academic Intelligence
                        </span>
                    </div>
                </div>

                <button
                    className="new-chat-button"
                    onClick={newConversation}
                >
                    <span className="new-chat-plus">+</span>
                    <span>Cuộc trò chuyện mới</span>
                </button>

                <div className="sidebar-section">
                    <div className="sidebar-section-title">
                        KHÁM PHÁ
                    </div>

                    {suggestions.map((item) => (
                        <button
                            key={item.title}
                            className="sidebar-topic"
                            onClick={() => handleSend(item.question)}
                            disabled={loading}
                        >
                            <span className="topic-title">
                                {item.title}
                            </span>
                            <span className="topic-description">
                                {item.description}
                            </span>
                        </button>
                    ))}
                </div>

                <div className="sidebar-footer">
                    <div className="footer-rule" />
                    <p>HO CHI MINH CITY</p>
                    <p>OPEN UNIVERSITY</p>
                    <span>OU RAG Assistant · MVP</span>
                </div>
            </aside>

            {/* MAIN CONTENT */}
            <div className="main-panel">
                <header className="topbar">
                    <div className="topbar-left">
                        <button
                            className="mobile-menu-button"
                            aria-label="Mở menu"
                            onClick={() => setSidebarOpen(true)}
                        >
                            ☰
                        </button>

                        <div className="topbar-brand">
                            <span className="topbar-ou">OU</span>
                            <span className="topbar-separator">/</span>
                            <span>ACADEMIC ASSISTANT</span>
                        </div>
                    </div>

                    <div className="topbar-actions">
                        <span className="topbar-caption">
                            UNIVERSITY KNOWLEDGE
                        </span>

                        <button
                            className="theme-toggle"
                            onClick={toggleTheme}
                            aria-label={
                                theme === "light"
                                    ? "Chuyển sang giao diện tối"
                                    : "Chuyển sang giao diện sáng"
                            }
                            title={
                                theme === "light"
                                    ? "Dark mode"
                                    : "Light mode"
                            }
                        >
                            <span aria-hidden="true">
                                {theme === "light" ? "☾" : "☀"}
                            </span>
                        </button>
                    </div>
                </header>

                <main className="conversation-area">
                    {messages.length === 0 ? (
                        <div className="welcome-screen">
                            <div className="welcome-eyebrow">
                                YOUR ACADEMIC COMPANION
                            </div>

                            <h1 className="welcome-heading">
                                Knowledge,
                                <br />
                                <em>beautifully clear.</em>
                            </h1>

                            <p className="welcome-description">
                                Khám phá thông tin học tập, quy chế
                                và học bổng tại Trường Đại học Mở
                                TP. Hồ Chí Minh.
                            </p>

                            <div className="welcome-divider" />

                            <p className="suggestion-label">
                                BẮT ĐẦU VỚI MỘT CÂU HỎI
                            </p>

                            <div className="suggestion-grid">
                                {suggestions.map((item) => (
                                    <button
                                        className="suggestion-card"
                                        key={item.title}
                                        onClick={() => handleSend(item.question)}
                                        disabled={loading}
                                    >
                                        <span className="suggestion-title">
                                            {item.title}
                                        </span>

                                        <span className="suggestion-description">
                                            {item.description}
                                        </span>

                                        <span className="suggestion-arrow">
                                            ↗
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="messages-list">
                            <div className="conversation-heading">
                                <span>CUỘC HỘI THOẠI</span>
                                <span>OU / AI</span>
                            </div>

                            {messages.map((message) => (
                                <ChatMessage
                                    key={message.id}
                                    message={message}
                                />
                            ))}

                            {loading && (
                                <div
                                    className="loading-message"
                                    role="status"
                                >
                                    <span className="loading-dot" />
                                    Đang tìm tài liệu và tổng hợp câu trả lời...
                                </div>
                            )}

                            {error && (
                                <div className="error-message" role="alert">
                                    {error}
                                </div>
                            )}

                            <div ref={bottomRef} />
                        </div>
                    )}
                </main>

                <div className="chat-bottom">
                    <ChatInput
                        onSend={handleSend}
                        loading={loading}
                    />

                    <p className="chat-disclaimer">
                        Câu trả lời được tổng hợp từ tài liệu OU.
                        Vui lòng kiểm tra nguồn trích dẫn.
                    </p>
                </div>
            </div>
        </div>
    );
}
