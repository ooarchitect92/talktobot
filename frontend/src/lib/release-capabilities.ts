import { useEffect, useState } from 'react';
export interface ReleaseCapabilities { billing: boolean; crm: boolean; channels: boolean; integrations: boolean; providers?: Partial<Record<'telegram' | 'zoho', boolean>> }
const available = { billing: true, crm: true, channels: true, integrations: true, providers: { telegram: true, zoho: true } };
const unavailable = { billing: false, crm: false, channels: false, integrations: false, providers: { telegram: false, zoho: false } };
export function useReleaseCapabilities(): ReleaseCapabilities {
  const [value, setValue] = useState(import.meta.env.PROD ? unavailable : available);
  useEffect(() => {
    if (!import.meta.env.PROD) return;
    let active = true;
    void fetch('/api/v1/release/capabilities', { cache: 'no-store' }).then(async response => {
      if (!response.ok) return;
      const data = await response.json() as Record<string, unknown>;
      const providers = data.providers as Record<string, unknown> | undefined;
      if (active) setValue({ billing: data.billing === true, crm: data.crm === true,
                           channels: data.channels === true, integrations: data.integrations === true,
                           providers: { telegram: providers?.telegram === true, zoho: providers?.zoho === true } });
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  return value;
}
