"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";

import { AppFrame } from "@/components/shared/app-frame";
import { MobileDock } from "@/components/shared/mobile-dock";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

type TicketInfo = {
  participant_name: string;
  ticket_status: string;
};

export default function TicketPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const slug = params.slug;

  const [code, setCode] = useState(searchParams.get("token") ?? "");
  const [title, setTitle] = useState("2단계 / 내 티켓 확인");
  const [meta, setMeta] = useState("등록 시 받은 확인 코드를 입력해 주세요.");
  const [log, setLog] = useState("확인 코드를 입력하고 조회 버튼을 누르세요.");
  const [busy, setBusy] = useState(false);

  async function load(inputCode: string) {
    try {
      if (!inputCode.trim()) throw new Error("확인 코드를 입력해 주세요.");
      setBusy(true);
      const ticket = await api<TicketInfo>(`/api/public/tickets/${encodeURIComponent(inputCode.trim())}`);
      setTitle(`${ticket.participant_name} 님의 티켓`);
      setMeta(`상태: ${ticket.ticket_status === "active" ? "입장 완료" : ticket.ticket_status}`);
      setLog("티켓을 확인했습니다.");
    } catch (error) {
      setTitle("티켓을 찾지 못했습니다");
      setMeta("확인 코드를 다시 확인해 주세요.");
      setLog(error instanceof Error ? error.message : "조회에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const t = searchParams.get("token");
    if (t) {
      setCode(t);
      void load(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppFrame
      brand="참가자 콘솔"
      nav={[
        { href: `/e/${slug}`, label: "안내" },
        { href: `/e/${slug}/register`, label: "등록" },
      ]}
    >
      <section className="surface-soft mb-3 rounded-2xl p-4">
        <p className="text-xs font-medium text-muted-foreground">안내·등록·티켓</p>
        <h1 className="mt-1 text-xl font-semibold">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{meta}</p>
      </section>

      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>확인 코드 입력</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          <Label>확인 코드</Label>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="예: xxxxxxxx" />
          <p className="text-sm text-muted-foreground">{log}</p>
        </CardContent>
      </Card>

      <Card className="mt-3 rounded-2xl border-dashed bg-secondary/70">
        <CardContent className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
          <CheckCircle2 className="h-4 w-4" />
          현장 입장 시 이 화면을 스태프에게 보여주세요.
        </CardContent>
      </Card>

      <MobileDock>
        <div className="mx-auto max-w-[980px]">
          <Button className="h-12 w-full rounded-xl text-base" onClick={() => void load(code)} disabled={busy}>
            내 티켓 조회
          </Button>
        </div>
      </MobileDock>
    </AppFrame>
  );
}
