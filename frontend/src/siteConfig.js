// Central Configuration for Month-End HR Self-Audit Assistant
// Change owner name, product name, or legal contacts in this single file.

export const SITE_CONFIG = {
  productName: "Month-End HR Self-Audit Assistant",
  ownerName: "Homingo Labs Private Limited",
  year: "2026",
  hackathonNote: "Prototype built for Homingo Hack Days 2026. All data shown is fictional.",
  policyVersion: "2026.1",
  lastUpdated: "November 22, 2026",
  grievanceOfficer: {
    name: "Aditi Sharma",
    title: "Data Protection & Grievance Redressal Officer",
    email: "grievance.officer@homingo-audit.demo",
    phone: "+91 80 4000 0000",
    address: "4th Floor, Innovation Park, Outer Ring Road, Bangalore 560103, Karnataka, India",
    responseTimeline: "Under Section 32 of the DPDP Act 2023, grievances are acknowledged within 24 hours and resolved within 7 business days."
  },
  cookieCategories: {
    necessary: {
      name: "Strictly Necessary",
      description: "Essential for core app functionality, user authentication, security tokens, and tamper-evident audit ledger integrity. Cannot be disabled.",
      locked: true,
      defaultChecked: true,
    },
    preferences: {
      name: "Preferences",
      description: "Remembers your light/dark theme preference and active test persona across browser sessions. If disabled, settings last for the current session only.",
      locked: false,
      defaultChecked: false,
    },
    analytics: {
      name: "Analytics",
      description: "Anonymous, first-party aggregated audit metric counts to verify test rule runs. No third-party trackers, cross-site cookies, or personal profiles are used.",
      locked: false,
      defaultChecked: false,
    },
  },
};
