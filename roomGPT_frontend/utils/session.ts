import { getCurrentUser } from "./auth";

const SESSION_STORAGE_KEY = "lumiere-current-session-id";

function getSessionStorageKey(): string {
  if (typeof window === "undefined") {
    return SESSION_STORAGE_KEY;
  }
  const email = (getCurrentUser()?.email || "").trim().toLowerCase();
  if (!email) {
    return SESSION_STORAGE_KEY;
  }
  return `${SESSION_STORAGE_KEY}:${email}`;
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getCurrentSessionId(): string {
  if (typeof window === "undefined") {
    return "main_session";
  }

  const storageKey = getSessionStorageKey();
  const existing = window.localStorage.getItem(storageKey);
  if (existing) {
    return existing;
  }

  const sessionId = createSessionId();
  window.localStorage.setItem(storageKey, sessionId);
  return sessionId;
}

export function setCurrentSessionId(sessionId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const storageKey = getSessionStorageKey();
  window.localStorage.setItem(storageKey, sessionId);
}

export function createAndStoreSessionId(): string {
  const sessionId = createSessionId();
  setCurrentSessionId(sessionId);
  return sessionId;
}
