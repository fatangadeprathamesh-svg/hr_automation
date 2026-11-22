import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, ShieldAlert, CheckCircle2, AlertOctagon, HelpCircle } from 'lucide-react';
import LegalLayout from './LegalLayout';
import { SITE_CONFIG } from '../../siteConfig';

export default function TermsOfUsePage() {
  return (
    <LegalLayout
      title="Terms of Use"
      subtitle="Operational rules, evaluation conditions, and prototype licensing terms for Month-End HR Self-Audit Assistant."
    >
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <FileText className="w-5 h-5 text-[var(--accent-text)]" />
          1. Prototype License &amp; Evaluation Scope
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          The <strong>{SITE_CONFIG.productName}</strong> is provided as an evaluation prototype for the Homingo Hack Days 2026.
          All access is granted on a limited, non-exclusive, revocable, and non-commercial trial basis solely to evaluate
          the deterministic HR audit engine and maker-checker duties framework.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <ShieldAlert className="w-5 h-5 text-[var(--accent-text)]" />
          2. Simulated Data &amp; No Government Integration
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          All calculations for Provident Fund (EPFO), ESIC, Professional Tax, and Income Tax (TDS) are based on sample
          rates and heuristic formulas for demonstration purposes. <strong>This prototype does not connect to any official
          government portal</strong> (such as TRACES, EPFO unified portal, or State PT portals). Users must never rely on
          these calculations for actual statutory tax filings without independent certified payroll review.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <CheckCircle2 className="w-5 h-5 text-[var(--accent-text)]" />
          3. Maker-Checker Rules &amp; User Conduct
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-2">
          By using this service, you agree to adhere to the core governance principles enforced by the backend:
        </p>
        <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
          <li><strong>Maker-Checker Integrity:</strong> A user who drafts, submits, or prepares an HR duty item cannot approve their own item. Any attempt to bypass maker-checker validation will be rejected with an HTTP 403 Forbidden status.</li>
          <li><strong>Bot-Human Separation:</strong> Automated background processes may ingest, calculate, and prepare compliance tasks, but final authorization requires a designated human approver with proper credentials.</li>
          <li><strong>Ledger Auditing:</strong> All modifications, corrections, and sign-offs are permanently recorded in the hash-chained audit ledger.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <AlertOctagon className="w-5 h-5 text-[var(--accent-text)]" />
          4. Disclaimer of Warranties &amp; Limitation of Liability
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          The prototype is provided <em>"AS IS"</em> and <em>"AS AVAILABLE"</em> without warranties of any kind, either express or implied.
          Neither {SITE_CONFIG.ownerName} nor its contributors shall be held liable for any damages, penalties, or compliance disputes
          arising from the use or inability to use this software.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <HelpCircle className="w-5 h-5 text-[var(--accent-text)]" />
          5. Modifications &amp; Governing Law
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          We reserve the right to amend these Terms of Use at any time. Material changes will be accompanied by an incremented
          policy version number. These terms are governed by the laws of India, and subject to the exclusive jurisdiction of the
          courts of Bangalore, Karnataka.
        </p>
      </section>
    </LegalLayout>
  );
}
