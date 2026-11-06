
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "OU Academic Assistant",
    description:
        "Trợ lý AI tra cứu quy chế và thông tin sinh viên OU",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="vi" suppressHydrationWarning>
            <body>{children}</body>
        </html>
    );
}
