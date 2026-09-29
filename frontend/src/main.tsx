import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import NavBar from "@/components/NavBar";
import { RoleProvider } from "@/lib/role";
import "@/app/globals.css";
import LandingPage from "@/app/page";
import AdminPage from "@/app/admin/page";
import AlertsPage from "@/app/alerts/page";
import AnalyticsPage from "@/app/analytics/page";
import CitizenPage from "@/app/citizen/page";
import DashboardPage from "@/app/dashboard/page";
import HyperlocalPage from "@/app/hyperlocal/page";
import MapPage from "@/app/map/page";
import ResourcesPage from "@/app/resources/page";
import WardPage from "@/app/ward/[id]/page";
import LoginPage from "@/app/login/page";

function App() {
  const { pathname } = useLocation();
  const isLogin = pathname === "/login";

  return (
    <RoleProvider>
      {!isLogin && <NavBar />}
      <main className="mx-auto max-w-[1500px] px-4 pb-16 pt-6 sm:px-6">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<LandingPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/citizen" element={<CitizenPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/hyperlocal" element={<HyperlocalPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/ward/:id" element={<WardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </RoleProvider>
  );
}

export default function Root() {
  return (
    <StrictMode>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>
    </StrictMode>
  );
}

createRoot(document.getElementById("root")!).render(<Root />);