export const metadata = { title: "AI云医院 · 居民健康门户" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f5f7fa" }}>
        {children}
      </body>
    </html>
  );
}
