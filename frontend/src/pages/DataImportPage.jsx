import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Download,
  RefreshCw,
  Search,
  Filter,
  History,
  Table as TableIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Zap,
  AlertCircle,
  FileText,
  X,
  Trash2,
} from 'lucide-react';
import {
  uploadMasterCsv,
  getUploadStatus,
  getRejectedRows,
  downloadRejectedRowsCsv,
  getUploadHistory,
  getMasterRecords,
  getMasterStats,
  resetAllDataApi,
  getCurrentPersona,
  retryUpload,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import StatsCard from '../components/common/StatsCard';
import StatusPill from '../components/common/StatusPill';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';

const RECORD_TYPES = [
  { id: 'all', label: 'All Records' },
  { id: 'employee_profile', label: 'Employee Profile' },
  { id: 'leave_request', label: 'Leave Request' },
  { id: 'leave_balance', label: 'Leave Balance' },
  { id: 'timesheet', label: 'Timesheet' },
  { id: 'training', label: 'Training' },
  { id: 'engagement_survey', label: 'Engagement Survey' },
  { id: 'applicant', label: 'Applicant' },
];

const CANONICAL_COLUMNS = [
  "record_id", "record_type", "source_file", "employee_id", "applicant_id",
  "employee_name", "first_name", "last_name", "department", "position",
  "division", "business_unit", "branch_location", "manager", "employment_type",
  "gender", "age", "dob", "marital_status", "state", "education",
  "hire_date", "exit_date", "employee_status", "performance_score",
  "performance_rating", "monthly_income", "years_experience", "salary_hike_pct",
  "event_date", "start_date", "end_date", "applied_date", "status",
  "category", "reason", "days", "clock_in", "clock_out", "hours_total",
  "hours_scheduled", "break_minutes", "leave_entitlement", "leave_taken_so_far",
  "leave_remaining", "engagement_score", "satisfaction_score",
  "work_life_balance_score", "training_program", "training_outcome",
  "trainer", "training_location", "training_cost", "desired_salary", "country",
  // 6 optional columns
  "email", "project_code", "amount", "expense_category", "receipt_attached", "overtime_approved"
];

function formatFileSize(bytes) {
  if (!bytes && bytes !== 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function DataImportPage() {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'records' | 'history'

  // Upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileInspection, setFileInspection] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [currentUpload, setCurrentUpload] = useState(null);
  const [pollIntervalId, setPollIntervalId] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [rejectedRowsData, setRejectedRowsData] = useState([]);
  const [isLoadingRejected, setIsLoadingRejected] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  async function handleRetryUpload(uploadId) {
    if (!uploadId) return;
    setIsRetrying(true);
    setUploadError(null);
    try {
      await retryUpload(uploadId);
      setIsUploading(true);
      const res = await getUploadStatus(uploadId);
      setCurrentUpload(res);
    } catch (err) {
      setUploadError(err.message || 'Failed to retry upload.');
    } finally {
      setIsRetrying(false);
    }
  }

  // Guarded Reset Data state
  const persona = getCurrentPersona();
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetConfirmationInput, setResetConfirmationInput] = useState('');
  const [isResetting, setIsResetting] = useState(false);
  const [resetSuccessMsg, setResetSuccessMsg] = useState(null);

  // Upload History state
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Records state
  const [records, setRecords] = useState([]);
  const [recordsTotal, setRecordsTotal] = useState(0);
  const [recordsPage, setRecordsPage] = useState(1);
  const [recordsPageSize, setRecordsPageSize] = useState(25);
  const [recordsTotalPages, setRecordsTotalPages] = useState(1);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [selectedRecordType, setSelectedRecordType] = useState('all');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Stats state
  const [stats, setStats] = useState(null);

  const fileInputRef = useRef(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setRecordsPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load initial stats & history on mount
  useEffect(() => {
    loadStats();
    loadHistory();
  }, []);

  // Poll upload status when upload is processing
  useEffect(() => {
    if (!currentUpload || (currentUpload.status !== 'processing' && currentUpload.status !== 'queued')) {
      if (pollIntervalId) {
        clearInterval(pollIntervalId);
        setPollIntervalId(null);
      }
      return;
    }

    const interval = setInterval(async () => {
      try {
        const statusRes = await getUploadStatus(currentUpload.id);
        setCurrentUpload(statusRes);

        if (statusRes.status === 'done' || statusRes.status === 'failed') {
          clearInterval(interval);
          setPollIntervalId(null);
          setIsUploading(false);

          if (statusRes.status === 'done') {
            setUploadSuccess(
              `Ingestion complete: ${statusRes.accepted_rows.toLocaleString()} accepted rows, ${statusRes.rejected_rows.toLocaleString()} rejected.`
            );
            loadStats();
            loadHistory();
            if (statusRes.rejected_rows > 0) {
              fetchRejected(statusRes.id);
            }
          } else {
            setUploadError(statusRes.error_message || 'Upload processing failed.');
          }
        }
      } catch (err) {
        console.warn('Polling error:', err);
      }
    }, 1000);

    setPollIntervalId(interval);

    return () => clearInterval(interval);
  }, [currentUpload?.id, currentUpload?.status]);

  // Load records whenever filters change
  useEffect(() => {
    if (activeTab === 'records') {
      loadRecords();
    }
  }, [activeTab, recordsPage, recordsPageSize, selectedRecordType, selectedDepartment, debouncedSearch]);

  async function loadStats() {
    try {
      const data = await getMasterStats();
      setStats(data);
    } catch (_) {}
  }

  async function loadHistory() {
    setLoadingHistory(true);
    try {
      const data = await getUploadHistory(50);
      setHistoryList(data.uploads || []);
    } catch (_) {
    } finally {
      setLoadingHistory(false);
    }
  }

  async function loadRecords() {
    setLoadingRecords(true);
    try {
      const params = {
        page: recordsPage,
        page_size: recordsPageSize,
      };
      if (selectedRecordType !== 'all') {
        params.record_type = selectedRecordType;
      }
      if (selectedDepartment) {
        params.department = selectedDepartment;
      }
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      const res = await getMasterRecords(params);
      setRecords(res.items || []);
      setRecordsTotal(res.total || 0);
      setRecordsTotalPages(res.total_pages || 1);
    } catch (err) {
      console.warn('Failed to load master records:', err);
    } finally {
      setLoadingRecords(false);
    }
  }

  async function fetchRejected(uploadId) {
    setIsLoadingRejected(true);
    try {
      const res = await getRejectedRows(uploadId);
      setRejectedRowsData(res.rejected_rows || []);
    } catch (err) {
      console.warn('Failed to fetch rejected rows:', err);
    } finally {
      setIsLoadingRejected(false);
    }
  }

  async function handleConfirmReset() {
    if (resetConfirmationInput !== 'RESET') return;
    setIsResetting(true);
    setUploadError(null);
    try {
      const res = await resetAllDataApi();
      setResetSuccessMsg(res.message || 'All ingested and synthetic data purged successfully.');
      setResetModalOpen(false);
      setResetConfirmationInput('');
      loadStats();
      if (activeTab === 'history') loadHistory();
      if (activeTab === 'records') loadRecords();
    } catch (err) {
      setUploadError(err.message || 'Failed to reset database.');
    } finally {
      setIsResetting(false);
    }
  }

  // File selection & drop handlers
  function handleFileSelect(e) {
    const file = e.target.files?.[0];
    validateAndSetFile(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    validateAndSetFile(file);
  }

  function validateAndSetFile(file) {
    if (!file) return;

    setUploadError(null);
    setUploadSuccess(null);
    setRejectedRowsData([]);
    setFileInspection(null);

    // Check extension
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Invalid file type: Please select a valid .csv file.');
      setSelectedFile(null);
      return;
    }

    // Check size limit: 200MB
    const maxBytes = 200 * 1024 * 1024;
    if (file.size > maxBytes) {
      setUploadError(
        `File is too large (${formatFileSize(file.size)}). The maximum allowed upload size is 200 MB.`
      );
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);

    // Inspect header client-side to report missing required or unknown columns immediately
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result || '';
        const firstLine = text.split(/[\r\n]+/)[0] || '';
        const delimiter = (firstLine.includes('\t') && firstLine.split('\t').length > firstLine.split(',').length) ? '\t' : ',';
        const rawHeaders = firstLine.split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''));
        const normalizedHeaders = rawHeaders.map(h => h.toLowerCase().replace(/\s+/g, '_'));

        const missingRequired = ['record_id', 'record_type'].filter(req => !normalizedHeaders.includes(req));
        const unknownCols = rawHeaders.filter((_, idx) => {
          const norm = normalizedHeaders[idx];
          return norm && !CANONICAL_COLUMNS.includes(norm);
        });

        const inspection = {
          checked: true,
          totalColumns: rawHeaders.length,
          missingRequired,
          unknownColumns: unknownCols,
        };
        setFileInspection(inspection);

        if (missingRequired.length > 0) {
          let warnMsg = `CSV is missing required column(s): ${missingRequired.join(', ')}.`;
          if (unknownCols.length > 0) {
            warnMsg += ` Unknown columns ignored: ${unknownCols.join(', ')}.`;
          }
          setUploadError(warnMsg);
        }
      } catch (_) {
        setFileInspection(null);
      }
    };
    reader.readAsText(file.slice(0, 8192));
  }

  async function handleStartUpload() {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    setRejectedRowsData([]);

    try {
      const res = await uploadMasterCsv(selectedFile);
      setCurrentUpload({
        id: res.upload_id,
        filename: res.filename,
        status: 'queued',
        total_rows: 0,
        accepted_rows: 0,
        rejected_rows: 0,
        duration_seconds: 0,
        duplicate_warning: res.duplicate_warning,
      });

      if (res.duplicate_warning) {
        setUploadSuccess('Note: An identical file was previously uploaded. Existing records will be updated idempotently.');
      }
    } catch (err) {
      setIsUploading(false);
      setUploadError(err.message || 'Server is unreachable or upload failed. Verify backend is running.');
    }
  }

  async function handleDownloadRejected(uploadId) {
    try {
      await downloadRejectedRowsCsv(uploadId);
    } catch (err) {
      setUploadError('Failed to download rejected rows CSV.');
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <GlassCard className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)]">
              <FileSpreadsheet className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Master HR Data Import</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Ingest, validate, and query enterprise Master HR CSV files (55 columns, up to 500k+ rows) with atomic bulk UPSERT.
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700">
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'upload'
                ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            Upload File
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'records'
                ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <TableIcon className="w-4 h-4" />
            Records Viewer
          </button>
          <button
            onClick={() => {
              setActiveTab('history');
              loadHistory();
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
              activeTab === 'history'
                ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <History className="w-4 h-4" />
            Upload History
          </button>

          {(persona?.role === 'hr_admin' || persona?.role === 'hr') && (
            <button
              onClick={() => {
                setResetConfirmationInput('');
                setResetModalOpen(true);
              }}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-200 dark:border-rose-800 transition-colors"
              title="Reset all ingested and synthetic data"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Reset All Data</span>
            </button>
          )}
        </div>
      </GlassCard>

      {/* Global Notifications */}
      <ErrorBanner message={uploadError} onDismiss={() => setUploadError(null)} />
      {resetSuccessMsg && (
        <div className="rounded-2xl border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 p-4 shadow-sm text-xs flex items-center justify-between">
          <div className="flex items-center gap-3 text-rose-800 dark:text-rose-200">
            <CheckCircle2 className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
            <span>{resetSuccessMsg}</span>
          </div>
          <button onClick={() => setResetSuccessMsg(null)} className="text-rose-600 hover:text-rose-800 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {uploadSuccess && (
        <div className="rounded-2xl border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 p-4 shadow-sm text-xs flex items-center justify-between">
          <div className="flex items-center gap-3 text-emerald-800 dark:text-emerald-200">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
          <button onClick={() => setUploadSuccess(null)} className="text-emerald-600 hover:text-emerald-800 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Overview Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatsCard
            title="Total Records"
            value={stats.total_records.toLocaleString()}
            subtitle="Ingested in DB"
            icon={TableIcon}
          />
          <StatsCard
            title="Employees"
            value={stats.totals.employees_count.toLocaleString()}
            subtitle="Profiles stored"
            icon={CheckCircle2}
          />
          <StatsCard
            title="Timesheet Hours"
            value={`${stats.totals.timesheet_hours_total.toLocaleString()}h`}
            subtitle="Logged hours"
            icon={Clock}
          />
          <StatsCard
            title="Leave Days"
            value={`${stats.totals.leave_days_total.toLocaleString()}d`}
            subtitle="Requested days"
            icon={FileSpreadsheet}
          />
          <StatsCard
            title="Unapproved TS"
            value={stats.totals.unapproved_timesheets.toLocaleString()}
            subtitle="Pending review"
            icon={AlertTriangle}
          />
          <StatsCard
            title="Applicants"
            value={stats.totals.applicants_count.toLocaleString()}
            subtitle="Candidates"
            icon={Zap}
          />
        </div>
      )}

      {/* TAB 1: UPLOAD & PROCESSING */}
      {activeTab === 'upload' && (
        <div className="space-y-6">
          <GlassCard className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">Upload Master CSV</h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Drag and drop your HR CSV file below. The system validates all 55 columns with streaming background bulk insertion.
                </p>
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-3xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                dragActive
                  ? 'border-[var(--accent)] bg-[var(--accent-bg-subtle)] scale-[0.99]'
                  : 'border-slate-300 dark:border-slate-700 hover:border-[var(--accent)] bg-slate-50/40 dark:bg-slate-900/30'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="w-14 h-14 rounded-2xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] flex items-center justify-center mb-3 shadow-inner">
                <UploadCloud className="w-7 h-7" />
              </div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {selectedFile ? selectedFile.name : 'Drag & drop your CSV file here, or browse'}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Supports .csv files up to 200 MB with UTF-8 & BOM encoding.
              </p>

              {selectedFile && (
                <div className="mt-4 flex flex-col items-center gap-2">
                  <div className="px-4 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-700 dark:text-slate-300 shadow-sm flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[var(--accent-text)]" />
                    <span>{selectedFile.name}</span>
                    <span className="text-slate-400">|</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{formatFileSize(selectedFile.size)}</span>
                  </div>

                  {fileInspection && (
                    <div className="text-[11px] max-w-lg space-y-1">
                      {fileInspection.missingRequired.length > 0 ? (
                        <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 font-sans">
                          <strong>Missing required column(s):</strong> {fileInspection.missingRequired.join(', ')}
                          {fileInspection.unknownColumns.length > 0 && (
                            <div className="mt-1 text-[10px] text-rose-600 dark:text-rose-400">
                              Unknown columns that will be ignored: {fileInspection.unknownColumns.join(', ')}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 font-sans flex items-center gap-1.5 justify-center">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span>Valid header: {fileInspection.totalColumns} columns detected (required fields present)</span>
                          {fileInspection.unknownColumns.length > 0 && (
                            <span className="text-amber-700 dark:text-amber-400 ml-1">
                              &bull; {fileInspection.unknownColumns.length} unknown column(s) will be ignored
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              {selectedFile && (
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  disabled={isUploading}
                  className="px-4 py-2 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 transition-colors"
                >
                  Clear
                </button>
              )}
              <button
                type="button"
                onClick={handleStartUpload}
                disabled={!selectedFile || isUploading}
                className="btn-accent flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold shadow-md disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    Start Ingestion
                  </>
                )}
              </button>
            </div>

            {/* Live Progress Bar & Status Card */}
            {currentUpload && (
              <div className="mt-6 p-5 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 space-y-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <StatusPill status={currentUpload.status} />
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {currentUpload.filename}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-mono text-slate-500 dark:text-slate-400">
                    {currentUpload.duration_seconds > 0 && (
                      <span>Time: {currentUpload.duration_seconds.toFixed(2)}s</span>
                    )}
                    {currentUpload.rows_per_second > 0 && (
                      <span className="text-[var(--accent-text)] font-bold">
                        {currentUpload.rows_per_second.toLocaleString()} rows/s
                      </span>
                    )}
                  </div>
                </div>

                {/* Animated Progress Bar */}
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-2.5 rounded-full transition-all duration-300 ${
                      currentUpload.status === 'failed'
                        ? 'bg-rose-500'
                        : currentUpload.status === 'done'
                        ? 'bg-emerald-500'
                        : 'bg-[var(--accent)] animate-pulse'
                    }`}
                    style={{
                      width:
                        currentUpload.status === 'done'
                          ? '100%'
                          : currentUpload.status === 'processing'
                          ? `${Math.min(95, Math.max(15, (currentUpload.accepted_rows / (currentUpload.total_rows || 1)) * 100))}%`
                          : '10%',
                    }}
                  />
                </div>

                {/* Ingestion Metrics Grid */}
                <div className="grid grid-cols-3 gap-3 pt-1">
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                    <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Processed</span>
                    <p className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                      {currentUpload.total_rows.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40">
                    <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Accepted</span>
                    <p className="text-base font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">
                      {currentUpload.accepted_rows.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/40">
                    <span className="text-[10px] font-medium text-rose-600 dark:text-rose-400 uppercase tracking-wider">Rejected</span>
                    <p className="text-base font-bold text-rose-700 dark:text-rose-300 mt-0.5">
                      {currentUpload.rejected_rows.toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Duplicate Re-upload Warning */}
                {currentUpload.duplicate_warning && (
                  <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 flex items-start gap-2 text-xs text-amber-800 dark:text-amber-300">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                    <span>
                      <strong>Idempotent Re-upload:</strong> This identical file hash was previously ingested. Existing records were updated in-place without creating duplicate rows.
                    </span>
                  </div>
                )}

                {/* 5-Stage Pipeline Stepper */}
                <div className="pt-3 border-t border-slate-200/50 dark:border-slate-800/60">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                    <span>End-to-End Ingestion & Audit Pipeline</span>
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
                    {/* Stage 1: Uploaded */}
                    {(() => {
                      const stage = currentUpload.pipeline_stages?.uploaded || (currentUpload.status !== 'queued' ? { status: 'done' } : { status: 'in_progress' });
                      const isDone = stage.status === 'done';
                      const isProgress = stage.status === 'in_progress' || (currentUpload.status === 'queued' && !isDone);
                      const isFailed = stage.status === 'failed';
                      return (
                        <div className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                          isDone ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-500/30' :
                          isProgress ? 'bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]' :
                          isFailed ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-500/30' :
                          'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200/50 dark:border-slate-700/50 opacity-60'
                        }`}>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] text-slate-700 dark:text-slate-300">1. Uploaded</span>
                              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> :
                               isProgress ? <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-text)] animate-spin" /> :
                               isFailed ? <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> :
                               <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400">Master CSV saved</p>
                          </div>
                          {stage.timestamp && (
                            <span className="text-[9px] font-mono text-slate-400 mt-2">{new Date(stage.timestamp).toLocaleTimeString()}</span>
                          )}
                        </div>
                      );
                    })()}

                    {/* Stage 2: Validated */}
                    {(() => {
                      const stage = currentUpload.pipeline_stages?.validated || (currentUpload.status === 'done' ? { status: 'done', accepted_rows: currentUpload.accepted_rows, rejected_rows: currentUpload.rejected_rows } : { status: currentUpload.status === 'processing' ? 'in_progress' : 'pending' });
                      const isDone = stage.status === 'done';
                      const isProgress = stage.status === 'in_progress';
                      const isFailed = stage.status === 'failed';
                      return (
                        <div className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                          isDone ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-500/30' :
                          isProgress ? 'bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]' :
                          isFailed ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-500/30' :
                          'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200/50 dark:border-slate-700/50 opacity-60'
                        }`}>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] text-slate-700 dark:text-slate-300">2. Validated</span>
                              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> :
                               isProgress ? <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-text)] animate-spin" /> :
                               isFailed ? <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> :
                               <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400">Schema & punch check</p>
                          </div>
                          {isDone && (
                            <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400 mt-2">
                              {stage.accepted_rows?.toLocaleString() ?? currentUpload.accepted_rows} ok / {stage.rejected_rows ?? currentUpload.rejected_rows} rej
                            </span>
                          )}
                        </div>
                      );
                    })()}

                    {/* Stage 3: Mapped */}
                    {(() => {
                      const stage = currentUpload.pipeline_stages?.mapped || (currentUpload.status === 'done' ? { status: 'done', rows_mapped: currentUpload.rows_mapped } : { status: 'pending' });
                      const isDone = stage.status === 'done';
                      const isProgress = stage.status === 'in_progress';
                      const isFailed = stage.status === 'failed';
                      const mapCounts = stage.rows_mapped || {};
                      const totalMapped = Object.values(mapCounts).reduce((a, b) => a + b, 0);
                      return (
                        <div className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                          isDone ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-500/30' :
                          isProgress ? 'bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]' :
                          isFailed ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-500/30' :
                          'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200/50 dark:border-slate-700/50 opacity-60'
                        }`}>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] text-slate-700 dark:text-slate-300">3. Mapped</span>
                              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> :
                               isProgress ? <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-text)] animate-spin" /> :
                               isFailed ? <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> :
                               <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400">Attendance, TS, Claims</p>
                          </div>
                          {isDone && (
                            <span className="text-[9px] font-mono text-slate-500 dark:text-slate-400 mt-2">
                              {totalMapped > 0 ? `${totalMapped.toLocaleString()} rows` : '5 audit tables'}
                            </span>
                          )}
                        </div>
                      );
                    })()}

                    {/* Stage 4: Evaluated */}
                    {(() => {
                      const stage = currentUpload.pipeline_stages?.evaluated || (currentUpload.status === 'done' ? { status: 'done' } : { status: 'pending' });
                      const isDone = stage.status === 'done';
                      const isProgress = stage.status === 'in_progress';
                      const isFailed = stage.status === 'failed';
                      return (
                        <div className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                          isDone ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-500/30' :
                          isProgress ? 'bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]' :
                          isFailed ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-500/30' :
                          'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200/50 dark:border-slate-700/50 opacity-60'
                        }`}>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] text-slate-700 dark:text-slate-300">4. Evaluated</span>
                              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> :
                               isProgress ? <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-text)] animate-spin" /> :
                               isFailed ? <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> :
                               <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400">Rules Engine</p>
                          </div>
                          {isDone && (
                            <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400 mt-2">
                              {stage.total_flags !== undefined ? `${stage.total_flags} findings` : 'Evaluated'}
                            </span>
                          )}
                        </div>
                      );
                    })()}

                    {/* Stage 5: Dashboards updated */}
                    {(() => {
                      const stage = currentUpload.pipeline_stages?.dashboards_updated || (currentUpload.status === 'done' ? { status: 'done' } : { status: 'pending' });
                      const isDone = stage.status === 'done';
                      const isProgress = stage.status === 'in_progress';
                      const isFailed = stage.status === 'failed';
                      return (
                        <div className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                          isDone ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-500/30' :
                          isProgress ? 'bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]' :
                          isFailed ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-500/30' :
                          'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200/50 dark:border-slate-700/50 opacity-60'
                        }`}>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] text-slate-700 dark:text-slate-300">5. Synced</span>
                              {isDone ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> :
                               isProgress ? <RefreshCw className="w-3.5 h-3.5 text-[var(--accent-text)] animate-spin" /> :
                               isFailed ? <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> :
                               <span className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400">Dashboards ready</p>
                          </div>
                          {isDone && (
                            <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400 mt-2">Ready</span>
                          )}
                        </div>
                      );
                    })()}
                  </div>

                  {/* Retry button if failed */}
                  {currentUpload.status === 'failed' && (
                    <div className="mt-3 flex items-center justify-between p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800">
                      <div className="text-xs text-rose-700 dark:text-rose-300">
                        <strong>Pipeline Stalled:</strong> {currentUpload.error_message || 'An error occurred during ingestion.'}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRetryUpload(currentUpload.id)}
                        disabled={isRetrying}
                        className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
                      >
                        <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
                        <span>{isRetrying ? 'Retrying...' : 'Retry Ingestion'}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </GlassCard>

          {/* Rejected Rows Table Card */}
          {rejectedRowsData.length > 0 && (
            <GlassCard className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-rose-700 dark:text-rose-400 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Validation Rejections ({rejectedRowsData.length.toLocaleString()})
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    These rows failed business schema or constraint validation. Valid rows were successfully loaded.
                  </p>
                </div>
                {currentUpload && (
                  <button
                    onClick={() => handleDownloadRejected(currentUpload.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 hover:bg-rose-100 text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Rejected Rows (CSV)
                  </button>
                )}
              </div>

              <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 dark:bg-slate-800/70 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                      <th className="py-2.5 px-3 w-16">Row #</th>
                      <th className="py-2.5 px-3 w-32">Record ID</th>
                      <th className="py-2.5 px-3">Validation Failure Reason</th>
                      <th className="py-2.5 px-3 hidden md:table-cell">Raw Sample</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {rejectedRowsData.slice(0, 50).map((rej, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-mono text-slate-500">{rej.row_num}</td>
                        <td className="py-2.5 px-3 font-mono font-medium text-slate-800 dark:text-slate-200">
                          {rej.record_id}
                        </td>
                        <td className="py-2.5 px-3 text-rose-600 dark:text-rose-400 font-medium">
                          {rej.reason}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400 truncate max-w-xs hidden md:table-cell">
                          {rej.raw_preview}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {rejectedRowsData.length > 50 && (
                <p className="text-[11px] text-slate-400 text-center">
                  Displaying first 50 rejected rows. Use the download button above to inspect the complete rejected CSV.
                </p>
              )}
            </GlassCard>
          )}
        </div>
      )}

      {/* TAB 2: RECORDS VIEWER */}
      {activeTab === 'records' && (
        <div className="space-y-4">
          <GlassCard className="space-y-4">
            {/* Filter Pills for Record Type */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none">
              {RECORD_TYPES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => {
                    setSelectedRecordType(t.id);
                    setRecordsPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                    selectedRecordType === t.id
                      ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {t.label}
                  {stats?.by_record_type?.[t.id] !== undefined && (
                    <span className="ml-1.5 text-[10px] opacity-80">
                      ({stats.by_record_type[t.id].toLocaleString()})
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Search and Department Filter Toolbar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by employee name, ID, or record ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedDepartment}
                  onChange={(e) => {
                    setSelectedDepartment(e.target.value);
                    setRecordsPage(1);
                  }}
                  className="px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  <option value="">All Departments</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Product">Product</option>
                  <option value="Operations">Operations</option>
                  <option value="Sales">Sales</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Finance">Finance</option>
                  <option value="Human Resources">Human Resources</option>
                  <option value="Legal">Legal</option>
                </select>

                <select
                  value={recordsPageSize}
                  onChange={(e) => {
                    setRecordsPageSize(Number(e.target.value));
                    setRecordsPage(1);
                  }}
                  className="px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                >
                  <option value={25}>25 / page</option>
                  <option value={50}>50 / page</option>
                  <option value={100}>100 / page</option>
                </select>
              </div>
            </div>

            {/* Records Table */}
            {loadingRecords ? (
              <SkeletonLoader rows={8} />
            ) : records.length === 0 ? (
              <EmptyState
                icon={TableIcon}
                title="No records found"
                description="No master HR records match your filter criteria or no master CSV file has been uploaded yet."
              />
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-100/70 dark:bg-slate-800/70 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                      <th className="py-2.5 px-3">Record ID</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Employee Name</th>
                      <th className="py-2.5 px-3">Employee ID</th>
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Metrics / Key Data</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {records.map((rec) => {
                      // Format metrics field depending on record_type
                      let metricStr = '-';
                      if (rec.record_type === 'timesheet') {
                        metricStr = `${rec.hours_total ?? 0} hrs`;
                      } else if (rec.record_type === 'leave_request') {
                        metricStr = `${rec.days ?? 0} days (${rec.category || 'general'})`;
                      } else if (rec.record_type === 'employee_profile') {
                        metricStr = rec.monthly_income ? `$${Number(rec.monthly_income).toLocaleString()}/mo` : rec.position || '-';
                      } else if (rec.record_type === 'training') {
                        metricStr = rec.training_program || '-';
                      } else if (rec.record_type === 'engagement_survey') {
                        metricStr = `Score: ${rec.engagement_score ?? '-'}/10`;
                      }

                      const dateVal = rec.event_date || rec.start_date || rec.created_at?.slice(0, 10) || '-';

                      return (
                        <tr key={rec.record_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3 font-mono font-medium text-slate-800 dark:text-slate-200">
                            {rec.record_id}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded-lg text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                              {rec.record_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">
                            {rec.employee_name || rec.applicant_id || '-'}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-500">
                            {rec.employee_id || '-'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400">
                            {rec.department || '-'}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-500">
                            {dateVal}
                          </td>
                          <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300 truncate max-w-xs">
                            {metricStr}
                          </td>
                          <td className="py-2.5 px-3">
                            <StatusPill status={rec.status || 'active'} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {recordsTotal > 0 && (
              <div className="flex items-center justify-between pt-2 text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Showing {((recordsPage - 1) * recordsPageSize + 1).toLocaleString()} to{' '}
                  {Math.min(recordsPage * recordsPageSize, recordsTotal).toLocaleString()} of {recordsTotal.toLocaleString()} rows
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setRecordsPage((p) => Math.max(1, p - 1))}
                    disabled={recordsPage <= 1 || loadingRecords}
                    className="p-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="font-mono px-2">
                    {recordsPage} / {recordsTotalPages}
                  </span>
                  <button
                    onClick={() => setRecordsPage((p) => Math.min(recordsTotalPages, p + 1))}
                    disabled={recordsPage >= recordsTotalPages || loadingRecords}
                    className="p-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </GlassCard>
        </div>
      )}

      {/* TAB 3: UPLOAD HISTORY */}
      {activeTab === 'history' && (
        <GlassCard className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">Master Ingestion Audit History</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Full chronological ledger of uploaded master files, acceptance counts, and throughput speeds.
              </p>
            </div>
            <button
              onClick={loadHistory}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
              title="Refresh History"
            >
              <RefreshCw className={`w-4 h-4 ${loadingHistory ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {loadingHistory ? (
            <SkeletonLoader rows={5} />
          ) : historyList.length === 0 ? (
            <EmptyState
              icon={History}
              title="No upload history"
              description="Upload your first Master HR CSV file to view historical ingestion logs."
            />
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/70 dark:bg-slate-800/70 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                    <th className="py-2.5 px-3">Upload ID</th>
                    <th className="py-2.5 px-3">File Name</th>
                    <th className="py-2.5 px-3">Uploaded At</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Total</th>
                    <th className="py-2.5 px-3 text-right">Accepted</th>
                    <th className="py-2.5 px-3 text-right">Rejected</th>
                    <th className="py-2.5 px-3 text-right">Speed</th>
                    <th className="py-2.5 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {historyList.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                        {item.id.slice(0, 8)}...
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800 dark:text-slate-200">
                        {item.filename}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">
                        {item.uploaded_at ? new Date(item.uploaded_at).toLocaleString() : '-'}
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusPill status={item.status} />
                      </td>
                      <td className="py-2.5 px-3 font-mono text-right font-medium text-slate-800 dark:text-slate-200">
                        {item.total_rows.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-right font-medium text-emerald-600 dark:text-emerald-400">
                        {item.accepted_rows.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-right font-medium text-rose-600 dark:text-rose-400">
                        {item.rejected_rows.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-right text-slate-500">
                        {item.rows_per_second > 0 ? `${item.rows_per_second.toLocaleString()} r/s` : `${item.duration_seconds}s`}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {item.rejected_rows > 0 ? (
                          <button
                            onClick={() => handleDownloadRejected(item.id)}
                            className="p-1 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400"
                            title="Download Rejected Rows CSV"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      )}

      {/* Guarded Reset All Data Confirmation Modal */}
      {resetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-7 shadow-2xl relative border border-rose-500/30">
            <div className="flex items-start justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
                <AlertTriangle className="w-5 h-5" />
                <h3 className="text-base font-bold">Reset All Data</h3>
              </div>
              <button
                onClick={() => setResetModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-4 space-y-3 text-xs text-slate-600 dark:text-slate-300">
              <p>
                This action is <strong className="text-rose-600 dark:text-rose-400">destructive and irreversible</strong>. It will:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-slate-500 dark:text-slate-400">
                <li>Purge all uploaded master HR CSV records and batch history</li>
                <li>Clear all attendance, timesheet, leave, and expense claims</li>
                <li>Reset the compliance audit ledger to its genesis state</li>
                <li>Preserve administrator accounts, personas, and statutory policy definitions</li>
              </ul>
              <p className="font-semibold text-slate-800 dark:text-slate-200 pt-1">
                To confirm, type <span className="font-mono text-rose-600 dark:text-rose-400 font-bold">RESET</span> below:
              </p>
              <input
                type="text"
                value={resetConfirmationInput}
                onChange={(e) => setResetConfirmationInput(e.target.value)}
                placeholder="Type RESET to confirm"
                className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-mono text-xs focus:ring-2 focus:ring-rose-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReset}
                disabled={resetConfirmationInput !== 'RESET' || isResetting}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-40 text-white font-bold text-xs shadow-md transition-all cursor-pointer disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                {isResetting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Resetting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    Confirm Purge
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
