import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AVAS - AI Valuation Automation System',
  description: 'Automated property valuation report generation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
