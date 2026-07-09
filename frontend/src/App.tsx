import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { Logo } from "@/components/mobile/Logo";
import { AppShell } from "@/views/mobile/AppShell";
import { SignIn } from "@/views/mobile/SignIn";
import { WorkspacePicker } from "@/views/mobile/WorkspacePicker";

/**
 * Vantage field app — routing gate.
 *   no session        → SignIn
 *   session, no tenant → WorkspacePicker (multi-tenancy)
 *   session + tenant   → AppShell (My Day / Messages / AI Chat / Profile)
 */
function Root() {
  const { ready, user, workspaceId } = useAuth();

  if (!ready) {
    return (
      <div className="on-forest field-app items-center justify-center bg-forest-950">
        <Logo size={112} className="animate-pulse" />
      </div>
    );
  }
  if (!user) return <SignIn />;
  if (!workspaceId) return <WorkspacePicker user={user} />;
  return <AppShell workspaceId={workspaceId} />;
}

const App = () => (
  <AuthProvider>
    <Root />
  </AuthProvider>
);

export default App;
