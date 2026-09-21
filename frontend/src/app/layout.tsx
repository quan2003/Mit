import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { CaptureProvider } from "@/context/CaptureContext";
import AutoCaptureToast from "@/components/AutoCaptureToast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CayMit - Phát Hiện Bệnh Cây",
  description: "Hệ thống AI giám sát và phát hiện bệnh cây Mít thông minh",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <CaptureProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
          {/* Floating toast - hiện khi auto-capture bật dù ở trang nào */}
          <AutoCaptureToast />
        </CaptureProvider>
      </body>
    </html>
  );
}
