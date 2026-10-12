let interactiveSession: unknown = null;
const memoryOnlySessions = import.meta.env.PROD;

export function readStorage<T>(key: string, fallback: T): T {
  if (key === 'northstar.session' && memoryOnlySessions) {
    try { localStorage.removeItem(key); } catch { /* Restricted storage. */ }
    return (interactiveSession as T | null) ?? fallback;
  }
  try {
    const value = localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeStorage<T>(key: string, value: T): void {
  if (key === 'northstar.session' && memoryOnlySessions) {
    interactiveSession = value;
    try { localStorage.removeItem(key); } catch { /* Restricted storage. */ }
    return;
  }
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private browsing / quota */ }
}

export function removeStorage(key: string): void {
  if (key === 'northstar.session') interactiveSession = null;
  try { localStorage.removeItem(key); } catch { /* Restricted storage. */ }
}

export const clone = <T>(value: T): T => structuredClone(value);
