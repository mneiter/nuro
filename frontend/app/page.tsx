"use client";

import { FormEvent, useState } from "react";

import TimerDisplay from "./components/TimerDisplay";
import useTimer from "./hooks/useTimer";

export default function HomePage() {
  const {
    timer,
    profile,
    isAuthenticated,
    loading,
    error,
    login,
    register,
    logout,
    startPomodoro,
    cancelActiveTimer,
    clearError
  } = useTimer();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    clearError();
    if (!email || !password) {
      return;
    }
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      setPassword("");
    } catch (err) {
      console.error(err);
    }
  };

  const toggleMode = () => {
    setMode((prev) => (prev === "login" ? "register" : "login"));
    clearError();
  };

  const handleStart = async () => {
    try {
      await startPomodoro();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCancel = async () => {
    try {
      await cancelActiveTimer();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <main>
      <div className="container">
        <header>
          <h1>Nuro Focus</h1>
          <p>Your Pomodoro companion.</p>
        </header>

        {!isAuthenticated ? (
          <form onSubmit={handleSubmit}>
            <label>
              Email
              <input
                autoComplete="email"
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {error ? <div className="alert">{error}</div> : null}
            <button className="primary" disabled={loading} type="submit">
              {loading ? "Please wait." : mode === "login" ? "Sign in" : "Create account"}
            </button>
            <div className="toggle-auth">
              <span>{mode === "login" ? "Need an account?" : "Already have an account?"} </span>
              <button type="button" onClick={toggleMode}>
                {mode === "login" ? "Register" : "Sign in"}
              </button>
            </div>
          </form>
        ) : (
          <>
            <TimerDisplay timer={timer} />
            <div className="status">
              <span>
                Logged in as <strong>{profile?.email ?? email}</strong>
              </span>
              <button className="secondary" type="button" onClick={logout}>
                Logout
              </button>
            </div>
            {error ? <div className="alert">{error}</div> : null}
            <div className="actions">
              <button className="primary" disabled={loading} type="button" onClick={handleStart}>
                {loading && timer?.status === "running" ? "Updating." : "Start 25 minutes"}
              </button>
              <button
                className="secondary"
                disabled={!timer || timer.status !== "running" || loading}
                type="button"
                onClick={handleCancel}
              >
                Cancel
              </button>
            </div>
          </>
        )}

        <footer>Timers sync automatically thanks to the FastAPI long-poll API.</footer>
      </div>
    </main>
  );
}
