import Link from "next/link";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type NavItem = { href: string; label: string };

type AppFrameProps = {
  brand: string;
  children: ReactNode;
  nav?: NavItem[];
  className?: string;
};

export function AppFrame({ brand, children, nav = [], className }: AppFrameProps) {
  return (
    <main className={cn("app-shell", className)}>
      <header className="surface-soft mb-4 rounded-2xl px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="inline-flex min-w-0 items-center gap-2.5">
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border bg-white text-xs font-bold text-foreground">
              D
            </span>
            <span className="truncate text-sm font-semibold md:text-base">{brand}</span>
          </Link>
        </div>

        {nav.length > 0 ? (
          <nav className="mt-3 flex flex-wrap gap-2">
            {nav.map((item) => (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className="rounded-full border border-border bg-white px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:text-foreground"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        ) : null}
      </header>
      {children}
    </main>
  );
}
