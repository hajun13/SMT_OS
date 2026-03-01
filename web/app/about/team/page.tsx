"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/shared/app-frame";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

type OrgChartMember = {
  role: string;
  name: string;
  photo_url: string | null;
};

type OrgChartTeam = {
  team: string;
  members: OrgChartMember[];
};

export default function TeamPage() {
  const [orgChart, setOrgChart] = useState<OrgChartTeam[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await api<OrgChartTeam[]>("/api/public/org-chart");
        setOrgChart(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "조직도를 불러오지 못했습니다.");
      }
    })();
  }, []);

  return (
    <AppFrame brand="운영진" nav={[{ href: "/", label: "홈" }, { href: "/login", label: "로그인" }]}>
      <section className="mb-3 rounded-2xl border border-border bg-white px-4 py-5">
        <h1 className="text-xl font-semibold">운영진</h1>
        <p className="mt-2 text-sm text-muted-foreground">서중한합회 학생 사역팀 운영진</p>
      </section>

      {error ? (
        <Card className="surface-soft rounded-2xl">
          <CardContent className="py-4 text-sm text-muted-foreground">{error}</CardContent>
        </Card>
      ) : null}

      <section className="grid gap-3">
        {orgChart.map((team) => (
          <Card key={team.team} className="surface-soft rounded-2xl">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{team.team}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {team.members.map((member) => (
                <div key={`${team.team}-${member.role}-${member.name}`} className="flex items-center gap-2 rounded-xl border border-border bg-white px-3 py-2">
                  {member.photo_url ? (
                    <img
                      src={member.photo_url}
                      alt={`${member.name} 프로필`}
                      className="h-9 w-9 rounded-full border border-border object-cover"
                    />
                  ) : (
                    <div className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-secondary text-[10px] text-muted-foreground">
                      사진
                    </div>
                  )}
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{member.role}</span> · {member.name}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="mt-4">
        <Link href="/" className="text-sm text-muted-foreground underline underline-offset-2">
          홈으로 돌아가기
        </Link>
      </section>
    </AppFrame>
  );
}
