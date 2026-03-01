"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { WorkspaceShell } from "@/components/shared/workspace-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, roleHeader, type ParticipantRow } from "@/lib/api";
import { canAccessLeader, fetchMe, getToken, logout, type SessionUser } from "@/lib/auth";

type EventItem = { id: string; slug: string; title: string };
type GroupSlot = { id: string; name: string; capacity: number; sort_order: number };
type GroupAssignment = { participant_id: string; group_id: string };
type NoticeDoc = { id: string; title: string; content: string | null };

const ROLE = "leader";
const ORG_ID = "org-1";

function roleLabel(role: string | null): string {
  if (role === "student") return "학생";
  if (role === "teacher") return "지도교사";
  if (role === "evangelist") return "전도사";
  if (role === "pastor") return "목사";
  return "기타";
}

function refundLabel(status: string | null, requested: boolean | null): string {
  if (status === "approved") return "승인";
  if (status === "rejected") return "거절";
  if (status === "pending" || requested) return "요청중";
  return "없음";
}

export default function LeaderPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");

  const [participants, setParticipants] = useState<ParticipantRow[]>([]);
  const [groups, setGroups] = useState<GroupSlot[]>([]);
  const [assignments, setAssignments] = useState<GroupAssignment[]>([]);
  const [notices, setNotices] = useState<NoticeDoc[]>([]);

  const [selectedChurch, setSelectedChurch] = useState("all");
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null);
  const [q, setQ] = useState("");
  const [reasonDrafts, setReasonDrafts] = useState<Record<string, string>>({});

  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("지도교사 콘솔 준비 완료");

  const students = useMemo(() => participants.filter((p) => p.participant_role === "student"), [participants]);

  const churches = useMemo(() => {
    return Array.from(new Set(students.map((p) => p.church_or_school || "소속 미입력"))).sort();
  }, [students]);

  const visibleStudents = useMemo(() => {
    const query = q.trim().toLowerCase();
    return students.filter((p) => {
      const church = p.church_or_school || "소속 미입력";
      if (currentUser?.account_type === "leader" && currentUser.church_or_school && church !== currentUser.church_or_school) {
        return false;
      }
      if (selectedChurch !== "all" && church !== selectedChurch) return false;
      if (!query) return true;
      return (
        p.name.toLowerCase().includes(query)
        || church.toLowerCase().includes(query)
        || roleLabel(p.participant_role).toLowerCase().includes(query)
      );
    });
  }, [students, selectedChurch, q]);

  const groupNameById = useMemo(() => {
    const map = new Map<string, string>();
    groups.forEach((g) => map.set(g.id, g.name));
    return map;
  }, [groups]);

  const assignmentByParticipantId = useMemo(() => {
    const map = new Map<string, string>();
    assignments.forEach((a) => map.set(a.participant_id, a.group_id));
    return map;
  }, [assignments]);

  const churchSummary = useMemo(() => {
    const bucket = new Map<string, { total: number; paid: number; unpaid: number }>();
    students.forEach((p) => {
      const church = p.church_or_school || "소속 미입력";
      const current = bucket.get(church) ?? { total: 0, paid: 0, unpaid: 0 };
      current.total += 1;
      if (p.registration_fee_paid) current.paid += 1;
      else current.unpaid += 1;
      bucket.set(church, current);
    });
    return Array.from(bucket.entries())
      .map(([church, s]) => ({ church, ...s }))
      .sort((a, b) => b.total - a.total);
  }, [students]);

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

      const [rows, groupRows, groupAssignments, noticeDocs] = await Promise.all([
        api<ParticipantRow[]>(`/api/events/${eventId}/participants`, { headers: roleHeader(ROLE) }),
        api<GroupSlot[]>(`/api/events/${eventId}/groups`, { headers: roleHeader(ROLE) }).catch(() => []),
        api<GroupAssignment[]>(`/api/events/${eventId}/assignments/group`, { headers: roleHeader(ROLE) }).catch(() => []),
        api<NoticeDoc[]>(`/api/team/documents?org_id=${encodeURIComponent(ORG_ID)}&kind=notice`, {
          headers: roleHeader(ROLE),
        }).catch(() => []),
      ]);

      setParticipants(rows);
      setGroups(groupRows);
      setAssignments(groupAssignments);
      setNotices(noticeDocs);

      if (selectedChurch !== "all") {
        const exists = rows.some((p) => (p.church_or_school || "소속 미입력") === selectedChurch && p.participant_role === "student");
        if (!exists) setSelectedChurch("all");
      }

      setLog("학생 등록 정보를 불러왔습니다.");
    });

  const markFeePaid = (participantId: string, paid: boolean) =>
    runTask(async () => {
      await api(`/api/participants/${participantId}/answers`, {
        method: "PATCH",
        headers: roleHeader(ROLE),
        json: { answers: { registration_fee_paid: paid } },
      });
      await refresh();
    });

  const markChurchPaid = (church: string) =>
    runTask(async () => {
      const targets = students.filter((p) => (p.church_or_school || "소속 미입력") === church && !p.registration_fee_paid);
      await Promise.all(
        targets.map((p) =>
          api(`/api/participants/${p.participant_id}/answers`, {
            method: "PATCH",
            headers: roleHeader(ROLE),
            json: { answers: { registration_fee_paid: true } },
          }),
        ),
      );
      await refresh();
      setLog(`${church} 미납 인원을 납부완료로 처리했습니다.`);
    });

  const requestRefund = (participantId: string) =>
    runTask(async () => {
      const reason = (reasonDrafts[participantId] || "").trim();
      if (!reason) throw new Error("환불 요청 사유를 입력하세요.");

      await api(`/api/participants/${participantId}/answers`, {
        method: "PATCH",
        headers: roleHeader(ROLE),
        json: {
          answers: {
            refund_requested: true,
            refund_status: "pending",
            refund_reason: reason,
            refund_requested_by: currentUser?.name ?? "지도교사",
            refund_requested_at: new Date().toISOString(),
          },
        },
      });
      setReasonDrafts((prev) => ({ ...prev, [participantId]: "" }));
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
        if (!canAccessLeader(me)) {
          router.replace("/login");
          return;
        }
        setCurrentUser(me);
        if (me.account_type === "leader" && me.church_or_school) {
          setSelectedChurch(me.church_or_school);
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
      const list = await api<EventItem[]>("/api/events", { headers: roleHeader(ROLE) });
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
      title="지도교사 콘솔"
      subtitle="교회 학생 등록 정보와 납부·환불 관리"
      sectionLinks={[
        { href: "#notice", label: "행사 공지" },
        { href: "#church-summary", label: "교회별 납부" },
        { href: "#students", label: "학생 등록 정보" },
      ]}
    >
      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>행사 선택</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Select value={eventId} onValueChange={setEventId}>
            <SelectTrigger>
              <SelectValue placeholder="행사를 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {events.map((event) => (
                <SelectItem key={event.id} value={event.id}>{event.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={refresh} disabled={busy} className="h-11 w-full rounded-xl">새로고침</Button>
        </CardContent>
      </Card>

      <Card id="notice" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>행사 공지 확인 (최신순)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {notices.length ? (
            notices.slice(0, 10).map((notice) => (
              <div key={notice.id} className="rounded-xl border border-border bg-white p-3">
                <p className="text-sm font-semibold">{notice.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{notice.content || "내용 없음"}</p>
              </div>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">등록된 공지가 없습니다.</div>
          )}
        </CardContent>
      </Card>

      <Card id="church-summary" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>교회 단위 등록비 납부 현황</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {churchSummary.length ? (
            churchSummary.map((s) => (
              <div key={s.church} className="rounded-xl border border-border bg-white px-3 py-2">
                <p className="text-sm font-semibold">{s.church}</p>
                <p className="text-xs text-muted-foreground">총 {s.total}명 · 납부 {s.paid}명 · 미납 {s.unpaid}명</p>
                <Button
                  className="mt-2 h-9 rounded-lg"
                  variant="secondary"
                  disabled={busy || s.unpaid === 0}
                  onClick={() => markChurchPaid(s.church)}
                >
                  미납 전체 납부처리
                </Button>
              </div>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">표시할 데이터가 없습니다.</div>
          )}
        </CardContent>
      </Card>

      <Card id="students" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>교회 학생 등록 정보</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-2">
            <Select value={selectedChurch} onValueChange={setSelectedChurch} disabled={currentUser?.account_type === "leader" && !!currentUser.church_or_school}>
              <SelectTrigger>
                <SelectValue placeholder="교회 선택" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체 교회</SelectItem>
                {churches.map((church) => (
                  <SelectItem key={church} value={church}>{church}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input placeholder="이름/교회 검색" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>

          <div className="grid gap-2">
            {visibleStudents.length ? (
              visibleStudents.map((p) => {
                const groupId = assignmentByParticipantId.get(p.participant_id);
                const groupName = groupId ? (groupNameById.get(groupId) || "배정됨") : "미배정";
                const paid = p.registration_fee_paid === true;
                const refund = refundLabel(p.refund_status, p.refund_requested);

                return (
                  <div key={p.participant_id} className="rounded-xl border border-border bg-white p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold">{p.name}</p>
                        <p className="text-xs text-muted-foreground">{roleLabel(p.participant_role)} · {p.church_or_school || "소속 미입력"}</p>
                        <p className="text-xs text-muted-foreground">조배정: {groupName}</p>
                        <p className="text-xs text-muted-foreground">등록비: {paid ? "납부완료" : "미납"} · 환불: {refund}</p>
                        {p.refund_reason ? <p className="text-xs text-muted-foreground">사유: {p.refund_reason}</p> : null}
                      </div>
                    </div>

                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <Button
                        className="h-9 rounded-lg"
                        variant={paid ? "secondary" : "default"}
                        disabled={busy || paid}
                        onClick={() => markFeePaid(p.participant_id, true)}
                      >
                        납부 완료 처리
                      </Button>
                      <Button
                        className="h-9 rounded-lg"
                        variant="secondary"
                        disabled={busy || p.refund_status === "pending"}
                        onClick={() => requestRefund(p.participant_id)}
                      >
                        환불 요청
                      </Button>
                    </div>

                    <div className="mt-2 grid gap-1">
                      <Textarea
                        rows={2}
                        placeholder="환불 요청 사유"
                        value={reasonDrafts[p.participant_id] ?? ""}
                        onChange={(e) => setReasonDrafts((prev) => ({ ...prev, [p.participant_id]: e.target.value }))}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">표시할 학생 데이터가 없습니다.</div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-dashed bg-secondary/70">
        <CardContent className="py-4 text-sm text-muted-foreground">{log}</CardContent>
      </Card>
    </WorkspaceShell>
  );
}
