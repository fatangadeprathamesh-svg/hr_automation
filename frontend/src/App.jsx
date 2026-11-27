import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import VerifyOtpPage from './pages/VerifyOtpPage';
import EmployeePage from './pages/EmployeePage';
import ManagerPage from './pages/ManagerPage';
import HRPage from './pages/HRPage';
import AuditLogPage from './pages/AuditLogPage';
import DataImportPage from './pages/DataImportPage';
import DutiesHubPage from './pages/DutiesHubPage';
import DutyDetailPage from './pages/DutyDetailPage';
import PrivacyPolicyPage from './pages/legal/PrivacyPolicyPage';
import TermsOfUsePage from './pages/legal/TermsOfUsePage';
import CookiePolicyPage from './pages/legal/CookiePolicyPage';
import ContactPage from './pages/legal/ContactPage';
import CookieConsentBanner from './components/common/CookieConsentBanner';
import AppLayout from './components/layout/AppLayout';
import { getCurrentPersona, getRoleHome, isAuthenticated } from './api';

function HomeRedirect() {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  const persona = getCurrentPersona();
  const role = persona?.role || 'employee';
  return <Navigate to={getRoleHome(role)} replace />;
}

function RoleRouteGuard({ allowedRoles, children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  const persona = getCurrentPersona();
  const role = persona?.role || 'employee';

  if (!allowedRoles.includes(role)) {
    const home = getRoleHome(role);
    return <Navigate to={home} replace state={{ roleNotice: "That page is not available for your role" }} />;
  }

  return children;
}

function DutyRouteGuard({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  const { dutyKey } = useParams();
  const persona = getCurrentPersona();
  const role = persona?.role || 'employee';

  if (role === 'ic_member' && dutyKey && dutyKey !== 'posh') {
    return <Navigate to="/duties" replace state={{ roleNotice: "That page is not available for your role" }} />;
  }
  return children;
}

export default function App() {
  const [persona, setPersona] = useState(getCurrentPersona());

  function handlePersonaChange(newPersona) {
    setPersona(newPersona);
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Home route: redirects to the authenticated role's home */}
        <Route path="/" element={<HomeRedirect />} />

        {/* Public Authentication Shell Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify" element={<VerifyOtpPage />} />
        <Route path="/verify-otp" element={<VerifyOtpPage />} />

        {/* Public Legal & Transparency Routes */}
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms" element={<TermsOfUsePage />} />
        <Route path="/cookies" element={<CookiePolicyPage />} />
        <Route path="/contact" element={<ContactPage />} />

        {/* Protected Application Shell Routes wrapped by AppLayout */}
        <Route
          element={
            <AppLayout
              title="Month-End HR Self-Audit Assistant"
              onPersonaChange={handlePersonaChange}
            />
          }
        >
          <Route
            path="/employee"
            element={
              <RoleRouteGuard allowedRoles={['employee']}>
                <EmployeePage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
          <Route
            path="/manager"
            element={
              <RoleRouteGuard allowedRoles={['manager']}>
                <ManagerPage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
          <Route
            path="/hr"
            element={
              <RoleRouteGuard allowedRoles={['hr_admin', 'hr']}>
                <HRPage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
          <Route
            path="/duties"
            element={
              <RoleRouteGuard allowedRoles={['employee', 'manager', 'hr_admin', 'hr', 'ic_member']}>
                <DutiesHubPage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
          <Route
            path="/duties/:dutyKey"
            element={
              <DutyRouteGuard>
                <DutyDetailPage key={persona?.id} />
              </DutyRouteGuard>
            }
          />
          <Route
            path="/data-import"
            element={
              <RoleRouteGuard allowedRoles={['hr_admin', 'hr']}>
                <DataImportPage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
          <Route
            path="/audit-log"
            element={
              <RoleRouteGuard allowedRoles={['manager', 'hr_admin', 'hr']}>
                <AuditLogPage key={persona?.id} />
              </RoleRouteGuard>
            }
          />
        </Route>

        {/* Fallback: Unknown URLs navigate to role home if authenticated, else /login */}
        <Route path="*" element={<HomeRedirect />} />
      </Routes>

      {/* Global DPDP Act 2023 Compliant Cookie & Privacy Consent Banner */}
      <CookieConsentBanner />
    </BrowserRouter>
  );
}
