"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarPlus, CheckCircle2, FileText, Users } from "lucide-react";
import { useRouter } from "next/navigation";

import { WorkspaceShell } from "@/components/shared/workspace-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, roleHeader, type ParticipantRow } from "@/lib/api";
import { canAccessAdmin, fetchMe, getToken, logout, type SessionUser } from "@/lib/auth";

type EventItem = { id: string; slug: string; title: string; template: string };
type ReportSummary = {
  registered_count: number;
  checked_in_count: number;
  survey_response_count: number;
  survey_response_rate: number;
  survey_average_rating: number | null;
};
type MeetingItem = { id: string; title: string; started_at: string };
type ActionItem = { id: string; title: string; status: string; department: string | null };
type TeamDocument = { id: string; title: string; version: number };
type PublicParticipantInfo = { title: string; content: string };
type RoleKey = "student" | "teacher" | "evangelist" | "pastor" | "unknown";

type TeamScope = "all" | "common" | "ops" | "planning" | "education" | "life" | "promo";
type CreateScope = Exclude<TeamScope, "all">;
type AdminSection = "overview" | "operations" | "team" | "approvals" | "team-leads" | "refunds";

const ROLE = "event_admin";
const ORG_ID = "org-1";

const TEAM_META: Record<CreateScope, { label: string; prefix: string; department: string | null }> = {
  common: { label: "공통(전체 공유)", prefix: "[공통]", department: null },
  ops: { label: "운영팀", prefix: "[운영팀]", department: "운영팀" },
  planning: { label: "기획팀", prefix: "[기획팀]", department: "기획팀" },
  education: { label: "교육팀", prefix: "[교육팀]", department: "교육팀" },
  life: { label: "생활팀", prefix: "[생활팀]", department: "생활팀" },
  promo: { label: "홍보팀", prefix: "[홍보팀]", department: "홍보팀" },
};

const VIEW_SCOPE_OPTIONS: { value: TeamScope; label: string }[] = [
  { value: "all", label: "전체 보기" },
  { value: "common", label: TEAM_META.common.label },
  { value: "ops", label: TEAM_META.ops.label },
  { value: "planning", label: TEAM_META.planning.label },
  { value: "education", label: TEAM_META.education.label },
  { value: "life", label: TEAM_META.life.label },
  { value: "promo", label: TEAM_META.promo.label },
];

const CREATE_SCOPE_OPTIONS: { value: CreateScope; label: string }[] = [
  { value: "common", label: TEAM_META.common.label },
  { value: "ops", label: TEAM_META.ops.label },
  { value: "planning", label: TEAM_META.planning.label },
  { value: "education", label: TEAM_META.education.label },
  { value: "life", label: TEAM_META.life.label },
  { value: "promo", label: TEAM_META.promo.label },
];
const OVERVIEW_SCOPES: CreateScope[] = ["common", "ops", "planning", "education", "life", "promo"];

function scopeLabel(scope: TeamScope): string {
  return VIEW_SCOPE_OPTIONS.find((item) => item.value === scope)?.label ?? "전체 보기";
}

function prefixedTitle(scope: CreateScope, title: string): string {
  const raw = title.trim();
  if (!raw) return raw;

  const knownPrefixes = Object.values(TEAM_META).map((item) => item.prefix);
  if (knownPrefixes.some((prefix) => raw.startsWith(prefix))) return raw;

  return `${TEAM_META[scope].prefix} ${raw}`;
}

function parseScopeFromTitle(title: string): TeamScope {
  const entry = (Object.entries(TEAM_META) as [CreateScope, { label: string; prefix: string; department: string | null }][]).find(([, meta]) =>
    title.startsWith(meta.prefix),
  );
  return entry ? entry[0] : "common";
}

function stripScopePrefix(title: string): string {
  return title.replace(/^\[(공통|운영팀|기획팀|교육팀|생활팀|홍보팀)\]\s*/, "");
}

function departmentToScope(department: string | null): TeamScope {
  if (!department) return "common";
  if (department === "운영팀") return "ops";
  if (department === "기획팀") return "planning";
  if (department === "교육팀") return "education";
  if (department === "생활팀") return "life";
  if (department === "홍보팀") return "promo";
  return "common";
}

function scopeToDepartment(scope: CreateScope): string | null {
  return TEAM_META[scope].department;
}

function matchesScope(itemScope: TeamScope, viewScope: TeamScope): boolean {
  if (viewScope === "all") return true;
  if (viewScope === "common") return itemScope === "common";
  return itemScope === "common" || itemScope === viewScope;
}

