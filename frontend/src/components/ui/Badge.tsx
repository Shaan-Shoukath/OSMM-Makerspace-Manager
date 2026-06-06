import type { PropsWithChildren } from "react";

type BadgeTone = "success" | "warn" | "danger" | "neutral";

type BadgeProps = PropsWithChildren<{
  tone: BadgeTone;
}>;

const toneClasses: Record<BadgeTone, string> = {
  success: "bg-success/10 text-success",
  warn: "bg-tinker text-ink",
  danger: "bg-danger/10 text-danger",
  neutral: "bg-surface text-ink",
};

export function Badge({ tone, children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
