import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "../api";

interface GoogleInitConfig {
  client_id: string;
  callback: (response: { credential: string }) => void;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
  context?: "signin" | "signup" | "use";
  itp_support?: boolean;
  login_uri?: string;
  nonce?: string;
  prompt_parent_id?: string;
  state_cookie_domain?: string;
  ux_mode?: "popup" | "redirect";
  allowed_parent_origin?: string | string[];
  native_callback?: (response: { credential: string }) => void;
}

interface GsiButtonConfig {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  logo_alignment?: "left" | "center";
  width?: string;
  locale?: string;
}

interface GoogleAccountsId {
  initialize: (config: GoogleInitConfig) => void;
  renderButton: (element: HTMLElement, config: GsiButtonConfig) => void;
  prompt: (momentListener?: (moment: {
    getNotDisplayed: () => string;
    getSkippedReason: () => string;
    getDismissedReason: () => string;
  }) => void) => void;
  cancel: () => void;
  revoke: (hint: string, callback: (response: { successful: boolean; error?: string }) => void) => void;
  disableAutoSelect: () => void;
  storeCredential: (credential: string, callback?: () => void) => void;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: GoogleAccountsId;
      };
    };
  }
}

export interface GoogleProfile {
  sub: string;
  email: string;
  email_verified: boolean;
  name: string;
  given_name: string;
  family_name: string;
  picture: string;
  locale: string;
}

export interface GoogleAuthResult {
  loading: boolean;
  error: string;
  initGoogleButton: (
    containerId: string,
    onCredential: (credential: string) => void,
    options?: {
      text?: "signin_with" | "signup_with" | "continue_with" | "signin";
      theme?: "outline" | "filled_blue" | "filled_black";
      size?: "large" | "medium" | "small";
      shape?: "rectangular" | "pill" | "circle" | "square";
    },
  ) => void;
  handleCredential: (
    credential: string,
    onSuccess: (token: string, profile: GoogleProfile) => Promise<void>,
    errorMessage: string,
  ) => Promise<void>;
  extractProfile: (credential: string) => GoogleProfile | null;
}

const SCRIPT_ID = "google-gsi-script";

export function decodeJWTPayload<T = Record<string, unknown>>(token: string): T | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(normalized);
    return JSON.parse(decoded) as T;
  } catch {
    return null;
  }
}

export function useGoogleAuth(clientId: string): GoogleAuthResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const initializedRef = useRef(false);

  useEffect(() => {
    return () => {
      initializedRef.current = false;
    };
  }, []);

  const initGoogleButton = useCallback(
    (
      containerId: string,
      onCredential: (credential: string) => void,
      options?: {
        text?: "signin_with" | "signup_with" | "continue_with" | "signin";
        theme?: "outline" | "filled_blue" | "filled_black";
        size?: "large" | "medium" | "small";
        shape?: "rectangular" | "pill" | "circle" | "square";
      },
    ) => {
      if (!clientId) {
        console.warn("[useGoogleAuth] initGoogleButton called with empty clientId — skipping GIS initialization.");
        return;
      }
      if (initializedRef.current) return;

      const initialize = async () => {
        if (!window.google) {
          console.warn("[useGoogleAuth] Google Identity Services script loaded but window.google is undefined.");
          return;
        }
        if (initializedRef.current) return;
        initializedRef.current = true;

        let nonce: string | undefined;
        try {
          const nonceRes = await api.get("/auth/nonce");
          nonce = nonceRes.data.nonce;
        } catch {
          // nonce is optional; proceed without it
        }

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response: { credential: string }) => {
            onCredential(response.credential);
          },
          cancel_on_tap_outside: false,
          ...(nonce ? { nonce } : {}),
        });
        const btnContainer = document.getElementById(containerId);
        if (btnContainer) {
          window.google.accounts.id.renderButton(btnContainer, {
            type: "standard",
            theme: options?.theme ?? "outline",
            size: options?.size ?? "large",
            width: "320",
            shape: options?.shape ?? "pill",
            logo_alignment: "left",
            text: options?.text ?? "continue_with",
          });
        }
      };

      const existingScript = document.getElementById(SCRIPT_ID);
      if (existingScript) {
        initialize();
        return;
      }

      const script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initialize;
      script.onerror = () => {
        console.error("[useGoogleAuth] Failed to load Google Identity Services script from https://accounts.google.com/gsi/client");
      };
      document.body.appendChild(script);
    },
    [clientId],
  );

  const extractProfile = useCallback(
    (credential: string): GoogleProfile | null => {
      return decodeJWTPayload<GoogleProfile>(credential);
    },
    [],
  );

  const handleCredential = useCallback(
    async (
      credential: string,
      onSuccess: (token: string, profile: GoogleProfile) => Promise<void>,
      errorMessage: string,
    ) => {
      const profile = extractProfile(credential);
      setLoading(true);
      setError("");

      try {
        const res = await api.post("/auth/google", { credential });
        const token: string = res.data.access_token;
        await onSuccess(token, profile ?? ({} as GoogleProfile));
      } catch {
        if (profile) {
          try {
            await onSuccess(credential, profile);
            return;
          } catch {
            // Fall through to error
          }
        }
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [extractProfile],
  );

  return { loading, error, initGoogleButton, handleCredential, extractProfile };
}
