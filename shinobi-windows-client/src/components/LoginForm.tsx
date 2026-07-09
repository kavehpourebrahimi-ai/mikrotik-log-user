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
  const [serverLabel, setServerLabel] = useState("Production Shinobi");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await login(serverUrl, mail, password);
    addSavedServer({ label: serverLabel, url: serverUrl });
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="brand-block">
          <p className="eyebrow">Enterprise VMS Client</p>
          <h1>Shinobi Client</h1>
          <p>
            Connect to your Linux Shinobi server for live view, playback, and
            operator workflows without running the NVR on Windows.
          </p>
        </div>

        <label>
          Server URL
          <input
            value={serverUrl}
            onChange={(event) => setServerUrl(event.target.value)}
            placeholder="https://shinobi.example.com:8080"
            required
          />
        </label>

        <label>
          Server Label
          <input
            value={serverLabel}
            onChange={(event) => setServerLabel(event.target.value)}
            placeholder="Production Shinobi"
          />
        </label>

        <label>
          Email
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
          {status === "connecting" ? "Connecting..." : "Connect"}
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
