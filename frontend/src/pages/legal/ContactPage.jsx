import React, { useState } from 'react';
import { Mail, Phone, MapPin, Send, CheckCircle2, ShieldCheck, Clock } from 'lucide-react';
import LegalLayout from './LegalLayout';
import { SITE_CONFIG } from '../../siteConfig';

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    name: 'Alice Employee',
    email: 'alice@company.com',
    subject: 'Grievance / Feedback regarding HR Audit Demo',
    message: '',
  });

  function handleSubmit(e) {
    e.preventDefault();
    setSubmitted(true);
  }

  return (
    <LegalLayout
      title="Contact &amp; Grievance Redressal"
      subtitle="Reach out for technical feedback, prototype inquiries, or DPDP Act 2023 data principal requests."
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left: Official Contact Details */}
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
              Statutory Grievance Redressal
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              In compliance with Section 13 and Rule 3 of the Digital Personal Data Protection Act 2023,
              the designated Data Protection &amp; Grievance Officer handles all access, correction, erasure,
              and data rights requests.
            </p>
          </div>

          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-start gap-3">
              <Mail className="w-4 h-4 text-[#F26A21] shrink-0 mt-0.5" />
              <div>
                <strong className="block text-slate-900 dark:text-white font-semibold">Grievance Officer Email:</strong>
                <a href={`mailto:${SITE_CONFIG.grievanceOfficer.email}`} className="text-[#F26A21] underline">
                  {SITE_CONFIG.grievanceOfficer.email}
                </a>
                <p className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">
                  Officer: {SITE_CONFIG.grievanceOfficer.name} ({SITE_CONFIG.grievanceOfficer.title})
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-start gap-3">
              <Phone className="w-4 h-4 text-[#F26A21] shrink-0 mt-0.5" />
              <div>
                <strong className="block text-slate-900 dark:text-white font-semibold">Direct Telephone:</strong>
                <span className="text-slate-700 dark:text-slate-300">{SITE_CONFIG.grievanceOfficer.phone}</span>
                <p className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">Mon - Fri, 9:30 AM to 6:00 PM IST</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-start gap-3">
              <MapPin className="w-4 h-4 text-[#F26A21] shrink-0 mt-0.5" />
              <div>
                <strong className="block text-slate-900 dark:text-white font-semibold">Physical Registered Address:</strong>
                <span className="text-slate-700 dark:text-slate-300 leading-relaxed block mt-0.5">
                  {SITE_CONFIG.grievanceOfficer.address}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-orange-50/60 dark:bg-orange-950/30 border border-orange-200/60 dark:border-orange-800/60 flex items-start gap-3">
              <Clock className="w-4 h-4 text-[#F26A21] shrink-0 mt-0.5" />
              <div className="text-[11px] text-slate-700 dark:text-slate-300">
                <strong>Statutory SLA:</strong> {SITE_CONFIG.grievanceOfficer.responseTimeline}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Interactive Message Form */}
        <div className="p-6 rounded-3xl bg-slate-50/80 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/80">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
            Send Feedback or Inquire
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Directly test the grievance ticketing intake channel for this prototype.
          </p>

          {submitted ? (
            <div className="p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-center animate-in zoom-in-95 duration-200">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <h4 className="text-sm font-bold text-emerald-800 dark:text-emerald-200">
                Message Received (Simulated)
              </h4>
              <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1 leading-relaxed">
                Thank you! Your simulated inquiry has been logged with ticket reference <code>GRV-{Date.now().toString().slice(-6)}</code>.
              </p>
              <button
                type="button"
                onClick={() => setSubmitted(false)}
                className="mt-4 px-4 py-1.5 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                Send another message
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Your Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:border-[#F26A21] focus:ring-2 focus:ring-orange-500/20 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Your Email</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:border-[#F26A21] focus:ring-2 focus:ring-orange-500/20 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Subject</label>
                <input
                  type="text"
                  required
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:border-[#F26A21] focus:ring-2 focus:ring-orange-500/20 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Message / Request</label>
                <textarea
                  rows={4}
                  required
                  placeholder="Describe your inquiry, data correction request, or evaluation feedback..."
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:border-[#F26A21] focus:ring-2 focus:ring-orange-500/20 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-[#F26A21] hover:bg-[#dc5612] text-white shadow-md shadow-orange-500/25 transition-all flex items-center justify-center gap-1.5 focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
              >
                <Send className="w-3.5 h-3.5" />
                Submit Inquiry
              </button>
            </form>
          )}
        </div>
      </div>
    </LegalLayout>
  );
}
