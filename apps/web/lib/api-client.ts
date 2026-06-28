export type Idea = {
  id: string;
  title: string;
  thesis: string;
  created_at: string;
};

export type StrategyStatus =
  | "Draft"
  | "Backtested"
  | "Paper Trading"
  | "Live Small Size"
  | "Live Full Size"
  | "Paused"
  | "Retired";

export type Strategy = {
  id: string;
  name: string;
  status: StrategyStatus;
  source_idea_id: string | null;
  description: string;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  actor: string;
  action: string;
  subject: string;
  created_at: string;
};

export type IdeaCreate = {
  title: string;
  thesis: string;
};

export type StrategyCreate = {
  name: string;
  source_idea_id?: string | null;
  description: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getIdeas(): Promise<Idea[]> {
  const body = await request<{ ideas: Idea[] }>("/ideas");
  return body.ideas;
}

export async function createIdea(payload: IdeaCreate): Promise<Idea> {
  return request<Idea>("/ideas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getStrategies(): Promise<Strategy[]> {
  const body = await request<{ strategies: Strategy[] }>("/strategies");
  return body.strategies;
}

export async function createStrategy(payload: StrategyCreate): Promise<Strategy> {
  return request<Strategy>("/strategies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAuditEvents(): Promise<AuditEvent[]> {
  const body = await request<{ audit_events: AuditEvent[] }>("/audit-events");
  return body.audit_events;
}
