import Link from "next/link";
import type { ReactNode } from "react";

import { BRAND_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  note?: string;
};

type SectionLink = {
  href: string;
  label: string;
};

type WorkspaceShellProps = {
  title: string;
  subtitle: string;
  navItems: NavItem[];
  sectionLinks?: SectionLink[];
  children: ReactNode;
  className?: string;
};

export function WorkspaceShell({ title, subtitle, navItems, sectionLinks = [], children, className }: WorkspaceShellProps) {
  return (
    <main className={cn("app-shell", className)}>
      <header className="surface-soft mb-4 rounded-2xl p-3">
        <Link href="/" className="inline-flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-white text-xs font-semibold">D</span>
          <span className="text-sm font-semibold">{BRAND_NAME}</span>
        </Link>

        <div className="mt-3">
          <p className="text-base font-semibold">{title}</p>
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        </div>

        <nav className="mt-3 grid gap-2 sm:grid-cols-3">
          {navItems.map((item) => (
            <Link
              key={`${item.href}-${item.label}`}
              href={item.href}
              className="rounded-xl border border-border bg-white px-3 py-2 text-left"
            >
              <p className="text-sm font-medium">{item.label}</p>
            </Link>
          ))}
        </nav>

        {sectionLinks.length > 0 ? (
          <nav className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
            {sectionLinks.map((item) => (
              <a
                key={`${item.href}-${item.label}`}
                href={item.href}
                className="rounded-full border border-border bg-white px-3 py-1 text-xs text-muted-foreground"
              >
                {item.label}
              </a>
            ))}
          </nav>
        ) : null}
      </header>

      <section className="space-y-3">{children}</section>
    </main>
  );
}
