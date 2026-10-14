import type { Metadata } from "next";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";
import "./companion.css";

export const metadata: Metadata = {
  title: "MindPulse | A little more in tune",
  description: "Private mood check-ins and mental health screening for everyday self-awareness.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />
        <main>{children}</main>
      </body>
    </html>
  );
}