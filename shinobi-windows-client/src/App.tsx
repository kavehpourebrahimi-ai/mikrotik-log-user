import { useSessionStore } from "./store/session";
import { LoginForm } from "./components/LoginForm";
import { Shell } from "./components/Shell";
import "./App.css";

function App() {
  const session = useSessionStore((state) => state.session);

  return session ? <Shell /> : <LoginForm />;
}

export default App;
