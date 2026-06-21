import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Link, Navigate } from "react-router-dom";

import { ProtectedRoute } from "@/components/guards/protected-route";
import { RoleRoute } from "@/components/guards/role-route";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { LoginPage } from "@/features/auth/pages/login-page";
import { RegisterPage } from "@/features/auth/pages/register-page";
import { VerifyEmailPage } from "@/features/auth/pages/verify-email-page";

// Auth pages load eagerly (first paint for guests); the authenticated app is
// code-split per feature so the initial bundle stays small.
const DashboardPage = lazy(() =>
  import("@/features/dashboard/pages/dashboard-page").then((m) => ({
    default: m.DashboardPage,
  })),
);
const AnalyzePage = lazy(() =>
  import("@/features/analyze/pages/analyze-page").then((m) => ({
    default: m.AnalyzePage,
  })),
);
const BatchesPage = lazy(() =>
  import("@/features/batches/pages/batches-page").then((m) => ({
    default: m.BatchesPage,
  })),
);
const BatchDetailPage = lazy(() =>
  import("@/features/batches/pages/batch-detail-page").then((m) => ({
    default: m.BatchDetailPage,
  })),
);
const AnalyticsPage = lazy(() =>
  import("@/features/analytics/pages/analytics-page").then((m) => ({
    default: m.AnalyticsPage,
  })),
);
const ComparePage = lazy(() =>
  import("@/features/compare/pages/compare-page").then((m) => ({
    default: m.ComparePage,
  })),
);
const ProfilePage = lazy(() =>
  import("@/features/profile/pages/profile-page").then((m) => ({
    default: m.ProfilePage,
  })),
);
const ModelsPage = lazy(() =>
  import("@/features/models/pages/models-page").then((m) => ({ default: m.ModelsPage })),
);
const ModelDetailPage = lazy(() =>
  import("@/features/models/pages/model-detail-page").then((m) => ({
    default: m.ModelDetailPage,
  })),
);
const DatasetsPage = lazy(() =>
  import("@/features/datasets/pages/datasets-page").then((m) => ({
    default: m.DatasetsPage,
  })),
);
const DatasetDetailPage = lazy(() =>
  import("@/features/datasets/pages/dataset-detail-page").then((m) => ({
    default: m.DatasetDetailPage,
  })),
);
const ExperimentsPage = lazy(() =>
  import("@/features/experiments/pages/experiments-page").then((m) => ({
    default: m.ExperimentsPage,
  })),
);
const ExperimentDetailPage = lazy(() =>
  import("@/features/experiments/pages/experiment-detail-page").then((m) => ({
    default: m.ExperimentDetailPage,
  })),
);
const TrafficPage = lazy(() =>
  import("@/features/traffic/pages/traffic-page").then((m) => ({
    default: m.TrafficPage,
  })),
);
const UsersPage = lazy(() =>
  import("@/features/users/pages/users-page").then((m) => ({ default: m.UsersPage })),
);
const ApiKeysPage = lazy(() =>
  import("@/features/api-keys/pages/api-keys-page").then((m) => ({
    default: m.ApiKeysPage,
  })),
);

function lazyEl(node: ReactNode): ReactNode {
  return <Suspense fallback={<LoadingState />}>{node}</Suspense>;
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you're looking for doesn't exist."
      action={
        <Button asChild>
          <Link to="/dashboard">Back to dashboard</Link>
        </Button>
      }
    />
  );
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/verify-email", element: <VerifyEmailPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: lazyEl(<DashboardPage />) },
          { path: "analyze", element: lazyEl(<AnalyzePage />) },
          { path: "batches", element: lazyEl(<BatchesPage />) },
          { path: "batches/:batchId", element: lazyEl(<BatchDetailPage />) },
          { path: "analytics", element: lazyEl(<AnalyticsPage />) },
          { path: "compare", element: lazyEl(<ComparePage />) },
          { path: "profile", element: lazyEl(<ProfilePage />) },
          { path: "api-keys", element: lazyEl(<ApiKeysPage />) },
          {
            element: <RoleRoute allow={["ai_developer", "admin"]} />,
            children: [
              { path: "models", element: lazyEl(<ModelsPage />) },
              { path: "models/:modelId", element: lazyEl(<ModelDetailPage />) },
              { path: "datasets", element: lazyEl(<DatasetsPage />) },
              { path: "datasets/:datasetId", element: lazyEl(<DatasetDetailPage />) },
              { path: "experiments", element: lazyEl(<ExperimentsPage />) },
              {
                path: "experiments/:experimentId",
                element: lazyEl(<ExperimentDetailPage />),
              },
            ],
          },
          {
            element: <RoleRoute allow={["admin"]} />,
            children: [
              { path: "traffic", element: lazyEl(<TrafficPage />) },
              { path: "users", element: lazyEl(<UsersPage />) },
            ],
          },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);
