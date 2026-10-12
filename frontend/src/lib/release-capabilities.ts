import { useEffect, useState } from 'react';
export interface ReleaseCapabilities { billing: boolean; crm: boolean; channels: boolean; integrations: boolean }
const available = { billing: true, crm: true, channels: true, integrations: true };
const unavailable = { billing: false, crm: false, channels: false, integrations: false };
export function useReleaseCapabilities(): ReleaseCapabilities {
  const [value, setValue] = useState(import.meta.env.PROD ? unavailable : available);
  useEffect(() => {
    if (!import.meta.env.PROD) return;
    let active = true;
    void fetch('/api/v1/release/capabilities', { cache: 'no-store' }).then(async response => {
      if (!response.ok) return;
      const data = await response.json() as Record<string, unknown>;
      if (active) setValue({ billing: data.billing === true, crm: data.crm === true,
                           channels: data.channels === true, integrations: data.integrations === true });
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  return value;
}
