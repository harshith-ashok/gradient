import type { Metadata } from "next";
import { Public_Sans, Spectral } from "next/font/google";
import "./globals.css";

const sans = Public_Sans({ variable: "--font-public-sans", subsets: ["latin"] });
const serif = Spectral({
  variable: "--font-spectral",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: { default: "Gradient", template: "%s · Gradient" },
  description: "An adaptive learning portal that turns a syllabus into a personal study path.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
