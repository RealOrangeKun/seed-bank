import { QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { ThemeProvider } from "@/components/theme/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/features/auth/auth-provider";
import { I18nProvider } from "@/i18n";
import { queryClient } from "@/lib/query-client";

import { router } from "./router";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <RouterProvider router={router} />
            <Toaster position="top-right" richColors />
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </I18nProvider>
  </React.StrictMode>,
);
