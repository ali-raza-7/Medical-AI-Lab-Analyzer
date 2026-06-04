import { createBrowserRouter, useRouteError, isRouteErrorResponse } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HistoryPage from "./pages/HistoryPage";
import ComparePage from "./pages/ComparePage";

function RootError() {
  const error = useRouteError();
  console.error(error);

  let message = "An unexpected error occurred.";
  if (isRouteErrorResponse(error)) {
    if (error.status === 404) message = "Page not found.";
    else message = error.statusText;
  } else if (error instanceof Error) {
    message = error.message;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
      <h1 className="text-4xl font-bold text-red-500 mb-4">Oops!</h1>
      <p className="text-lg text-slate-600 dark:text-slate-400 mb-6">{message}</p>
      <button
        onClick={() => window.location.href = "/"}
        className="rounded-xl bg-emerald-500 px-6 py-2 text-white hover:bg-emerald-600 transition-colors"
      >
        Go Home
      </button>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: <RootError />,
    children: [
      { path: "/", element: <Dashboard /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/signup", element: <SignupPage /> },
      { path: "/history", element: <HistoryPage /> },
      { path: "/compare", element: <ComparePage /> },
      { path: "*", element: <RootError /> }
    ],
  },
]);

