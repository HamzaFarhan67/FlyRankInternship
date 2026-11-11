import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Task API",
  description: "SQLite task CRUD API"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
