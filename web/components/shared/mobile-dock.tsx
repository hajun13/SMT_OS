import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type MobileDockProps = {
  children: ReactNode;
  className?: string;
};

export function MobileDock({ children, className }: MobileDockProps) {
  return (
    <div
      className={cn(
        "mt-3 border-t border-border bg-background/95 px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur lg:mx-auto lg:max-w-[1120px] lg:rounded-2xl lg:border lg:shadow-panel",
        className,
      )}
    >
      {children}
    </div>
  );
}