function roleToKey(role: string | null): RoleKey {
  if (role === "student") return "student";
  if (role === "teacher") return "teacher";
  if (role === "evangelist") return "evangelist";
  if (role === "pastor") return "pastor";
  return "unknown";
}

function teamToScope(team: string | null): CreateScope {
  if (team === "ops") return "ops";
  if (team === "planning") return "planning";
  if (team === "education") return "education";
  if (team === "life") return "life";
  if (team === "promo") return "promo";
  return "common";
}

export default function AdminPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");
  const [report, setReport] = useState<ReportSummary | null>(null);

  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [docs, setDocs] = useState<TeamDocument[]>([]);

  const [viewScope, setViewScope] = useState<TeamScope>("all");
  const [createScope, setCreateScope] = useState<CreateScope>("common");
  const [activeSection, setActiveSection] = useState<AdminSection>("overview");

  const [newEventTitle, setNewEventTitle] = useState("봄 청소년 캠프");
  const [groupCount, setGroupCount] = useState("5");
  const [groupCapacity, setGroupCapacity] = useState("20");
  const [meetingTitle, setMeetingTitle] = useState("운영 점검 회의");
  const [actionTitle, setActionTitle] = useState("현장 안내 배너 점검");
  const [docTitle, setDocTitle] = useState("현장 운영 노트");
  const [docContent, setDocContent] = useState("입장 동선, 안전 공지, 담당자 연락처");
  const [noticeTitle, setNoticeTitle] = useState("행사 공지");
  const [noticeContent, setNoticeContent] = useState("집결 시간, 복장, 준비물을 확인해 주세요.");
  const [participantInfoTitle, setParticipantInfoTitle] = useState("행사 안내");
  const [participantInfoContent, setParticipantInfoContent] = useState("장소 안내와 준비물을 확인하고 등록을 진행해 주세요.");

  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState("관리자 콘솔 준비 완료");
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<SessionUser[]>([]);
  const [ministryUsers, setMinistryUsers] = useState<SessionUser[]>([]);
  const [participantRows, setParticipantRows] = useState<ParticipantRow[]>([]);
  const [roleCounts, setRoleCounts] = useState<Record<RoleKey, number>>({
    student: 0,
    teacher: 0,
    evangelist: 0,
    pastor: 0,
    unknown: 0,
  });

  const checkinRate = useMemo(() => {
    if (!report || report.registered_count === 0) return 0;
    return Math.round((report.checked_in_count / report.registered_count) * 100);
  }, [report]);

  const meetingItems = useMemo(() => {
    return meetings
      .filter((m) => matchesScope(parseScopeFromTitle(m.title), viewScope))
      .map((m) => {
        const scope = parseScopeFromTitle(m.title);
        return `${scopeLabel(scope)} · ${stripScopePrefix(m.title)}`;
      });
  }, [meetings, viewScope]);

  const actionItems = useMemo(() => {
    return actions
      .filter((a) => matchesScope(departmentToScope(a.department), viewScope))
      .map((a) => {
        const scope = departmentToScope(a.department);
        return `${scopeLabel(scope)} · ${a.title} · ${a.status}`;
      });
  }, [actions, viewScope]);

  const documentItems = useMemo(() => {
    return docs
      .filter((d) => matchesScope(parseScopeFromTitle(d.title), viewScope))
      .map((d) => {
        const scope = parseScopeFromTitle(d.title);
        return `${scopeLabel(scope)} · ${stripScopePrefix(d.title)} (v${d.version})`;
      });
  }, [docs, viewScope]);

  const refundRequests = useMemo(() => {
    return participantRows.filter((row) => row.refund_status === "pending");
  }, [participantRows]);
  const isSuperAdmin = Boolean(currentUser?.is_super_admin);
  const isTeamScoped = Boolean(currentUser && !currentUser.can_approve);
  const isTeamLead = Boolean(currentUser?.is_team_lead);
  const teamScopedValue = teamToScope(currentUser?.team ?? null);
  const overviewScopes = useMemo(() => {
    if (!isTeamScoped) return OVERVIEW_SCOPES;
    const scopes: CreateScope[] = ["common"];
    if (teamScopedValue !== "common") scopes.push(teamScopedValue);
    return scopes;
  }, [isTeamScoped, teamScopedValue]);

  const teamOverviewCards = useMemo(() => {
    return overviewScopes.map((scope) => {
      const meetingCount = meetings.filter((m) => parseScopeFromTitle(m.title) === scope).length;
      const openActionCount = actions.filter(
        (a) => departmentToScope(a.department) === scope && a.status === "open",
      ).length;
      const docCount = docs.filter((d) => parseScopeFromTitle(d.title) === scope).length;
      return {
        scope,
        label: TEAM_META[scope].label,
        meetingCount,
        openActionCount,
        docCount,
      };
    });
  }, [overviewScopes, meetings, actions, docs]);

  const allowedViewScopeOptions = isTeamScoped
    ? VIEW_SCOPE_OPTIONS.filter((item) => item.value === "common" || item.value === teamScopedValue)
    : VIEW_SCOPE_OPTIONS;
  const allowedCreateScopeOptions = isTeamScoped
    ? CREATE_SCOPE_OPTIONS.filter((item) => item.value === teamScopedValue)
    : CREATE_SCOPE_OPTIONS;
  const sectionTabs = useMemo(() => {
    const tabs: { key: AdminSection; label: string }[] = [
      { key: "overview", label: "핵심 현황" },
      { key: "operations", label: "운영 액션" },
      { key: "team", label: "팀 운영" },
    ];
    if (isSuperAdmin) {
      tabs.push({ key: "approvals", label: "가입 승인" });
      tabs.push({ key: "team-leads", label: "팀장 권한" });
    }
    if (isTeamLead) {
      tabs.push({ key: "refunds", label: "환불 승인" });
    }
    return tabs;
  }, [isSuperAdmin, isTeamLead]);

  const runTask = async (task: () => Promise<void>) => {
    try {
      setBusy(true);
      await task();
    } catch (error) {
      setLog(error instanceof Error ? error.message : "오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const loadEvents = async () => {
    const list = await api<EventItem[]>("/api/events", { headers: roleHeader(ROLE) });
    setEvents(list);
    if (!eventId && list[0]) setEventId(list[0].id);
  };

  const loadReport = async (selectedEventId: string) => {
    if (!selectedEventId) {
      setReport(null);
      return;
    }

    const summary = await api<ReportSummary>(`/api/events/${selectedEventId}/reports/summary`, {
      headers: roleHeader(ROLE),
    });
    setReport(summary);
  };

  const loadRoleSummary = async (selectedEventId: string) => {
    if (!selectedEventId) {
      setParticipantRows([]);
      setRoleCounts({ student: 0, teacher: 0, evangelist: 0, pastor: 0, unknown: 0 });
      return;
    }
    const rows = await api<ParticipantRow[]>(`/api/events/${selectedEventId}/participants`, {
      headers: roleHeader(ROLE),
    });
    setParticipantRows(rows);
    const next: Record<RoleKey, number> = { student: 0, teacher: 0, evangelist: 0, pastor: 0, unknown: 0 };
    for (const row of rows) {
      const key = roleToKey(row.participant_role);
      next[key] += 1;
    }
    setRoleCounts(next);
  };

  const decideRefund = (participantId: string, approve: boolean) =>
    runTask(async () => {
      await api(`/api/participants/${participantId}/refund-decision`, {
        method: "POST",
        json: { approve },
      });
      if (eventId) {
        await loadRoleSummary(eventId);
      }
      setLog(`환불 요청을 ${approve ? "승인" : "거절"}했습니다.`);
    });

  const loadParticipantInfo = async (selectedEventId: string) => {
    if (!selectedEventId) {
      setParticipantInfoTitle("행사 안내");
      setParticipantInfoContent("장소 안내와 준비물을 확인하고 등록을 진행해 주세요.");
      return;
    }
    const info = await api<PublicParticipantInfo>(`/api/public/events/${selectedEventId}/participant-info`);
    setParticipantInfoTitle(info.title || "행사 안내");
    setParticipantInfoContent(info.content || "");
  };

  const loadTeam = async () => {
    const [ms, ais, ds] = await Promise.all([
      api<MeetingItem[]>(`/api/team/meetings?org_id=${encodeURIComponent(ORG_ID)}`, { headers: roleHeader(ROLE) }),
      api<ActionItem[]>(`/api/team/action-items?org_id=${encodeURIComponent(ORG_ID)}`, { headers: roleHeader(ROLE) }),
      api<TeamDocument[]>(`/api/team/documents?org_id=${encodeURIComponent(ORG_ID)}`, { headers: roleHeader(ROLE) }),
    ]);
    setMeetings(ms);
    setActions(ais);
    setDocs(ds);
  };

  const loadMinistryUsers = async () => {
    const users = await api<SessionUser[]>("/api/auth/ministry-users");
    setMinistryUsers(users);
  };

  const refreshAll = () =>
    runTask(async () => {
      await loadEvents();
      const selected = eventId || events[0]?.id || "";
      if (selected) {
        setEventId(selected);
        await loadReport(selected);
        await loadRoleSummary(selected);
        await loadParticipantInfo(selected);
      }
      await loadTeam();
      setLog("최신 상태로 업데이트했습니다.");
    });

  const createEvent = () =>
    runTask(async () => {
      if (!newEventTitle.trim()) throw new Error("행사 이름을 입력하세요.");
      const created = await api<{ id: string; title: string }>("/api/events", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          slug: `event-${Date.now()}`,
          title: newEventTitle.trim(),
          template: "day_event",
          start_at: "2026-05-16T00:00:00Z",
          end_at: "2026-05-16T11:00:00Z",
          capacity: 300,
        },
      });
      await loadEvents();
      setEventId(created.id);
      await loadReport(created.id);
      setLog(`새 행사 생성 완료: ${created.title}`);
    });

  const deleteSelectedEvent = () =>
    runTask(async () => {
      if (!isTeamLead) throw new Error("팀장 권한이 있어야 삭제할 수 있습니다.");
      if (!eventId) throw new Error("삭제할 행사를 먼저 선택하세요.");
      const selected = events.find((item) => item.id === eventId);
      if (!selected) throw new Error("선택된 행사 정보를 찾을 수 없습니다.");
      if (!window.confirm(`'${selected.title}' 행사를 삭제하시겠습니까?`)) return;

      await api<{ id: string; title: string }>(`/api/events/${eventId}`, {
        method: "DELETE",
      });

      const list = await api<EventItem[]>("/api/events", { headers: roleHeader(ROLE) });
      setEvents(list);
      const nextId = list[0]?.id ?? "";
      setEventId(nextId);
      if (nextId) {
        await loadReport(nextId);
        await loadRoleSummary(nextId);
      } else {
        setReport(null);
        setParticipantRows([]);
      }
      setLog(`행사를 삭제했습니다: ${selected.title}`);
    });

  const deleteAllEvents = () =>
    runTask(async () => {
      if (!isTeamLead) throw new Error("팀장 권한이 있어야 삭제할 수 있습니다.");
      if (!events.length) throw new Error("삭제할 행사가 없습니다.");
      if (!window.confirm(`현재 행사 ${events.length}개를 모두 삭제하시겠습니까?`)) return;

      for (const item of events) {
        await api(`/api/events/${item.id}`, { method: "DELETE" });
      }

      setEvents([]);
      setEventId("");
      setReport(null);
      setParticipantRows([]);
      setRoleCounts({ student: 0, teacher: 0, evangelist: 0, pastor: 0, unknown: 0 });
      setLog(`행사 ${events.length}개를 모두 삭제했습니다.`);
    });

  const addMeeting = () =>
    runTask(async () => {
      await api("/api/team/meetings", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          title: prefixedTitle(createScope, meetingTitle),
          started_at: new Date().toISOString(),
        },
      });
      await loadTeam();
      setLog(`${scopeLabel(createScope)} 회의를 추가했습니다.`);
    });

  const addAction = () =>
    runTask(async () => {
      await api("/api/team/action-items", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          title: actionTitle,
          department: scopeToDepartment(createScope),
          status: "open",
          event_id: eventId || null,
        },
      });
      await loadTeam();
      setLog(`${scopeLabel(createScope)} 할 일을 추가했습니다.`);
    });

  const addDoc = () =>
    runTask(async () => {
      await api("/api/team/documents", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          title: prefixedTitle(createScope, docTitle),
          kind: "guide",
          content: docContent,
          event_id: eventId || null,
          version: 1,
        },
      });
      await loadTeam();
      setLog(`${scopeLabel(createScope)} 운영 노트를 저장했습니다.`);
    });

  const addNotice = () =>
    runTask(async () => {
      await api("/api/team/documents", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          title: prefixedTitle("common", noticeTitle),
          kind: "notice",
          content: noticeContent,
          event_id: eventId || null,
          version: 1,
        },
      });
      setLog("지도교사 콘솔용 행사 공지를 등록했습니다.");
    });

  const saveParticipantInfo = () =>
    runTask(async () => {
      if (!eventId) throw new Error("행사를 먼저 선택하세요.");
      if (!participantInfoTitle.trim()) throw new Error("안내 제목을 입력하세요.");
      await api("/api/team/documents", {
        method: "POST",
        headers: roleHeader(ROLE),
        json: {
          org_id: ORG_ID,
          title: participantInfoTitle.trim(),
          kind: "participant_info",
          content: participantInfoContent.trim(),
          event_id: eventId,
          version: 1,
        },
      });
      setLog("참가자 콘솔 행사 안내/등록 정보를 저장했습니다.");
    });

  const runGrouping = () =>
    runTask(async () => {
      if (!eventId) throw new Error("행사를 먼저 선택하세요.");

      const count = Number.parseInt(groupCount, 10);
      const capacity = Number.parseInt(groupCapacity, 10);

      if (!Number.isFinite(count) || count < 1 || count > 20) {
        throw new Error("조 개수는 1~20 사이로 입력하세요.");
      }
      if (!Number.isFinite(capacity) || capacity < 1 || capacity > 999) {
        throw new Error("조별 인원은 1~999 사이로 입력하세요.");
      }

      const groups = Array.from({ length: count }, (_, i) => ({
        name: `${i + 1}조`,
        capacity,
        sort_order: i + 1,
      }));

      await api(`/api/events/${eventId}/groups`, {
        method: "PUT",
        headers: roleHeader(ROLE),
        json: { groups },
      });
      const result = await api<{ assigned_count: number }>(`/api/events/${eventId}/assignments/group/run`, {
        method: "POST",
        headers: roleHeader(ROLE),
      });
      setLog(`${count}개 조(조별 ${capacity}명)로 자동 배정했습니다. (${result.assigned_count}명)`);
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
        if (!canAccessAdmin(me)) {
          router.replace("/login");
          return;
        }
        setCurrentUser(me);
        const teamScope = teamToScope(me.team);
        setViewScope(teamScope);
        setCreateScope(teamScope);
        if (me.is_super_admin) {
          const pending = await api<{ id: string; email: string; name: string; account_type: "ministry" | "leader"; leader_role: string | null; church_or_school: string | null; team: string | null; status: "pending" | "approved" | "rejected"; can_approve: boolean; is_team_lead: boolean; is_super_admin: boolean; }[]>("/api/auth/approvals");
          setPendingApprovals(pending as SessionUser[]);
          await loadMinistryUsers();
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
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authReady]);

  useEffect(() => {
    if (!authReady) return;
    if (!eventId) return;
    void runTask(async () => {
      await loadReport(eventId);
      await loadRoleSummary(eventId);
      await loadParticipantInfo(eventId);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, authReady]);

  useEffect(() => {
    if (!sectionTabs.some((tab) => tab.key === activeSection)) {
      setActiveSection("overview");
    }
  }, [sectionTabs, activeSection]);

  const decideApproval = (userId: string, approve: boolean) =>
    runTask(async () => {
      await api(`/api/auth/approvals/${userId}`, {
        method: "POST",
        json: { approve },
      });
      const pending = await api<SessionUser[]>("/api/auth/approvals");
      setPendingApprovals(pending);
      await loadMinistryUsers();
      setLog(`사역팀 가입 요청을 ${approve ? "승인" : "거절"}했습니다.`);
    });

  const decideTeamLead = (userId: string, isTeamLead: boolean) =>
    runTask(async () => {
      await api(`/api/auth/ministry-users/${userId}/team-lead`, {
        method: "PATCH",
        json: { is_team_lead: isTeamLead },
      });
      await loadMinistryUsers();
      setLog(`팀장 권한을 ${isTeamLead ? "부여" : "해제"}했습니다.`);
    });

  const uploadMyProfileImage = (file: File | null) =>
    runTask(async () => {
      if (!file) return;
      if (!file.type.startsWith("image/")) throw new Error("이미지 파일만 업로드할 수 있습니다.");
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("이미지 파일을 읽지 못했습니다."));
        reader.readAsDataURL(file);
      });
      const result = await api<{ user: SessionUser }>("/api/auth/me/profile-image", {
        method: "PATCH",
        json: { image_data_url: dataUrl },
      });
      setCurrentUser(result.user);
      setLog("프로필 사진을 저장했습니다.");
    });

  return (
    <WorkspaceShell
      title="관리자 콘솔"
      subtitle="준비·운영·리포트를 한 번에"
    >
      <Card className="surface-soft rounded-2xl">
        <CardContent className="flex flex-wrap gap-2 py-3">
          {sectionTabs.map((tab) => (
            <Button
              key={tab.key}
              type="button"
              variant={activeSection === tab.key ? "default" : "secondary"}
              className="h-9 rounded-full px-4"
              onClick={() => setActiveSection(tab.key)}
            >
              {tab.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      {activeSection === "overview" ? (
      <Card id="overview" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>핵심 현황</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-xl border border-border bg-white p-3">
            <p className="text-xs text-muted-foreground">내 프로필 사진</p>
            <div className="mt-2 flex items-center gap-3">
              {currentUser?.profile_image_url ? (
                <img
                  src={currentUser.profile_image_url}
                  alt="내 프로필"
                  className="h-12 w-12 rounded-full border border-border object-cover"
                />
              ) : (
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-border bg-secondary text-xs text-muted-foreground">
                  없음
                </div>
              )}
              <label className="inline-flex h-10 cursor-pointer items-center rounded-lg border border-border bg-white px-3 text-sm">
                사진 업로드
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
                    void uploadMyProfileImage(file);
                    e.currentTarget.value = "";
                  }}
                />
              </label>
            </div>
          </div>

          <Select value={eventId} onValueChange={setEventId}>
            <SelectTrigger>
              <SelectValue placeholder="행사를 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {events.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="grid gap-2 sm:grid-cols-4">
            <Metric icon={Users} label="등록" value={String(report?.registered_count ?? 0)} />
            <Metric icon={CheckCircle2} label="체크인" value={String(report?.checked_in_count ?? 0)} />
            <Metric icon={BarChart3} label="설문 응답" value={String(report?.survey_response_count ?? 0)} />
            <Metric icon={BarChart3} label="체크인율" value={`${checkinRate}%`} />
          </div>

          <div className="grid gap-2 sm:grid-cols-5">
            <MiniStat label="학생" value={roleCounts.student} />
            <MiniStat label="지도교사" value={roleCounts.teacher} />
            <MiniStat label="전도사" value={roleCounts.evangelist} />
            <MiniStat label="목사" value={roleCounts.pastor} />
            <MiniStat label="미입력" value={roleCounts.unknown} />
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {teamOverviewCards.map((card) => (
              <TeamStatusCard
                key={card.scope}
                label={card.label}
                meetingCount={card.meetingCount}
                openActionCount={card.openActionCount}
                docCount={card.docCount}
              />
            ))}
          </div>

          <div className="flex gap-2">
            <Button onClick={refreshAll} disabled={busy} className="h-11 flex-1 rounded-xl">
              최신으로 새로고침
            </Button>
          </div>
        </CardContent>
      </Card>
      ) : null}

      {activeSection === "operations" ? (
      <Card id="operations" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>빠른 운영 액션</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <Input value={newEventTitle} onChange={(e) => setNewEventTitle(e.target.value)} placeholder="새 행사 이름" />
            <Button onClick={createEvent} disabled={busy} className="h-11 rounded-xl">행사 만들기</Button>
          </div>

          {isTeamLead ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <Button variant="destructive" className="h-11 rounded-xl" onClick={deleteSelectedEvent} disabled={busy || !eventId}>
                선택 행사 삭제
              </Button>
              <Button variant="destructive" className="h-11 rounded-xl" onClick={deleteAllEvents} disabled={busy || events.length === 0}>
                전체 행사 삭제
              </Button>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-white p-3 text-xs text-muted-foreground">
              행사 삭제는 팀장 권한 계정에서만 가능합니다.
            </div>
          )}

          <div className="grid gap-2 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <p className="text-xs text-muted-foreground">조 개수</p>
              <Input inputMode="numeric" value={groupCount} onChange={(e) => setGroupCount(e.target.value)} placeholder="예: 5" />
            </div>
            <div className="grid gap-1.5">
              <p className="text-xs text-muted-foreground">조별 인원</p>
              <Input inputMode="numeric" value={groupCapacity} onChange={(e) => setGroupCapacity(e.target.value)} placeholder="예: 20" />
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            <Button variant="secondary" className="h-11 rounded-xl" onClick={runGrouping} disabled={busy || !eventId}>
              소그룹 자동 배정 실행
            </Button>
            <Button variant="secondary" className="h-11 rounded-xl" onClick={refreshAll} disabled={busy}>
              리포트 다시 계산
            </Button>
          </div>

          <div className="grid gap-2">
            <Input value={noticeTitle} onChange={(e) => setNoticeTitle(e.target.value)} placeholder="행사 공지 제목" />
            <Textarea value={noticeContent} onChange={(e) => setNoticeContent(e.target.value)} rows={3} placeholder="공지 내용" />
            <Button variant="secondary" className="h-11 rounded-xl" onClick={addNotice} disabled={busy}>
              행사 공지 등록
            </Button>
          </div>

          <div className="grid gap-2">
            <Input
              value={participantInfoTitle}
              onChange={(e) => setParticipantInfoTitle(e.target.value)}
              placeholder="참가자 안내 제목"
            />
            <Textarea
              value={participantInfoContent}
              onChange={(e) => setParticipantInfoContent(e.target.value)}
              rows={4}
              placeholder="참가자 콘솔의 행사 안내/등록 정보를 입력하세요."
            />
            <Button variant="secondary" className="h-11 rounded-xl" onClick={saveParticipantInfo} disabled={busy || !eventId}>
              참가자 안내 저장
            </Button>
          </div>
        </CardContent>
      </Card>
      ) : null}

      {isSuperAdmin && activeSection === "approvals" ? (
        <Card id="approvals" className="surface-soft rounded-2xl">
          <CardHeader>
            <CardTitle>사역팀 가입 승인</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {pendingApprovals.length ? (
              pendingApprovals.map((user) => (
                <div key={user.id} className="rounded-xl border border-border bg-white p-3">
                  <p className="text-sm font-semibold">{user.name} · {user.email}</p>
                  <p className="text-xs text-muted-foreground">요청 팀: {user.team ?? "-"}</p>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <Button className="h-9 rounded-lg" disabled={busy} onClick={() => decideApproval(user.id, true)}>승인</Button>
                    <Button variant="secondary" className="h-9 rounded-lg" disabled={busy} onClick={() => decideApproval(user.id, false)}>거절</Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">
                대기 중인 가입 요청이 없습니다.
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {isSuperAdmin && activeSection === "team-leads" ? (
        <Card id="team-leads" className="surface-soft rounded-2xl">
          <CardHeader>
            <CardTitle>팀장 지정/해제</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {ministryUsers.filter((user) => user.status === "approved").length ? (
              ministryUsers
                .filter((user) => user.status === "approved")
                .map((user) => (
                  <div key={`lead-${user.id}`} className="rounded-xl border border-border bg-white p-3">
                    <p className="text-sm font-semibold">{user.name} · {user.email}</p>
                    <p className="text-xs text-muted-foreground">팀: {user.team ?? "-"} · 현재: {user.is_team_lead ? "팀장" : "팀원"}</p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <Button
                        className="h-9 rounded-lg"
                        disabled={busy || user.is_team_lead}
                        onClick={() => decideTeamLead(user.id, true)}
                      >
                        팀장 지정
                      </Button>
                      <Button
                        variant="secondary"
                        className="h-9 rounded-lg"
                        disabled={busy || !user.is_team_lead}
                        onClick={() => decideTeamLead(user.id, false)}
                      >
                        팀장 해제
                      </Button>
                    </div>
                  </div>
                ))
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">
                승인된 사역팀 계정이 없습니다.
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {isTeamLead && activeSection === "refunds" ? (
        <>
          <Card id="refunds" className="surface-soft rounded-2xl">
            <CardHeader>
              <CardTitle>환불 요청 관리</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {refundRequests.length ? (
                refundRequests.map((row) => (
                  <div key={row.participant_id} className="rounded-xl border border-border bg-white p-3">
                    <p className="text-sm font-semibold">{row.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {row.church_or_school || "소속 미입력"} · 사유: {row.refund_reason || "사유 미입력"}
                    </p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <Button className="h-9 rounded-lg" disabled={busy} onClick={() => decideRefund(row.participant_id, true)}>
                        승인
                      </Button>
                      <Button
                        className="h-9 rounded-lg"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => decideRefund(row.participant_id, false)}
                      >
                        거절
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">
                  대기 중인 환불 요청이 없습니다.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="surface-soft rounded-2xl">
            <CardHeader>
              <CardTitle>환불 처리 이력</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2">
              {participantRows.filter((row) => row.refund_status === "approved" || row.refund_status === "rejected").length ? (
                participantRows
                  .filter((row) => row.refund_status === "approved" || row.refund_status === "rejected")
                  .slice(0, 20)
                  .map((row) => (
                    <div key={`history-${row.participant_id}`} className="rounded-xl border border-border bg-white px-3 py-2">
                      <p className="text-sm font-semibold">{row.name} · {row.church_or_school || "소속 미입력"}</p>
                      <p className="text-xs text-muted-foreground">
                        결과: {row.refund_status === "approved" ? "승인" : "거절"} · 처리자: {row.refund_processed_by || "-"} · 처리시각: {row.refund_processed_at || "-"}
                      </p>
                    </div>
                  ))
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-white p-4 text-sm text-muted-foreground">
                  환불 처리 이력이 없습니다.
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      {activeSection === "team" ? (
      <Card id="team" className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>팀 운영</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <p className="text-xs text-muted-foreground">보기 범위</p>
              <Select value={viewScope} onValueChange={(value) => setViewScope(value as TeamScope)}>
                <SelectTrigger>
                  <SelectValue placeholder="보기 범위 선택" />
                </SelectTrigger>
                <SelectContent>
                  {allowedViewScopeOptions.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <p className="text-xs text-muted-foreground">등록 범위</p>
              <Select value={createScope} onValueChange={(value) => setCreateScope(value as CreateScope)}>
                <SelectTrigger>
                  <SelectValue placeholder="등록 범위 선택" />
                </SelectTrigger>
                <SelectContent>
                  {allowedCreateScopeOptions.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <Input value={meetingTitle} onChange={(e) => setMeetingTitle(e.target.value)} placeholder="회의 제목" />
            <Button variant="secondary" onClick={addMeeting} disabled={busy} className="h-11 rounded-xl">
              <CalendarPlus className="mr-2 h-4 w-4" />회의 추가
            </Button>
          </div>

          <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
            <Input value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} placeholder="할 일" />
            <Button variant="secondary" onClick={addAction} disabled={busy} className="h-11 rounded-xl">
              할 일 추가
            </Button>
          </div>

          <div className="grid gap-2">
            <Input value={docTitle} onChange={(e) => setDocTitle(e.target.value)} placeholder="운영 노트 제목" />
            <Textarea value={docContent} onChange={(e) => setDocContent(e.target.value)} rows={3} placeholder="운영 메모" />
            <Button variant="secondary" onClick={addDoc} disabled={busy} className="h-11 rounded-xl">
              <FileText className="mr-2 h-4 w-4" />노트 저장
            </Button>
          </div>

          <div className="rounded-xl border border-dashed border-border bg-white px-3 py-2 text-xs text-muted-foreground">
            현재 보기: <span className="font-medium text-foreground">{scopeLabel(viewScope)}</span> · 등록 시 적용: <span className="font-medium text-foreground">{scopeLabel(createScope)}</span>
          </div>

          <div className="grid gap-2 sm:grid-cols-3">
            <InfoList title="최근 회의" items={meetingItems} />
            <InfoList title="할 일" items={actionItems} />
            <InfoList title="운영 노트" items={documentItems} />
          </div>
        </CardContent>
      </Card>
      ) : null}

      <Card className="rounded-2xl border-dashed bg-secondary/70">
        <CardContent className="py-4 text-sm text-muted-foreground">{log}</CardContent>
      </Card>
    </WorkspaceShell>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-white px-3 py-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <p className="text-xs">{label}</p>
      </div>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}

function InfoList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-border bg-white p-3">
      <p className="text-sm font-semibold">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
        {(items.length ? items.slice(0, 6) : ["아직 없음"]).map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function TeamStatusCard({
  label,
  meetingCount,
  openActionCount,
  docCount,
}: {
  label: string;
  meetingCount: number;
  openActionCount: number;
  docCount: number;
}) {
  return (
    <div className="rounded-xl border border-border bg-white p-3">
      <p className="text-sm font-semibold">{label}</p>
      <div className="mt-2 grid grid-cols-3 gap-1 text-center">
        <div className="rounded-md bg-secondary px-1 py-1.5">
          <p className="text-[10px] text-muted-foreground">회의</p>
          <p className="text-sm font-semibold">{meetingCount}</p>
        </div>
        <div className="rounded-md bg-secondary px-1 py-1.5">
          <p className="text-[10px] text-muted-foreground">할 일</p>
          <p className="text-sm font-semibold">{openActionCount}</p>
        </div>
        <div className="rounded-md bg-secondary px-1 py-1.5">
          <p className="text-[10px] text-muted-foreground">노트</p>
          <p className="text-sm font-semibold">{docCount}</p>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-white px-2 py-2 text-center">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-base font-semibold">{value}</p>
    </div>
  );
}
