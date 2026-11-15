import React from 'react';

export default function DiffViewer({ originalData, proposedData, recordVersion }) {
  if (!originalData || !proposedData) return null;

  const orig = typeof originalData === 'string' ? (JSON.parse(originalData) || {}) : originalData;
  const prop = typeof proposedData === 'string' ? (JSON.parse(proposedData) || {}) : proposedData;

  const allKeys = Array.from(new Set([...Object.keys(orig), ...Object.keys(prop)]));

  return (
    <div className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-xs overflow-x-auto shadow-inner">
      <div className="flex justify-between items-center pb-2 mb-3 border-b border-slate-700 text-slate-400">
        <span>RECORD VERSION: v{recordVersion}</span>
        <span>BEFORE / AFTER FIELD COMPARISON</span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-red-400 font-semibold mb-2">--- ORIGINAL VALUES ---</div>
          {allKeys.map((k) => (
            <div key={`orig-${k}`} className="py-0.5 truncate">
              <span className="text-slate-500">{k}: </span>
              <span className={orig[k] !== prop[k] ? "bg-red-950 text-red-200 px-1 rounded" : "text-slate-300"}>
                {orig[k] !== undefined && orig[k] !== null ? String(orig[k]) : "null"}
              </span>
            </div>
          ))}
        </div>
        <div>
          <div className="text-emerald-400 font-semibold mb-2">+++ PROPOSED CORRECTION +++</div>
          {allKeys.map((k) => (
            <div key={`prop-${k}`} className="py-0.5 truncate">
              <span className="text-slate-500">{k}: </span>
              <span className={orig[k] !== prop[k] ? "bg-emerald-950 text-emerald-200 font-bold px-1 rounded" : "text-slate-300"}>
                {prop[k] !== undefined && prop[k] !== null ? String(prop[k]) : "null"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
