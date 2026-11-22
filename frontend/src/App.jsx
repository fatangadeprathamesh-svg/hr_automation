import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import { getCurrentPersona } from './api';

export default function App() {
  const [persona, setPersona] = useState(getCurrentPersona());

  function handlePersonaChange(newPersona) {
    setPersona(newPersona);
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Authentication Shell Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/verify" element={<VerifyOtpPage />} />

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
          <Route path="/employee" element={<EmployeePage key={persona?.id} />} />
          <Route path="/manager" element={<ManagerPage key={persona?.id} />} />
          <Route path="/hr" element={<HRPage key={persona?.id} />} />
          <Route path="/duties" element={<DutiesHubPage key={persona?.id} />} />
          <Route path="/duties/:dutyKey" element={<DutyDetailPage key={persona?.id} />} />
          <Route path="/data-import" element={<DataImportPage key={persona?.id} />} />
          <Route path="/audit-log" element={<AuditLogPage key={persona?.id} />} />
        </Route>

        {/* Fallback: Unknown URLs navigate to /login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>

      {/* Global DPDP Act 2023 Compliant Cookie & Privacy Consent Banner */}
      <CookieConsentBanner />
    </BrowserRouter>
  );
}
