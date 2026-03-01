"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ChevronRight, FilePenLine, IdCard, Megaphone } from "lucide-react";

import { AppFrame } from "@/components/shared/app-frame";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

type PublicEvent = {
  id: string;
  title: string;
  template: string;
  capacity: number;
};
type PublicParticipantInfo = {
  title: string;
  content: string;
};

export default function PublicEventLandingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [participantInfo, setParticipantInfo] = useState<PublicParticipantInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<PublicEvent>(`/api/public/events/${slug}`)
      .then(async (data) => {
        if (!cancelled) {
          setEvent(data);
          setError(null);
        }
        const info = await api<PublicParticipantInfo>(`/api/public/events/${data.id}/participant-info`);
        if (!cancelled) {
          setParticipantInfo(info);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  return (
    <AppFrame brand="참가자 콘솔" nav={[{ href: "/", label: "홈" }, { href: "/field", label: "현장" }]}> 
      <section className="surface-soft mb-3 rounded-2xl p-4">
        <p className="text-xs font-medium text-muted-foreground">안내·등록·티켓</p>
        <h1 className="mt-1 text-xl font-semibold">{event?.title ?? "행사 정보를 불러오는 중"}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {error ?? (event ? `정원 ${event.capacity}명 · 등록 후 바로 티켓을 확인할 수 있어요.` : "잠시만 기다려 주세요.")}
        </p>
        <Button asChild className="mt-4 h-11 w-full rounded-xl">
          <Link href={`/e/${slug}/register`}>
            등록 시작하기
            <ChevronRight className="h-4 w-4" />
          </Link>
        </Button>
      </section>

      <section className="grid gap-3">
        <Card className="surface-soft rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Megaphone className="h-4 w-4" /> {participantInfo?.title || "행사 안내"}
            </CardTitle>
          </CardHeader>
          <CardContent className="whitespace-pre-line text-sm text-muted-foreground">
            {participantInfo?.content || "장소 안내와 준비물을 확인하고 등록을 진행해 주세요."}
          </CardContent>
        </Card>

        <Card className="surface-soft rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <FilePenLine className="h-4 w-4" /> 1단계 등록
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" className="h-10 w-full rounded-xl">
              <Link href={`/e/${slug}/register`}>등록 정보 입력하기</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="surface-soft rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <IdCard className="h-4 w-4" /> 2단계 내 티켓
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" className="h-10 w-full rounded-xl">
              <Link href={`/e/${slug}/ticket`}>티켓 확인하기</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </AppFrame>
  );
}
