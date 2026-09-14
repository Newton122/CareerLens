"use client";

import { describeApiError } from "@/components/format";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, apiCall, viewFile } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaEye, FaChartLine } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";
import { UpgradeDialog } from "@/components/UpgradePrompt";
import { PAYMENT_REQUIRED, PLAN_CHANGED_EVENT } from "@/components/billing";

interface CV {
  id: number;
  filename: string;
  created_at: string;
}

export default function CVPage() {
  const router = useRouter();
  const [cvs, setCVs] = useState<CV[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const [upgradeMessage, setUpgradeMessage] = useState<string | null>(null);

  const handleViewCV = async (cvId: number) => {
    try {
      await viewFile(`/api/cvs/${cvId}/download`);
    } catch {
      setDialog({ open: true, title: 'Error', message: "Failed to open CV", type: 'error' });
    }
  };

  // Fetches and returns the CV list; callers decide what to do with it.
  const loadCVs = useCallback(async (): Promise<CV[]> => {
    const response = await apiCall("/api/cvs");
    return response.ok ? response.json() : [];
  }, []);

  // State is set only in the promise callbacks, and never after the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    loadCVs()
      .then((data) => {
        if (active) setCVs(data);
      })
      .catch((err) => {
        if (active) setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error fetching CVs", type: 'error' });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadCVs]);

  const handleFileUpload = async (file: File) => {
    const allowedTypes = [".pdf", ".txt", ".png", ".jpg", ".jpeg"];
    const fileExt = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowedTypes.includes(fileExt)) {
      setDialog({ open: true, title: 'Error', message: "PDF, TXT, PNG, JPG, JPEG files only", type: 'error' });
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const token = localStorage.getItem("access_token");
      const response = await fetch(
        `${API_BASE}/api/upload-cv`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        },
      );

      if (response.status === PAYMENT_REQUIRED) {
        // The Free plan's CV limit (enforced by the server, before storing).
        const data = await response.json();
        setUpgradeMessage(describeApiError(data, "Your plan's CV limit is reached."));
        return;
      }
      if (!response.ok) {
        const data = await response.json();
        throw new Error(describeApiError(data, "Upload failed"));
      }

       const result = await response.json();
       window.dispatchEvent(new Event(PLAN_CHANGED_EVENT));  // CV count changed
       setDialog({ open: true, title: 'Success', message: "CV uploaded successfully", type: 'success' });
       setCVs(await loadCVs());
       router.push(`/analyze?cv_id=${result.cv_id}`);
     } catch (err) {
       setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Upload failed", type: 'error' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">My CV</h1>
        <p className="page-subtitle mb-6">
          Upload your CV for AI analysis
        </p>

        {/* Upload */}
        <div
          onDragEnter={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            const files = e.dataTransfer.files;
            if (files[0]) handleFileUpload(files[0]);
          }}
          className={`border-2 border-dashed border-neutral-700 rounded p-4 text-center mb-4 transition ${
            dragActive ? "border-blue-400 bg-neutral-800/50" : "hover:border-neutral-600"
          }`}
        >
          <input
            type="file"
            id="cv-upload"
            accept=".pdf,.txt,.png,.jpg,.jpeg"
            onChange={(e) =>
              e.target.files && handleFileUpload(e.target.files[0])
            }
            className="hidden"
            disabled={uploading}
          />
          <label htmlFor="cv-upload" className="block cursor-pointer">
            {uploading ? (
              <div>
                <p className="text-base text-neutral-200 mb-1">
                  Analyzing your CV with AI...
                </p>
                <p className="text-base text-neutral-500">
                  Extracting skills, experience, education
                </p>
              </div>
            ) : (
              <div>
                <p className="text-base text-neutral-200 mb-1">
                  Drop PDF, TXT, or image or click to browse
                </p>
                <p className="text-base text-neutral-500">
                  AI will analyze your CV and show recommendations
                </p>
              </div>
            )}
          </label>
        </div>

        {/* CVs List */}
        {loading ? (
          <LoadingSpinner />
        ) : cvs.length > 0 ? (
          <div className="space-y-2">
            {cvs.map((cv) => (
              <div
                key={cv.id}
                className="border border-neutral-700/50 rounded p-2"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-base font-medium">{cv.filename}</p>
                    <p className="text-base text-neutral-400">
                      {new Date(cv.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleViewCV(cv.id)}
                      className="btn-secondary"
                    >
                      <FaEye className="w-3 h-3" />
                      View CV
                    </button>
                     <button
                       onClick={() => router.push(`/analyze?cv_id=${cv.id}`)}
                       className="btn-secondary"
                     >
                      <FaChartLine className="w-3 h-3" />
                      Analysis
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-base text-neutral-500">
            No CVs uploaded yet.
          </p>
        )}
      </div>
      <UpgradeDialog message={upgradeMessage} onClose={() => setUpgradeMessage(null)} />
      <MessageDialog
        open={dialog.open}
        onClose={() => setDialog({ ...dialog, open: false })}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
    </div>
  );
}
