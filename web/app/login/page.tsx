"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppFrame } from "@/components/shared/app-frame";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { canAccessAdmin, canAccessLeader, setToken, type SessionUser } from "@/lib/auth";
import { BRAND_NAME } from "@/lib/brand";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [log, setLog] = useState("로그인 후 권한에 맞는 콘솔로 이동합니다.");
  const [busy, setBusy] = useState(false);

  async function submit() {
    try {
      setBusy(true);
      const res = await api<{ token: string; user: SessionUser }>("/api/auth/login", {
        method: "POST",
        json: { email, password },
      });
      setToken(res.token);

      if (canAccessAdmin(res.user)) {
        router.replace("/admin");
        return;
      }
      if (canAccessLeader(res.user)) {
        router.replace("/leader");
        return;
      }
      router.replace("/");
    } catch (error) {
      setLog(error instanceof Error ? error.message : "로그인에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppFrame brand={BRAND_NAME} nav={[{ href: "/", label: "홈" }, { href: "/signup", label: "회원가입" }]}>
      <Card className="surface-soft rounded-2xl">
        <CardHeader>
          <CardTitle>로그인</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-2">
            <Label>이메일</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
          </div>
          <div className="grid gap-2">
            <Label>비밀번호</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button className="h-11 rounded-xl" onClick={submit} disabled={busy}>로그인</Button>
          <p className="text-sm text-muted-foreground">{log}</p>
          <p className="text-sm text-muted-foreground">
            계정이 없다면 <Link href="/signup" className="underline">회원가입</Link>을 진행해 주세요.
          </p>
        </CardContent>
      </Card>
    </AppFrame>
  );
}
