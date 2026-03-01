"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AppFrame } from "@/components/shared/app-frame";
import { MobileDock } from "@/components/shared/mobile-dock";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

type PublicEvent = {
  id: string;
  title: string;
  template: string;
  capacity: number;
};

type FormField = {
  key: string;
  label: string;
  required: boolean;
};

export default function RegisterPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const [event, setEvent] = useState<PublicEvent | null>(null);
  const [fields, setFields] = useState<FormField[]>([]);

  const [applicant, setApplicant] = useState("");
  const [participant, setParticipant] = useState("");
  const [participantRole, setParticipantRole] = useState("");
  const [phone, setPhone] = useState("");
  const [church, setChurch] = useState("");
  const [grade, setGrade] = useState("");
  const [dynamic, setDynamic] = useState<Record<string, string>>({});

  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("정보를 입력하고 아래 버튼을 눌러 등록하세요.");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const found = await api<PublicEvent>(`/api/public/events/${slug}`);
        if (cancelled) return;
        setEvent(found);
        const form = await api<FormField[]>(`/api/public/events/${found.id}/registration-form`);
        if (!cancelled) setFields(form);
      } catch (error) {
        if (!cancelled) setLog(error instanceof Error ? error.message : "행사 정보를 불러오지 못했습니다.");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  const extraFields = useMemo(() => fields.filter((f) => !["grade", "church_or_school"].includes(f.key)), [fields]);

  async function submit() {
    try {
      if (!event) throw new Error("행사 정보를 불러오는 중입니다.");
      if (!applicant.trim() || !participant.trim()) throw new Error("신청자와 참가자 이름을 입력해 주세요.");
      if (!participantRole) throw new Error("참가자 구분을 선택해 주세요.");
      if (["teacher", "evangelist", "pastor"].includes(participantRole) && !phone.trim()) {
        throw new Error("지도교사/전도사/목사는 전화번호를 입력해 주세요.");
      }

      setBusy(true);
      const answers: Record<string, string> = {
        participant_role: participantRole,
        phone: phone.trim(),
        grade,
        church_or_school: church,
        ...dynamic,
      };

      const result = await api<{ ticket: { token: string } }>("/api/participants/register", {
        method: "POST",
        json: {
          event_id: event.id,
          applicant_name: applicant.trim(),
          participant_name: participant.trim(),
          kind: "individual",
          church_or_school: church,
          grade,
          answers,
        },
      });

      router.push(`/e/${slug}/ticket?token=${encodeURIComponent(result.ticket.token)}`);
    } catch (error) {
      setLog(error instanceof Error ? error.message : "등록에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppFrame
      brand="참가자 콘솔"
      nav={[
        { href: `/e/${slug}`, label: "안내" },
        { href: `/e/${slug}/ticket`, label: "내 티켓" },
      ]}
    >
      <section className="surface-soft mb-3 rounded-2xl p-4">
        <p className="text-xs font-medium text-muted-foreground">안내·등록·티켓</p>
        <h1 className="mt-1 text-xl font-semibold">{event ? `${event.title} 등록` : "행사 정보를 불러오는 중"}</h1>
        <p className="mt-2 text-sm text-muted-foreground">등록이 끝나면 자동으로 내 티켓 화면으로 이동합니다.</p>
      </section>

      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>기본 정보</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <Field label="신청자 이름" value={applicant} setValue={setApplicant} />
          <Field label="참가자 이름" value={participant} setValue={setParticipant} />
          <div className="grid gap-2">
            <Label>참가자 구분</Label>
            <Select value={participantRole} onValueChange={setParticipantRole}>
              <SelectTrigger>
                <SelectValue placeholder="선택해 주세요" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="student">학생</SelectItem>
                <SelectItem value="teacher">지도교사</SelectItem>
                <SelectItem value="evangelist">전도사</SelectItem>
                <SelectItem value="pastor">목사</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Field label="소속(교회/학교)" value={church} setValue={setChurch} />
          <Field label="학년" value={grade} setValue={setGrade} />
          <Field label="전화번호" value={phone} setValue={setPhone} />
        </CardContent>
      </Card>

      {extraFields.length > 0 ? (
        <Card className="surface-soft mt-3 rounded-2xl">
          <CardHeader>
            <CardTitle>추가 정보</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {extraFields.map((field) => (
              <div key={field.key} className="grid gap-2">
                <Label>
                  {field.label}
                  {field.required ? " *" : ""}
                </Label>
                <Input
                  value={dynamic[field.key] ?? ""}
                  onChange={(e) => setDynamic((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  placeholder={field.label}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card className="mt-3 rounded-2xl border-dashed bg-secondary/70">
        <CardContent className="py-4 text-sm text-muted-foreground">{log}</CardContent>
      </Card>

      <MobileDock>
        <div className="mx-auto max-w-[980px]">
          <Button className="h-12 w-full rounded-xl text-base" onClick={submit} disabled={busy}>
            등록 완료하고 내 티켓 보기
          </Button>
        </div>
      </MobileDock>
    </AppFrame>
  );
}

function Field({ label, value, setValue }: { label: string; value: string; setValue: (v: string) => void }) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => setValue(e.target.value)} />
    </div>
  );
}
