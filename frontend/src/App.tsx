import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { Logo } from "@/components/mobile/Logo";
import { AppShell } from "@/views/mobile/AppShell";
import { SignIn } from "@/views/mobile/SignIn";
import { WorkspacePicker } from "@/views/mobile/WorkspacePicker";

/**
 * Vantage field app — routing gate.
 *   no session        → SignIn
 *   session, no cluster → WorkspacePicker (multi-tenancy: pick a field area)
 *   session + cluster   → AppShell (My Day / Messages / AI Chat / Profile)
 */
function Root() {
  const { ready, email, clusterId } = useAuth();

  if (!ready) {
    return (
      <div className="on-forest field-app items-center justify-center bg-forest-950">
        <Logo size={112} className="animate-pulse" />
      </div>
    );
  }
  if (!email) return <SignIn />;
  if (clusterId == null) return <WorkspacePicker email={email} />;
  return <AppShell clusterId={clusterId} />;
}

const App = () => (
  <AuthProvider>
    <Root />
  </AuthProvider>
);

export default App;
