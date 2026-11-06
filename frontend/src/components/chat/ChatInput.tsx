
"use client";

import {
    useState,
    type FormEvent,
    type KeyboardEvent,
} from "react";

interface ChatInputProps {
    onSend: (question: string) => void;
    loading: boolean;
}

export default function ChatInput({
    onSend,
    loading,
}: ChatInputProps) {
    const [question, setQuestion] = useState("");

    function send() {
        const value = question.trim();
        if (!value || loading) return;

        onSend(value);
        setQuestion("");
    }

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        send();
    }

    function handleKeyDown(
        e: KeyboardEvent<HTMLTextAreaElement>
    ) {
        if (
            e.key === "Enter" &&
            !e.shiftKey &&
            !e.nativeEvent.isComposing
        ) {
            e.preventDefault();
            send();
        }
    }

    return (
        <form
            className="chat-input-form"
            onSubmit={handleSubmit}
        >
            <div className="chat-input-wrapper">
                <textarea
                    className="chat-input"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Hỏi điều bạn muốn biết về OU..."
                    aria-label="Nhập câu hỏi"
                    rows={2}
                    disabled={loading}
                />

                <button
                    className="send-button"
                    type="submit"
                    disabled={loading || !question.trim()}
                    aria-label="Gửi câu hỏi"
                    title="Gửi câu hỏi"
                >
                    <span aria-hidden="true">↗</span>
                </button>
            </div>

            <div className="input-hint">
                <span>ENTER ĐỂ GỬI</span>
                <span>SHIFT + ENTER ĐỂ XUỐNG DÒNG</span>
            </div>
        </form>
    );
}
