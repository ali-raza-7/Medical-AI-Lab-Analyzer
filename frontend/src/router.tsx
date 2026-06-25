import { lazy, Suspense } from "react";
import { createBrowserRouter, useRouteError, isRouteErrorResponse, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { useAuth } from "./lib/AuthContext";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const SignupPage = lazy(() => import("./pages/SignupPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const ComparePage = lazy(() => import("./pages/ComparePage"));
const PricingPage = lazy(() => import("./pages/PricingPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));

function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500/20 border-t-emerald-500" />
      <span className="sr-only">Loading page...</span>
    </div>
  );
}

function RootError() {
  const error = useRouteError();

  let message = "An unexpected error occurred.";
  if (isRouteErrorResponse(error)) {
    if (error.status === 404) message = "Page not found.";
    else message = error.statusText;
  } else if (error instanceof Error) {
    message = error.message;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center" role="alert">
      <h1 className="mb-4 text-4xl font-bold text-red-500">Oops!</h1>
      <p className="mb-6 text-lg text-slate-600 dark:text-slate-400">{message}</p>
      <button
        onClick={() => window.location.href = "/"}
        className="rounded-xl bg-emerald-500 px-6 py-2 text-white transition-colors hover:bg-emerald-600"
        aria-label="Go to home page"
      >
        Go Home
      </button>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: <RootError />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<PageLoader />}>
            <Dashboard />
          </Suspense>
        ),
      },
      {
        path: "/login",
        element: (
          <Suspense fallback={<PageLoader />}>
            <LoginPage />
          </Suspense>
        ),
      },
      {
        path: "/signup",
        element: (
          <Suspense fallback={<PageLoader />}>
            <SignupPage />
          </Suspense>
        ),
      },
      {
        path: "/history",
        element: (
          <Suspense fallback={<PageLoader />}>
            <ProtectedRoute>
              <HistoryPage />
            </ProtectedRoute>
          </Suspense>
        ),
      },
      {
        path: "/compare",
        element: (
          <Suspense fallback={<PageLoader />}>
            <ProtectedRoute>
              <ComparePage />
            </ProtectedRoute>
          </Suspense>
        ),
      },
      {
        path: "/pricing",
        element: (
          <Suspense fallback={<PageLoader />}>
            <PricingPage />
          </Suspense>
        ),
      },
      {
        path: "/forgot-password",
        element: (
          <Suspense fallback={<PageLoader />}>
            <ForgotPasswordPage />
          </Suspense>
        ),
      },
      {
        path: "/reset-password",
        element: (
          <Suspense fallback={<PageLoader />}>
            <ResetPasswordPage />
          </Suspense>
        ),
      },
      {
        path: "*",
        element: <RootError />,
      },
    ],
  },
]);
