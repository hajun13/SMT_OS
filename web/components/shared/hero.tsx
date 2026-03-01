import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type HeroMetric = { label: string; value: string };

type HeroProps = {
  eyebrow: string;
  title: string;
  description: string;
  metrics?: HeroMetric[];
  actions?: ReactNode;
};

export function Hero({ eyebrow, title, description, metrics = [], actions }: HeroProps) {
  return (
    <Card className="mb-4 border-border bg-card p-5 md:p-6">
      <Badge variant="secondary" className="rounded px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
        {eyebrow}
      </Badge>
      <h1 className="mt-3 text-[26px] font-semibold leading-tight md:text-[34px]">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground md:text-base">{description}</p>

      {metrics.length > 0 ? (
        <dl className="mt-4 grid gap-2 sm:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-md border border-border bg-background px-3 py-2.5">
              <dt className="text-[11px] font-medium text-muted-foreground">{metric.label}</dt>
              <dd className="mt-1 text-base font-semibold md:text-lg">{metric.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
    </Card>
  );
}
