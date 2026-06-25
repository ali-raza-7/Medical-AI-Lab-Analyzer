import { Component } from "react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", error, info.componentStack);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          className="flex min-h-[400px] flex-col items-center justify-center p-12 text-center"
          role="alert"
        >
          <h2 className="mb-2 text-xl font-bold text-red-500">Something went wrong</h2>
          <p className="mb-6 text-sm text-slate-500">
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="rounded-xl bg-emerald-500 px-6 py-2 text-sm font-bold text-white transition-colors hover:bg-emerald-600"
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
