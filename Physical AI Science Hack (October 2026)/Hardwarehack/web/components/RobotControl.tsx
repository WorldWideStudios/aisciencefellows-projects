"use client";
// Robot connection in the header: shows where brews go, and lets you switch robot or mock.
import { useEffect, useState } from "react";
import { api, type RobotConfig } from "@/lib/api";

export default function RobotControl({ onChange }: { onChange: () => void }) {
  const [config, setConfig] = useState<RobotConfig | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [open, setOpen] = useState(false);

  const check = async () => {
    try {
      const h = await api.health();
      setStatus({ ok: true, text: h.name ?? "robot" });
    } catch (e) {
      setStatus({ ok: false, text: (e as Error).message });
    }
  };
  useEffect(() => {
    api.robotConfig().then((c) => { setConfig(c); void check(); }).catch((e: Error) => setStatus({ ok: false, text: e.message }));
  }, []);

  const save = async () => {
    if (!config) return;
    try {
      setConfig(await api.setRobotConfig(config));
      await check();
      setOpen(false);
      onChange();
    } catch (e) {
      setStatus({ ok: false, text: (e as Error).message });
    }
  };

  const label = !config ? "Connecting…" : config.mock ? "Mock robot" : config.host || "No robot set";
  return (
    <div className="relative">
      <button className="btn" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className={`size-2 rounded-full ${status?.ok ? "bg-leaf" : "bg-alert"}`} aria-hidden="true" />
        {label}
      </button>
      {open && config && (
        <div className="absolute right-0 z-30 mt-2 w-72 rounded-lg border border-mithril bg-raised p-4 shadow-lg shadow-black" role="dialog" aria-label="Robot connection">
          <label className="mb-2 block text-sm">
            Robot address
            <input className="field mt-1" placeholder="192.168.0.42" value={config.host} disabled={config.mock}
                   onChange={(e) => setConfig({ ...config, host: e.target.value.trim() })} />
          </label>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={config.mock} onChange={(e) => setConfig({ ...config, mock: e.target.checked })} />
            Mock robot, for working away from the lab
          </label>
          {status && <p className={`mb-3 text-xs ${status.ok ? "text-leaf" : "text-alert"}`}>{status.ok ? `Connected to ${status.text}` : status.text}</p>}
          <div className="flex justify-end gap-2">
            <button className="btn btn-quiet" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={save}>Connect</button>
          </div>
        </div>
      )}
    </div>
  );
}
