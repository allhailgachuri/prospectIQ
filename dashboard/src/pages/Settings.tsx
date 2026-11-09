import { Moon, Sun, ExternalLink, Database, ShieldCheck } from "lucide-react";

export function Settings({
  theme,
  onThemeChange,
}: {
  theme: "light" | "dark";
  onThemeChange: (theme: "light" | "dark") => void;
}) {
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Settings</h1>
          <p>Manage your ProspectIQ workspace preferences.</p>
        </div>
      </header>

      <section className="settings-section">
        <div className="settings-icon">
          <Sun size={18} />
        </div>
        <div className="settings-copy">
          <h2>Appearance</h2>
          <p>Choose the display mode for this browser.</p>
        </div>
        <div className="segmented-control" role="group" aria-label="Appearance">
          <button
            type="button"
            aria-pressed={theme === "light"}
            onClick={() => onThemeChange("light")}
          >
            <Sun size={14} /> Light
          </button>
          <button
            type="button"
            aria-pressed={theme === "dark"}
            onClick={() => onThemeChange("dark")}
          >
            <Moon size={14} /> Dark
          </button>
        </div>
      </section>

      <section className="settings-section">
        <div className="settings-icon">
          <Database size={18} />
        </div>
        <div className="settings-copy">
          <h2>Data sources</h2>
          <p>
            Business discovery currently uses OpenStreetMap via its public
            Overpass API. Coverage depends on mapped data and public service
            availability.
          </p>
        </div>
        <a
          className="text-link"
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
        >
          OSM terms <ExternalLink size={13} />
        </a>
      </section>

      <section className="settings-section">
        <div className="settings-icon">
          <ShieldCheck size={18} />
        </div>
        <div className="settings-copy">
          <h2>Responsible research</h2>
          <p>
            Use publicly listed business details, respect source terms and
            opt-outs, verify records before outreach, and comply with applicable
            data-protection rules.
          </p>
        </div>
      </section>
    </div>
  );
}
