import "./globals.css";

export const metadata = {
  title: "Hackathon Starter",
  description: "Next.js, FastAPI, and MongoDB starter application",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
