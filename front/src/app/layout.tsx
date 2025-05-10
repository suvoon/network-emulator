import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeSwitcher } from "@/components";
import { NetworkProvider } from "@/context/NetworkContext";
const roboto = Roboto({
  weight: ['400', '500', '700'],
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Сетевой Эмулятор",
  description: "Веб-эмулятор сетевой топологии",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={roboto.className}>
      <body>
        <AuthProvider>
          <NetworkProvider>
            <main>{children}</main>
          </NetworkProvider>
        </AuthProvider>
        <ThemeSwitcher />
      </body>
    </html>
  );
}
