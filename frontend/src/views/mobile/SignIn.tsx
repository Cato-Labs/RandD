import { useRef, useState } from "react";
import { ArrowRightIcon, KeyRoundIcon } from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { Logo } from "@/components/mobile/Logo";
import { Eyebrow } from "@/components/mobile/bits";
import { cn } from "@/lib/utils";

/**
 * Field access — email then a one-time passcode. No backend auth exists on
 * this branch, so any well-formed email + a 4+ digit code signs in; the flow
 * and its states are the real deliverable and map cleanly onto a magic-code
 * endpoint later.
 */
export function SignIn() {
  const { signIn } = useAuth();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const codeRef = useRef<HTMLInputElement>(null);

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const codeValid = code.replace(/\D/g, "").length >= 4;

  async function sendCode(e: React.FormEvent) {
    e.preventDefault();
    if (!emailValid) {
      setError("Enter a valid work email.");
      return;
    }
    setError(null);
    setBusy(true);
    await new Promise((r) => setTimeout(r, 450));
    setBusy(false);
    setStep("code");
    requestAnimationFrame(() => codeRef.current?.focus());
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    if (!codeValid) {
      setError("Enter the 6-digit code we sent you.");
      return;
    }
    setError(null);
    setBusy(true);
    await signIn(email);
    // AuthProvider flips the app to the workspace picker on the next render.
  }

  return (
    <div className="on-forest field-app justify-between bg-forest-950 px-7 pb-10 pt-14 text-sage-200">
      {/* Wordmark */}
      <header className="flex items-center gap-3">
        <Logo size={38} />
        <span className="font-display text-xl tracking-tight text-cream">Vantage</span>
      </header>

      {/* Hero */}
      <div className="flex flex-col items-start">
        <div className="mb-8 self-center">
          <Logo size={124} />
        </div>
        <Eyebrow className="text-gold-300">Field access</Eyebrow>
        <h1 className="mt-3 font-display text-[clamp(2rem,9vw,2.7rem)] leading-[1.05] tracking-tight text-cream">
          {step === "email" ? (
            <>Welcome back to the field.</>
          ) : (
            <>Check your inbox.</>
          )}
        </h1>
        <p className="muted mt-3 max-w-xs text-[0.95rem] leading-relaxed text-sage-300">
          {step === "email"
            ? "Sign in with your work email and Vantage will walk today with you — property by property."
            : `We sent a 6-digit code to ${email}. Enter it to continue.`}
        </p>
      </div>

      {/* Form */}
      <div>
        {step === "email" ? (
          <form onSubmit={sendCode} className="flex flex-col gap-3">
            <label className="flex flex-col gap-2">
              <span className="eyebrow text-sage-300">Work email</span>
              <input
                autoComplete="email"
                autoFocus
                className="h-14 rounded-2xl border border-forest-700 bg-forest-900 px-4 text-base text-cream placeholder:text-sage-400"
                inputMode="email"
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                type="email"
                value={email}
              />
            </label>
            {error && <p className="text-sm text-[#f0a3a0]">{error}</p>}
            <SubmitButton busy={busy} disabled={!emailValid}>
              Send sign-in code
              <ArrowRightIcon className="size-4" />
            </SubmitButton>
          </form>
        ) : (
          <form onSubmit={verify} className="flex flex-col gap-3">
            <label className="flex flex-col gap-2">
              <span className="eyebrow text-sage-300">One-time code</span>
              <input
                autoComplete="one-time-code"
                className="h-14 rounded-2xl border border-forest-700 bg-forest-900 px-4 text-center text-2xl tracking-[0.5em] text-cream placeholder:tracking-normal placeholder:text-sage-400"
                inputMode="numeric"
                maxLength={6}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="······"
                ref={codeRef}
                value={code}
              />
            </label>
            {error && <p className="text-sm text-[#f0a3a0]">{error}</p>}
            <SubmitButton busy={busy} disabled={!codeValid}>
              <KeyRoundIcon className="size-4" />
              Enter the field
            </SubmitButton>
            <button
              className="mx-auto mt-1 text-sm text-sage-300 underline-offset-4 hover:underline"
              onClick={() => {
                setStep("email");
                setCode("");
                setError(null);
              }}
              type="button"
            >
              Use a different email
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function SubmitButton({
  children,
  busy,
  disabled,
}: {
  children: React.ReactNode;
  busy: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      className={cn(
        "mt-1 inline-flex h-14 items-center justify-center gap-2 rounded-2xl bg-gold px-5 text-base font-semibold text-[#231a06] transition-all",
        "hover:bg-gold-300 disabled:cursor-not-allowed disabled:opacity-45"
      )}
      disabled={disabled || busy}
      type="submit"
    >
      {busy ? "One moment…" : children}
    </button>
  );
}
