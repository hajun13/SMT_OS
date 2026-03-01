 "use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ChevronRight, ClipboardList, TicketCheck, UserRound, Users } from "lucide-react";

import { AppFrame } from "@/components/shared/app-frame";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchMe, getToken, type SessionUser } from "@/lib/auth";
import { BRAND_KO, BRAND_NAME } from "@/lib/brand";

export default function HomePage() {
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    void (async () => {
      const token = getToken();
      if (!token) return;
      try {
        const me = await fetchMe();
        setUser(me);
      } catch {
        setUser(null);
      }
    })();
  }, []);

  const menus = useMemo(() => {
    if (!user) {
      return [
        {
          href: "/e/spring-festival-2026",
          title: "참가자 콘솔",
          desc: "학생들이 바로 신청하고 티켓을 확인할 수 있습니다.",
          icon: UserRound,
        },
      ];
    }

    if (user.account_type === "leader") {
      return [
        {
          href: "/leader",
          title: "지도교사 콘솔",
          desc: "교회 학생 등록, 납부, 환불 요청을 관리합니다.",
          icon: Users,
        },
      ];
    }

    if (user.account_type === "ministry" && user.status === "approved") {
      return [
        {
          href: "/admin",
          title: "관리자 콘솔",
          desc: "준비, 운영, 리포트를 한 화면에서 관리합니다.",
          icon: ClipboardList,
        },
        {
          href: "/field",
          title: "현장 콘솔",
          desc: "체크인과 현장 등록을 빠르게 처리합니다.",
          icon: TicketCheck,
        },
        {
          href: "/leader",
          title: "지도교사 콘솔",
          desc: "지도교사·전도사·목사 등록/납부/환불 확인",
          icon: Users,
        },
      ];
    }

    return [
      {
        href: "/e/spring-festival-2026",
        title: "참가자 콘솔",
        desc: "승인 대기 중에는 참가자 화면만 사용할 수 있습니다.",
        icon: UserRound,
      },
    ];
  }, [user]);

  const nav = user
    ? [{ href: "/login", label: "다시 로그인" }]
    : [{ href: "/login", label: "로그인" }, { href: "/signup", label: "회원가입" }];

  return (
    <AppFrame brand={BRAND_NAME} nav={nav}>
      <section className="mb-3 rounded-2xl border border-border bg-white px-4 py-5">
        <p className="text-xs font-medium text-muted-foreground">{BRAND_KO}</p>
        <h1 className="mt-1 text-xl font-semibold">DoDream 운영 콘솔</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {!user
            ? "비회원은 참가자 콘솔에서 바로 신청할 수 있습니다."
            : "로그인 권한에 맞는 콘솔만 표시됩니다."}
        </p>
      </section>

      <section className="grid gap-3">
        {menus.map((menu) => {
          const Icon = menu.icon;
          return (
            <Card key={menu.href} className="surface-soft rounded-2xl">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
                    <Icon className="h-4 w-4" />
                  </span>
                  {menu.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-muted-foreground">{menu.desc}</p>
                <Button asChild className="h-11 w-full justify-between rounded-xl">
                  <Link href={menu.href}>
                    바로 열기
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {!user ? (
        <section className="mt-4 space-y-3">
          <Card className="surface-soft rounded-2xl">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">운영진</CardTitle>
            </CardHeader>
            <CardContent>
              <Button asChild variant="secondary" className="h-11 w-full rounded-xl">
                <Link href="/about/team">조직도 열기</Link>
              </Button>
            </CardContent>
          </Card>
        </section>
      ) : null}
    </AppFrame>
  );
}
