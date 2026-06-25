import React, { useEffect, useRef, useCallback } from "react";
import { useGoogleAuth } from "../../lib/useGoogleAuth";
import type { GoogleProfile } from "../../lib/useGoogleAuth";

interface GoogleLoginButtonProps {
  clientId: string;
  onSuccess: (token: string, profile: GoogleProfile) => Promise<void>;
  onError?: (error: string) => void;
  mode?: "signin" | "signup";
  className?: string;
}

export const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({
  clientId,
  onSuccess,
  onError,
  mode = "signin",
  className = "",
}) => {
  const containerId = useRef(
    `gsi-${Math.random().toString(36).slice(2, 10)}`,
  ).current;
  const mounted = useRef(false);
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);

  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const { loading, error, initGoogleButton, handleCredential } =
    useGoogleAuth(clientId);

  useEffect(() => {
    return () => {
      mounted.current = false;
    };
  }, []);

  const onCredential = useCallback(
    (credential: string) => {
      handleCredential(
        credential,
        async (token: string, profile: GoogleProfile) => {
          await onSuccessRef.current(token, profile);
        },
        `Google ${mode === "signup" ? "sign-up" : "sign-in"} failed. Please try email ${mode === "signup" ? "signup" : "login"}.`,
      );
    },
    [handleCredential, mode],
  );

  useEffect(() => {
    if (!clientId || mounted.current) return;
    mounted.current = true;

    initGoogleButton(containerId, onCredential, {
      text: mode === "signup" ? "signup_with" : "continue_with",
    });
  }, [clientId, containerId, initGoogleButton, onCredential, mode]);

  useEffect(() => {
    if (error && onErrorRef.current) {
      onErrorRef.current(error);
    }
  }, [error]);

  if (!clientId) {
    console.warn("[GoogleLoginButton] No clientId provided — Google Sign-In button will not render.");
    return null;
  }

  if (loading) {
    return (
      <div
        className={`w-full flex items-center justify-center py-3 text-sm text-slate-500 bg-slate-50 dark:bg-slate-800 rounded-xl ${className}`}
        role="status"
        aria-label={
          mode === "signup" ? "Signing up with Google" : "Signing in with Google"
        }
      >
        {mode === "signup"
          ? "Signing up with Google..."
          : "Signing in with Google..."}
      </div>
    );
  }

  return (
    <div className={className}>
      <div id={containerId} className="w-full flex justify-center" />
      {error && (
        <div
          className="mt-2 p-3 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg"
          role="alert"
        >
          {error}
        </div>
      )}
    </div>
  );
};
