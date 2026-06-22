import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

// 共享组件库示例。真实项目按设计规范扩展（表单、表格、患者卡片等）。

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

export function Button({ variant = "primary", style, ...rest }: ButtonProps) {
  const base = {
    padding: "8px 16px",
    borderRadius: 6,
    border: "none",
    cursor: "pointer",
    color: "#fff",
    background: variant === "primary" ? "#1677ff" : "#8c8c8c",
  } as const;
  return <button style={{ ...base, ...style }} {...rest} />;
}

export interface CardProps extends HTMLAttributes<HTMLElement> {
  title: string;
  children: ReactNode;
}

export function Card({ title, children, style, ...rest }: CardProps) {
  return (
    <section
      style={{ border: "1px solid #eee", borderRadius: 8, padding: 16, ...style }}
      {...rest}
    >
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </section>
  );
}
