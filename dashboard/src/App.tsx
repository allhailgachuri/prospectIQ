import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "./components/Sidebar";

const Dashboard = lazy(() =>
  import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const Prospects = lazy(() =>
  import("./pages/Prospects").then((m) => ({ default: m.Prospects })),
);
const ProspectDetail = lazy(() =>
  import("./pages/ProspectDetail").then((m) => ({ default: m.ProspectDetail })),
);
const WebsiteIntelligence = lazy(() =>
  import("./pages/WebsiteIntelligence").then((m) => ({
    default: m.WebsiteIntelligence,
  })),
);
const Analytics = lazy(() =>
  import("./pages/Analytics").then((m) => ({ default: m.Analytics })),
);
const Reports = lazy(() =>
  import("./pages/Reports").then((m) => ({ default: m.Reports })),
);
const Pipeline = lazy(() =>
  import("./pages/Pipeline").then((m) => ({ default: m.Pipeline })),
);
const Settings = lazy(() =>
  import("./pages/Settings").then((m) => ({ default: m.Settings })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    localStorage.getItem("prospectiq-theme") === "dark" ? "dark" : "light",
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("prospectiq-theme", theme);
  }, [theme]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-shell flex min-h-screen text-slate-900">
          <Sidebar
            theme={theme}
            onToggleTheme={() =>
              setTheme((value) => (value === "light" ? "dark" : "light"))
            }
          />
          <main className="app-main flex-1 overflow-auto">
            <div className="app-content max-w-7xl mx-auto px-6 py-8">
              <Suspense
                fallback={
                  <div className="py-20 text-center text-slate-400">
                    Loading workspace...
                  </div>
                }
              >
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/prospects" element={<Prospects />} />
                  <Route path="/prospects/:id" element={<ProspectDetail />} />
                  <Route path="/websites" element={<WebsiteIntelligence />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/pipeline" element={<Pipeline />} />
                  <Route
                    path="/settings"
                    element={
                      <Settings theme={theme} onThemeChange={setTheme} />
                    }
                  />
                </Routes>
              </Suspense>
            </div>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
