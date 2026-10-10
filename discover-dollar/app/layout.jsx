import "./globals.css";

export const metadata = {
  title: "ShiftSwap | Clinic Operations",
  description: "Staff shift swapping for clinic teams",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
