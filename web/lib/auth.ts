import { api } from "@/lib/api";

export type AccountType = "ministry" | "leader";
export type UserStatus = "pending" | "approved" | "rejected";

export type SessionUser = {
  id: string;
  email: string;
  name: string;
  account_type: AccountType;
  leader_role: string | null;
  church_or_school: string | null;
  team: string | null;
  status: UserStatus;
  can_approve: boolean;
  is_team_lead: boolean;
  profile_image_url: string | null;
  is_super_admin: boolean;
};

const TOKEN_KEY = "dodream_auth_token";
const USER_CACHE_KEY = "dodream_auth_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_CACHE_KEY);
}

export function getCachedUser(): SessionUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_CACHE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function setCachedUser(user: SessionUser): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
}

export async function fetchMe(): Promise<SessionUser> {
  const res = await api<{ user: SessionUser }>("/api/auth/me");
  setCachedUser(res.user);
  return res.user;
}

export async function logout(): Promise<void> {
  await api("/api/auth/logout", { method: "POST" });
  clearToken();
}

export function canAccessAdmin(user: SessionUser): boolean {
  return user.account_type === "ministry" && user.status === "approved";
}

export function canAccessLeader(user: SessionUser): boolean {
  return user.account_type === "leader" || canAccessAdmin(user);
}

export function canAccessField(user: SessionUser): boolean {
  return canAccessAdmin(user);
}
