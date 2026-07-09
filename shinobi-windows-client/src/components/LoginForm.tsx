import { FormEvent, useState } from "react";
import { useSessionStore } from "../store/session";

export function LoginForm() {
  const login = useSessionStore((state) => state.login);
  const addSavedServer = useSessionStore((state) => state.addSavedServer);
  const savedServers = useSessionStore((state) => state.savedServers);
  const status = useSessionStore((state) => state.status);
  const error = useSessionStore((state) => state.error);

  const [serverUrl, setServerUrl] = useState(
    savedServers[0]?.url ?? "http://127.0.0.1:8080",
  );
  const [mail, setMail] = useState("");
  const [password, setPassword] = useState("");
  const [serverLabel, setServerLabel] = useState("Operations Center");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await login(serverUrl, mail, password);
    addSavedServer({ label: serverLabel, url: serverUrl });
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="brand-block">
          <p className="eyebrow">Security Operations Client</p>
          <h1>Shinobi Operator Desk</h1>
          <p>
            Lightweight Windows client for security guards and control-room
            operators. The Shinobi server records on Linux. This workstation only
            monitors, reviews, and manages.
          </p>
        </div>

        <label>
          Shinobi Server URL
          <input
            value={serverUrl}
            onChange={(event) => setServerUrl(event.target.value)}
            placeholder="https://shinobi.example.com:8080"
            required
          />
        </label>

        <label>
          Site Label
          <input
            value={serverLabel}
            onChange={(event) => setServerLabel(event.target.value)}
            placeholder="Operations Center"
          />
        </label>

        <label>
          Operator Email
          <input
            type="email"
            value={mail}
            onChange={(event) => setMail(event.target.value)}
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <button type="submit" disabled={status === "connecting"}>
          {status === "connecting" ? "Connecting..." : "Enter Control Room"}
        </button>

        {savedServers.length > 0 ? (
          <div className="saved-servers">
            <span>Saved servers</span>
            <div className="saved-server-list">
              {savedServers.map((server) => (
                <button
                  key={server.url}
                  type="button"
                  className="saved-server-chip"
                  onClick={() => setServerUrl(server.url)}
                >
                  {server.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </form>
    </div>
  );
}
