import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, UserCheck, Lock, FileText, Database, Scale, Mail } from 'lucide-react';
import LegalLayout from './LegalLayout';
import { SITE_CONFIG } from '../../siteConfig';

export default function PrivacyPolicyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      subtitle="How Month-End HR Self-Audit Assistant processes and protects data in compliance with India's Digital Personal Data Protection Act 2023 (DPDP Act)."
    >
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Database className="w-5 h-5 text-[#F26A21]" />
          1. Scope &amp; Nature of Application
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          This Privacy Policy applies to the <strong>{SITE_CONFIG.productName}</strong>, developed by{' '}
          <strong>{SITE_CONFIG.ownerName}</strong> as a technology demonstrator for Homingo Hack Days 2026.
          All human resource profiles, employee numbers, compensation structures, timesheets, and disciplinary
          records used in this demonstration environment are <strong>fictitious and simulated</strong>.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <UserCheck className="w-5 h-5 text-[#F26A21]" />
          2. Personal Data Processed in this Prototype
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-3">
          For the purposes of simulating enterprise HR compliance and audit readiness, the system processes:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <strong className="text-slate-900 dark:text-white block mb-1">Identity &amp; Profile Data:</strong>
            Fictional employee IDs, full names, job titles, business units, branches, and manager reporting lines.
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <strong className="text-slate-900 dark:text-white block mb-1">Attendance &amp; Leave:</strong>
            Punch records, biometric timesheet summaries, annual leave balances, and absence justifications.
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <strong className="text-slate-900 dark:text-white block mb-1">Payroll &amp; Statutory:</strong>
            Simulated gross salaries, Provident Fund (PF), ESIC, Professional Tax, and TDS calculations.
          </div>
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <strong className="text-slate-900 dark:text-white block mb-1">Compliance &amp; Workplace Governance:</strong>
            POSH training completions, grievance logs, disciplinary show-cause notices, and appraisal reviews.
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Lock className="w-5 h-5 text-[#F26A21]" />
          3. Purposes of Processing &amp; Role-Based Access
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-2">
          Data is processed solely for deterministic audit reconciliation, regulatory compliance tracking, and maker-checker validation:
        </p>
        <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
          <li><strong>Employees:</strong> View their own attendance flags, submit correction requests, and access personal payslips.</li>
          <li><strong>Managers:</strong> Review and sign off on attendance anomalies and leave applications for their direct reports.</li>
          <li><strong>HR Administrators:</strong> Conduct month-end payroll runs, review statutory challans, and manage onboarding/offboarding workflows.</li>
          <li><strong>Internal Committee (IC) Members:</strong> Restricted access to sensitive POSH and grievance investigations under duty 3.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <ShieldCheck className="w-5 h-5 text-[#F26A21]" />
          4. Data Security &amp; Immutable Audit Trail
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          Every human approval, automated bot calculation, and consent decision is recorded in an immutable,
          <strong> SHA-256 hash-chained audit ledger</strong>. Passwords are encrypted using bcrypt salt hashing,
          and identity verification is guarded by short-lived 10-minute OTPs.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Scale className="w-5 h-5 text-[#F26A21]" />
          5. Rights Under India's DPDP Act 2023
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-3">
          Under Chapter III of the Digital Personal Data Protection Act 2023, Data Principals enjoy explicit statutory rights:
        </p>
        <div className="space-y-2 text-xs">
          <div className="p-3 rounded-xl bg-orange-50/50 dark:bg-orange-950/20 border border-orange-200/60 dark:border-orange-800/60">
            <strong className="text-slate-900 dark:text-white">Right to Access Information (Section 11):</strong> You may request a summary of your personal data and processing activities.
          </div>
          <div className="p-3 rounded-xl bg-orange-50/50 dark:bg-orange-950/20 border border-orange-200/60 dark:border-orange-800/60">
            <strong className="text-slate-900 dark:text-white">Right to Correction and Erasure (Section 12):</strong> You may request correction of inaccurate data or erasure of data no longer necessary for the audit purpose.
          </div>
          <div className="p-3 rounded-xl bg-orange-50/50 dark:bg-orange-950/20 border border-orange-200/60 dark:border-orange-800/60">
            <strong className="text-slate-900 dark:text-white">Right of Grievance Redressal (Section 13):</strong> You have the right to register grievances with our Data Protection Officer.
          </div>
          <div className="p-3 rounded-xl bg-orange-50/50 dark:bg-orange-950/20 border border-orange-200/60 dark:border-orange-800/60">
            <strong className="text-slate-900 dark:text-white">Right to Nominate (Section 14):</strong> You may designate a representative to exercise your data rights in the event of death or incapacity.
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Mail className="w-5 h-5 text-[#F26A21]" />
          6. Grievance Officer Contact
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-2">
          For inquiries or to exercise your DPDP Act rights, please contact our designated Grievance Officer:
        </p>
        <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
          <p><strong>Name:</strong> {SITE_CONFIG.grievanceOfficer.name}</p>
          <p><strong>Designation:</strong> {SITE_CONFIG.grievanceOfficer.title}</p>
          <p><strong>Email:</strong> <a href={`mailto:${SITE_CONFIG.grievanceOfficer.email}`} className="text-[#F26A21] underline">{SITE_CONFIG.grievanceOfficer.email}</a></p>
          <p><strong>Address:</strong> {SITE_CONFIG.grievanceOfficer.address}</p>
          <p className="text-slate-500 dark:text-slate-400 pt-1">{SITE_CONFIG.grievanceOfficer.responseTimeline}</p>
        </div>
      </section>
    </LegalLayout>
  );
}
