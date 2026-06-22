export const metadata = { title: "AI云医院 · 医共体监管驾驶舱" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0f1729" }}>
        {children}
      </body>
    </html>
  );
}
