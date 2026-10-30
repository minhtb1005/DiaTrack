import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "DiaTrack — Cùng bạn chăm sóc đường huyết",
  description: "Theo dõi đường huyết, lịch thuốc đã duyệt và chuẩn bị tái khám, trong một không gian dễ sử dụng.",
};

const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('med-theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}if(t==='dark'){document.documentElement.classList.add('dark');}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen text-slate-900 dark:text-slate-100">
        <AuthProvider>
          <Header />
          <main id="main-content" className="app-main" tabIndex={-1}>{children}</main>
          <footer className="site-footer">
            <strong>DiaTrack · Cùng bạn mỗi ngày</strong><span>Hỗ trợ theo dõi, không thay thế chỉ định bác sĩ.</span>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
