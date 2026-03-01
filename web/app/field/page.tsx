"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, UserCheck2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { WorkspaceShell } from "@/components/shared/workspace-shell";
import { MobileDock } from "@/components/shared/mobile-dock";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, roleHeader, type ParticipantRow } from "@/lib/api";
import { canAccessField, fetchMe, getToken, logout } from "@/lib/auth";

type EventItem = { id: string; title: string; slug: string };

function roleLabel(role: string | null): string {
  if (role === "student") return "학생";
  if (role === "teacher") return "지도교사";
  if (role === "evangelist") return "전도사";
  if (role === "pastor") return "목사";
  return "미입력";
}

export default function FieldPage() {
  const router = useRouter();
  const role = "staff";

  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");
  const [query, setQuery] = useState("");
  const [participants, setParticipants] = useState<ParticipantRow[]>([]);

  const [registeredCount, setRegisteredCount] = useState(0);
  const [checkedInCount, setCheckedInCount] = useState(0);

  const [onlyUnchecked, setOnlyUnchecked] = useState(true);
  const [authReady, setAuthReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("현장 체크인 준비 완료");

  const pendingCount = useMemo(() => Math.max(0, registeredCount - checkedInCount), [registeredCount, checkedInCount]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return participants.filter((p) => {
      const checked = p.ticket_status === "active";
      if (onlyUnchecked && checked) return false;
      if (!q) return true;
      return (
        p.name.toLowerCase().includes(q)
        || (p.church_or_school ?? "").toLowerCase().includes(q)
        || (p.grade ?? "").toLowerCase().includes(q)
        || roleLabel(p.participant_role).toLowerCase().includes(q)
      );
    });
  }, [participants, query, onlyUnchecked]);

  async function runTask(task: () => Promise<void>) {
    try {
      setBusy(true);
      await task();
    } catch (error) {
      setLog(error instanceof Error ? error.message : "오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  const refresh = () =>
    runTask(async () => {
      if (!eventId) throw new Error("행사를 먼저 선택하세요.");
      const [dashboard, rows] = await Promise.all([
        api<{ registered_count: number; checked_in_count: number }>(`/api/events/${eventId}/dashboard`, {
          headers: roleHeader(role),
        }),
        api<ParticipantRow[]>(`/api/events/${eventId}/participants`, {
          headers: roleHeader(role),
        }),
      ]);
      setRegisteredCount(dashboard.registered_count);
      setCheckedInCount(dashboard.checked_in_count);
      setParticipants(rows);
      setLog("현장 목록을 업데이트했습니다.");
    });

  const checkin = (participantId: string, name: string) =>
    runTask(async () => {
      if (!eventId) throw new Error("행사를 먼저 선택하세요.");
      await api("/api/checkins/by-participant", {
        method: "POST",
        headers: roleHeader(role),
        json: {
          event_id: eventId,
          participant_id: participantId,
          checkin_type: "entry",
        },
      });
      setLog(`${name} 체크인 완료`);
      await refresh();
    });

  useEffect(() => {
    void (async () => {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      try {
        const me = await fetchMe();
        if (!canAccessField(me)) {
          router.replace("/login");
          return;
        }
        setAuthReady(true);
      } catch {
        await logout();
        router.replace("/login");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!authReady) return;
    void runTask(async () => {
      const list = await api<EventItem[]>("/api/events", { headers: roleHeader(role) });
      setEvents(list);
      if (list[0]) setEventId(list[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authReady]);

  useEffect(() => {
    if (!authReady) return;
    if (!eventId) return;
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, authReady]);

  return (
    <WorkspaceShell
      title="현장 콘솔"
      subtitle="체크인을 빠르고 정확하게"
      sectionLinks={[{ href: "#checkin", label: "체크인" }]}
    >
      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>오늘 행사 선택</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Select value={eventId} onValueChange={setEventId}>
            <SelectTrigger>
              <SelectValue placeholder="행사를 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {events.map((event) => (
                <SelectItem key={event.id} value={event.id}>
                  {event.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="grid grid-cols-3 gap-2">
            <Stat label="등록" value={registeredCount} />
            <Stat label="체크인" value={checkedInCount} />
            <Stat label="남은 인원" value={pendingCount} />
          </div>
        </CardContent>
      </Card>

      <Card id="checkin" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>참가자 체크인</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2 rounded-xl border border-border bg-white px-3 py-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              className="h-auto border-none px-0 shadow-none focus-visible:ring-0"
              placeholder="이름, 소속, 학년 검색"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" className="h-4 w-4" checked={onlyUnchecked} onChange={(e) => setOnlyUnchecked(e.target.checked)} />
            미체크인만 보기
          </label>

          <div className="grid gap-2">
            {filtered.length ? (
              filtered.map((row) => {
                const checked = row.ticket_status === "active";
                return (
                  <div key={row.participant_id} className="rounded-xl border border-border bg-white p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold">{row.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(row.church_or_school ?? "소속 미입력")} · {(row.grade ?? "학년 미입력")} · {roleLabel(row.participant_role)}
                        </p>
                      </div>
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                        {checked ? "완료" : "대기"}
                      </span>
                    </div>
                    <Button
                      className="mt-3 h-10 w-full rounded-xl"
                      variant={checked ? "secondary" : "default"}
                      disabled={busy || checked}
                      onClick={() => checkin(row.participant_id, row.name)}
                    >
                      <UserCheck2 className="mr-2 h-4 w-4" />
                      {checked ? "체크인 완료" : "체크인 처리"}
                    </Button>
                  </div>
                );
              })
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">표시할 참가자가 없습니다.</div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-dashed bg-secondary/70">
        <CardContent className="py-4 text-sm text-muted-foreground">{log}</CardContent>
      </Card>

      <MobileDock>
        <div className="mx-auto max-w-[980px]">
          <Button className="h-12 w-full rounded-xl" onClick={refresh} disabled={busy || !eventId}>
            현장 목록 새로고침
          </Button>
        </div>
      </MobileDock>
    </WorkspaceShell>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-white px-2 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
