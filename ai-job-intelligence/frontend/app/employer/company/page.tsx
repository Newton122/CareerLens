"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import MessageDialog from "@/components/MessageDialog";

interface CompanyProfile {
  id?: string;
  name: string;
  description: string;
  industry: string;
  company_size: string;
  website?: string;
  linkedin?: string;
  twitter?: string;
}

export default function EmployerCompanyPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<CompanyProfile>({
    name: "",
    description: "",
    industry: "",
    company_size: "1-10",
    website: "",
    linkedin: "",
    twitter: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  // State is set only after the request returns, and never once the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await apiCall("/api/company");
        if (response.ok) {
          const data = await response.json();
          if (active) setFormData({
            id: data.id,
            name: data.name || "",
            description: data.description || "",
            industry: data.industry || "",
            company_size: data.company_size || "1-10",
            website: data.website || "",
            linkedin: data.linkedin || "",
            twitter: data.twitter || "",
          });
        }
      } catch {
        // No company profile yet - start with defaults
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const response = await apiCall("/api/company", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setDialog({ open: true, title: 'Success', message: "Company profile saved!", type: 'success' });
      } else {
        const data = await response.json();
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Failed to save profile"), type: 'error' });
      }
    } catch {
      setDialog({ open: true, title: 'Error', message: "Error saving profile", type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-500">Loading company profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">Company Profile</h1>
        <p className="text-base text-neutral-400 mb-3">
          Manage your company information
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="card">
            <h2 className="section-title mb-3">
              Basic Information
            </h2>
            <div className="space-y-2">
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Company Name *"
                className="input-premium"
                required
              />
              <select
                name="industry"
                value={formData.industry}
                onChange={handleChange}
                className="input-premium"
              >
                <option value="">Select industry...</option>
                <option value="Technology">Technology</option>
                <option value="Finance">Finance</option>
                <option value="Healthcare">Healthcare</option>
                <option value="Retail">Retail</option>
                <option value="Manufacturing">Manufacturing</option>
                <option value="Education">Education</option>
                <option value="Other">Other</option>
              </select>
              <select
                name="company_size"
                value={formData.company_size}
                onChange={handleChange}
                className="input-premium"
              >
                <option value="1-10">1-10 Employees</option>
                <option value="11-50">11-50 Employees</option>
                <option value="51-200">51-200 Employees</option>
                <option value="200+">200+ Employees</option>
              </select>
              <input
                type="url"
                name="website"
                value={formData.website || ""}
                onChange={handleChange}
                placeholder="Website URL"
                className="input-premium"
              />
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="About your company..."
                rows={3}
                className="input-premium"
              />
            </div>
          </div>

          <div className="card">
            <h2 className="section-title mb-3">
              Social & Contact
            </h2>
            <div className="space-y-2">
              <input
                type="url"
                name="linkedin"
                value={formData.linkedin || ""}
                onChange={handleChange}
                placeholder="LinkedIn URL"
                className="input-premium"
              />
              <input
                type="text"
                name="twitter"
                value={formData.twitter || ""}
                onChange={handleChange}
                placeholder="Twitter handle (e.g., @company)"
                className="input-premium"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={() => router.push("/employer/dashboard")}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
        <MessageDialog
          open={dialog.open}
          onClose={() => setDialog({ ...dialog, open: false })}
          title={dialog.title}
          message={dialog.message}
          type={dialog.type}
        />
      </div>
    </div>
  );
}
