"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { AppFrame } from "@/components/shared/app-frame";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { BRAND_NAME } from "@/lib/brand";

export default function SignupPage() {
  const router = useRouter();
  const [accountType, setAccountType] = useState<"ministry" | "leader">("leader");
  const [leaderRole, setLeaderRole] = useState("teacher");
  const [team, setTeam] = useState("ops");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [church, setChurch] = useState("");
  const [log, setLog] = useState("학생 계정은 가입할 수 없습니다.");
  const [busy, setBusy] = useState(false);

  const teamLabel = useMemo(() => {
    return {
      ops: "운영팀",
      planning: "기획팀",
      education: "교육팀",
      life: "생활팀",
      promo: "홍보팀",
    }[team];
  }, [team]);

  async function submit() {
    try {
      setBusy(true);
      const payload: Record<string, unknown> = {
        account_type: accountType,
        name,
        email,
        password,
        church_or_school: church || null,
      };
      if (accountType === "leader") {
        payload.leader_role = leaderRole;
      }
      if (accountType === "ministry") {
        payload.team = team;
      }

      const res = await api<{ user: { status: string } }>("/api/auth/signup", {
        method: "POST",
        json: payload,
      });

      if (accountType === "ministry" && res.user.status === "pending") {
        setLog(`${teamLabel} 계정이 등록되었습니다. 승인 후 로그인할 수 있습니다.`);
      } else {
        setLog("회원가입이 완료되었습니다. 로그인해 주세요.");
      }
      router.replace("/login");
    } catch (error) {
      setLog(error instanceof Error ? error.message : "회원가입에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppFrame brand={BRAND_NAME} nav={[{ href: "/", label: "홈" }, { href: "/login", label: "로그인" }]}>
      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>회원가입</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-2">
            <Label>계정 유형</Label>
            <Select value={accountType} onValueChange={(v) => setAccountType(v as "ministry" | "leader")}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="leader">지도교사/전도사/목사</SelectItem>
                <SelectItem value="ministry">사역팀</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {accountType === "leader" ? (
            <div className="grid gap-2">
              <Label>지도자 구분</Label>
              <Select value={leaderRole} onValueChange={setLeaderRole}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="teacher">지도교사</SelectItem>
                  <SelectItem value="evangelist">전도사</SelectItem>
                  <SelectItem value="pastor">목사</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="grid gap-2">
              <Label>사역팀</Label>
              <Select value={team} onValueChange={setTeam}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ops">운영팀</SelectItem>
                  <SelectItem value="planning">기획팀</SelectItem>
                  <SelectItem value="education">교육팀</SelectItem>
                  <SelectItem value="life">생활팀</SelectItem>
                  <SelectItem value="promo">홍보팀</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <Field label="이름" value={name} setValue={setName} />
          <Field label="이메일" value={email} setValue={setEmail} />
          <Field label="비밀번호" value={password} setValue={setPassword} type="password" />
          <Field label="교회/학교" value={church} setValue={setChurch} />

          <Button className="h-11 rounded-xl" onClick={submit} disabled={busy}>회원가입</Button>
          <p className="text-sm text-muted-foreground">{log}</p>
          <p className="text-sm text-muted-foreground">
            이미 계정이 있다면 <Link href="/login" className="underline">로그인</Link>
          </p>
        </CardContent>
      </Card>
    </AppFrame>
  );
}

function Field({
  label,
  value,
  setValue,
  type,
}: {
  label: string;
  value: string;
  setValue: (v: string) => void;
  type?: "text" | "password";
}) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Input type={type ?? "text"} value={value} onChange={(e) => setValue(e.target.value)} />
    </div>
  );
}
