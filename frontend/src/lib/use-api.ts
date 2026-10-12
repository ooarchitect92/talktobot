import { useCallback, useEffect, useState } from 'react';

export interface AsyncState<T> { data: T | null; loading: boolean; error: string | null; reload: () => void }

export function useApi<T>(loader: () => Promise<T>, dependencies: readonly unknown[] = []): AsyncState<T> {
  const [revision, setRevision] = useState(0);
  // Derive pending state synchronously so previous workspace data is never
  // returned during the render before an effect starts the next request.
  const [identity, setIdentity] = useState(() => ({ dependencies: [...dependencies], revision, request: Symbol('api-request') }));
  let currentIdentity = identity;
  if (identity.revision !== revision || identity.dependencies.length !== dependencies.length
    || dependencies.some((value, index) => !Object.is(value, identity.dependencies[index]))) {
    // React discards this render and retries with the new request identity
    // before children commit, so an old workspace response cannot be displayed.
    const next = { dependencies: [...dependencies], revision, request: Symbol('api-request') };
    setIdentity(next);
    currentIdentity = next;
  }
  const request = currentIdentity.request;
  const [snapshot, setSnapshot] = useState<{ request: symbol; data: T | null; error: string | null } | null>(null);
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    let active = true;
    void loader().then((data) => { if (active) setSnapshot({ request, data, error: null }); })
      .catch((reason: unknown) => { if (active) setSnapshot({ request, data: null, error: reason instanceof Error ? reason.message : 'Something went wrong' }); });
    return () => { active = false; };
    // The caller controls when the loader should be re-run through dependencies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);
  const current = snapshot?.request === request ? snapshot : null;
  return { data: current?.data ?? null, loading: current === null, error: current?.error ?? null, reload };
}
