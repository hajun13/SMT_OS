const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type EventSummary = {
  id: string;
  slug: string;
  title: string;
  template: string;
  capacity?: number;
};

export type ParticipantRow = {
  participant_id: string;
  name: string;
  church_or_school: string | null;
  grade: string | null;
  participant_role: string | null;
  phone: string | null;
  registration_fee_paid: boolean | null;
  refund_requested: boolean | null;
  refund_status: string | null;
  refund_reason: string | null;
  refund_processed_by: string | null;
  refund_processed_at: string | null;
  ticket_status: string | null;
};

type RequestInitWithJson = RequestInit & { json?: unknown };

function readAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("dodream_auth_token");
}

export async function api<T>(path: string, init: RequestInitWithJson = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const body = init.json !== undefined ? JSON.stringify(init.json) : init.body;

  if (init.json !== undefined && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const token = readAuthToken();
  if (token && !headers.has("authorization")) {
    headers.set("authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    throw new Error("서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : `요청 실패 (${response.status})`;
    throw new Error(detail);
  }

  return data as T;
}

export const roleHeader = (role: string) => ({ "x-role": role });
