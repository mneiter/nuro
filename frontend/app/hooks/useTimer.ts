"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  TimerResource,
  TimerTickResource,
  TimerStatus,
  cancelTimer as cancelTimerRequest,
  getProfile,
  listTimers,
  login as loginRequest,
  longPollTimer as longPollTimerRequest,
  register as registerRequest,
  startTimer as startTimerRequest
} from "../api/client";

const TOKEN_STORAGE_KEY = "nuro:token";
const TIMER_STORAGE_KEY = "nuro:timer";

export interface TimerTickState {
  id: string;
  label: string;
  status: TimerStatus;
  endsAt: string;
  remainingSeconds: number;
  etag: string;
  lastModified: string;
  lastSyncedAt: number;
}

interface Profile {
  id: string;
  email: string;
}

const isBrowser = () => typeof window !== "undefined";

function readStoredToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

function readStoredTimer(): TimerTickState | null {
  if (!isBrowser()) {
    return null;
  }
  const raw = window.localStorage.getItem(TIMER_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as TimerTickState;
    return parsed;
  } catch (error) {
    return null;
  }
}

function writeStoredTimer(timer: TimerTickState | null) {
  if (!isBrowser()) {
    return;
  }
  if (!timer) {
    window.localStorage.removeItem(TIMER_STORAGE_KEY);
  } else {
    window.localStorage.setItem(TIMER_STORAGE_KEY, JSON.stringify(timer));
  }
}

function writeStoredToken(token: string | null) {
  if (!isBrowser()) {
    return;
  }
  if (!token) {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } else {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

function normaliseTimer(resource: TimerResource | TimerTickResource): TimerTickState {
  return {
    id: resource.id,
    label: resource.label,
    status: resource.status,
    endsAt: resource.ends_at,
    remainingSeconds: resource.remaining_seconds,
    etag: resource.etag,
    lastModified: resource.last_modified,
    lastSyncedAt: Date.now()
  };
}

export default function useTimer() {
  const [token, setToken] = useState<string | null>(() => readStoredToken());
  const [profile, setProfile] = useState<Profile | null>(null);
  const [timer, setTimer] = useState<TimerTickState | null>(() => readStoredTimer());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const tokenRef = useRef<string | null>(token ?? null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    tokenRef.current = token;
    writeStoredToken(token);
    if (!token) {
      setProfile(null);
    }
  }, [token]);

  useEffect(() => {
    writeStoredTimer(timer);
  }, [timer]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message);
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError("Unexpected error");
    }
  }, []);

  const loadSession = useCallback(async () => {
    if (!tokenRef.current) {
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const [profileResponse, timersResponse] = await Promise.all([
        getProfile(tokenRef.current),
        listTimers(tokenRef.current)
      ]);
      if (!isMountedRef.current) {
        return;
      }
      setProfile(profileResponse);
      const running = timersResponse.find((item) => item.status === "running");
      const latest = running ?? timersResponse[0];
      if (latest) {
        setTimer(normaliseTimer(latest));
      } else {
        setTimer(null);
      }
    } catch (err) {
      handleError(err);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [handleError]);

  useEffect(() => {
    if (!token) {
      setTimer(null);
      return;
    }
    loadSession();
  }, [token, loadSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await loginRequest(email, password);
        setToken(response.access_token);
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await registerRequest(email, password);
        setToken(response.access_token);
      } catch (err) {
        handleError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const logout = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setToken(null);
    setTimer(null);
    setProfile(null);
    setError(null);
  }, []);

  const startPomodoro = useCallback(async () => {
    if (!tokenRef.current) {
      throw new Error("Not authenticated");
    }
    setLoading(true);
    setError(null);
    try {
      const resource = await startTimerRequest(tokenRef.current, 1500, "Pomodoro");
      const next = normaliseTimer(resource);
      setTimer(next);
      return next;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const cancelActiveTimer = useCallback(async () => {
    if (!tokenRef.current || !timer) {
      throw new Error("No timer to cancel");
    }
    setLoading(true);
    setError(null);
    try {
      const resource = await cancelTimerRequest(tokenRef.current, timer.id);
      const next = normaliseTimer(resource);
      setTimer(next);
      return next;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [handleError, timer]);

  useEffect(() => {
    if (!token || !timer || timer.status !== "running") {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    let active = true;

    const poll = async () => {
      let currentEtag: string | undefined = timer.etag;
      while (active && tokenRef.current) {
        try {
          const result = await longPollTimerRequest(tokenRef.current, timer.id, currentEtag, controller.signal);
          if (!active) {
            return;
          }
          if (result) {
            const next = normaliseTimer(result);
            currentEtag = next.etag;
            setTimer(next);
          }
        } catch (err) {
          if (controller.signal.aborted || !active) {
            return;
          }
          handleError(err);
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
      }
    };

    poll();

    return () => {
      active = false;
      controller.abort();
    };
  }, [handleError, timer, token]);

  const isAuthenticated = useMemo(() => Boolean(token), [token]);

  const clearError = useCallback(() => setError(null), []);

  return {
    token,
    profile,
    timer,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    startPomodoro,
    cancelActiveTimer,
    clearError
  };
}
