import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight, Building2, HeartPulse, LockKeyhole, Mail, ShieldCheck, UserRound, UsersRound,
} from "lucide-react";
import { ROLE_META, useRole } from "@/lib/role";

const ROLE_OPTIONS = [
  { key: "officer", icon: ShieldCheck },
  { key: "hospital", icon: HeartPulse },
  { key: "labour", icon: Building2 },
  { key: "citizen", icon: UserRound },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const { setRole } = useRole();
  const [selectedRole, setSelectedRole] = useState("officer");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const signIn = (event) => {
    event.preventDefault();
    setRole(selectedRole);
    navigate(ROLE_META[selectedRole].home);
  };

  return (
    <div className="min-h-[calc(100vh-3rem)] overflow-hidden rounded-3xl bg-slate-950 text-white shadow-2xl">
      <div className="grid min-h-[680px] lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative flex flex-col justify-between overflow-hidden px-6 py-10 sm:px-12 lg:px-16">
          <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full border-[36px] border-orange-500/10" />
          <div className="pointer-events-none absolute -bottom-40 -left-20 h-96 w-96 rounded-full border-[48px] border-red-500/10" />
          <div className="relative">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-500">
                <ShieldCheck className="h-6 w-6" />
              </span>
              <div>
                <p className="text-sm font-bold tracking-[0.18em]">HEATSHIELD INDIA</p>
                <p className="text-xs text-slate-400">Heat-health early warning system</p>
              </div>
            </div>
            <div className="mt-24 max-w-xl">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-orange-300">Mysore command network</p>
              <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
                Read the heat.<br /><span className="text-orange-400">Protect people.</span>
              </h1>
              <p className="mt-6 max-w-md text-sm leading-7 text-slate-300">
                One shared view of thermal stress, ward vulnerability, health risk and the action needed next.
              </p>
            </div>
          </div>
          <div className="relative mt-16 flex items-center gap-3 text-xs text-slate-400">
            <UsersRound className="h-4 w-4 text-orange-400" />
            <span>Secure role-based access for city response teams and citizens</span>
          </div>
        </section>

        <section className="bg-white px-6 py-10 text-slate-900 sm:px-12 lg:px-14">
          <div className="mx-auto max-w-md">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-600">Welcome back</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight">Sign in to HeatShield</h2>
            <p className="mt-2 text-sm text-slate-500">Choose your access profile to continue.</p>

            <div className="mt-8 grid gap-2 sm:grid-cols-2">
              {ROLE_OPTIONS.map(({ key, icon: Icon }) => {
                const active = selectedRole === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedRole(key)}
                    className={`flex min-h-16 items-center gap-3 rounded-xl border p-3 text-left transition ${active ? "border-orange-500 bg-orange-50 ring-2 ring-orange-100" : "border-slate-200 bg-white hover:border-slate-400"}`}
                  >
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${active ? "bg-orange-500 text-white" : "bg-slate-100 text-slate-500"}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="text-xs font-semibold leading-4">{ROLE_META[key].label}</span>
                  </button>
                );
              })}
            </div>

            <form className="mt-8 space-y-4" onSubmit={signIn}>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">Email address</span>
                <span className="relative block">
                  <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                  <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
                </span>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">Password</span>
                <span className="relative block">
                  <LockKeyhole className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
                  <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
                </span>
              </label>
              <button type="submit" className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-slate-950 text-sm font-semibold text-white transition hover:bg-orange-600">
                Continue as {ROLE_META[selectedRole].short}
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>

            <p className="mt-5 rounded-lg bg-amber-50 px-3 py-2.5 text-center text-[11px] leading-5 text-amber-800">
              Demo mode: any valid email and password will open the selected workspace.
            </p>
            <p className="mt-8 text-center text-[11px] text-slate-400">By continuing, you agree to use HeatShield for decision support only.</p>
          </div>
        </section>
      </div>
    </div>
  );
}