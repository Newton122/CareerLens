"use client";

import { useState, useEffect } from "react";
import { API_BASE, apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import { useAuth } from "@/components/AuthProvider";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaUser, FaBriefcase, FaSave, FaUpload, FaTrash, FaGlobe } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";



interface ProfileData {
  name: string;
  email: string;
  role: string;
  company: string;
  description: string;
  industry: string;
  company_size: string;
  website: string;
  linkedin: string;
  twitter: string;
  image_url: string;
}

export default function ProfilePage() {
  const { role, email: authEmail } = useAuth();
  const [profile, setProfile] = useState<ProfileData>({
    name: "",
    email: "",
    role: "job_seeker",
    company: "",
    description: "",
    industry: "",
    company_size: "",
    website: "",
    linkedin: "",
    twitter: "",
    image_url: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const response = await apiCall("/api/profile");
      if (response.ok) {
        const data = await response.json();
        setProfile({
          name: data.name || "",
          email: data.email || authEmail || "",
          role: data.role || role || "job_seeker",
          company: data.company || "",
          description: data.description || "",
          industry: data.industry || "",
          company_size: data.company_size || "",
          website: data.website || "",
          linkedin: data.linkedin || "",
          twitter: data.twitter || "",
          image_url: data.image_url || "",
        });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error loading profile", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const response = await apiCall("/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          name: profile.name,
          company: profile.company,
          description: profile.description,
          industry: profile.industry,
          company_size: profile.company_size,
          website: profile.website,
          linkedin: profile.linkedin,
          twitter: profile.twitter,
          image_url: profile.image_url,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setDialog({ open: true, title: 'Success', message: "Profile saved successfully!", type: 'success' });
        setProfile((prev) => ({ ...prev, ...data }));
      } else {
        const err = await response.json();
        setDialog({ open: true, title: 'Error', message: err.detail || "Save failed", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error saving profile", type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setDialog({ open: true, title: 'Error', message: "Only image files are allowed", type: 'error' });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setDialog({ open: true, title: 'Error', message: "File too large (max 5MB)", type: 'error' });
      return;
    }

    setUploading(true);
    try {
      const token = localStorage.getItem("access_token");
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/upload-image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setProfile((prev) => ({ ...prev, image_url: data.image_url }));
        setDialog({ open: true, title: 'Success', message: "Image uploaded", type: 'success' });
      } else {
        const data = await response.json();
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Upload failed"), type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error uploading image", type: 'error' });
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveImage = () => {
    setProfile((prev) => ({ ...prev, image_url: "" }));
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  const isEmployer = profile.role === "employer";
  const isJobSeeker = profile.role === "job_seeker";

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <h1 className="text-sm font-bold mb-1">Your Profile</h1>
        <p className="text-sm text-neutral-400 mb-4">
          Manage your personal and professional information
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Basic Info */}
          <div className="card">
            <h2 className="section-title mb-3 flex items-center gap-2">
              <FaUser className="w-3 h-3" />
              Basic Info
            </h2>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">Name</label>
                <input
                  type="text"
                  name="name"
                  value={profile.name}
                  onChange={handleChange}
                  placeholder="Full name"
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">Email</label>
                <input
                  type="email"
                  value={profile.email}
                  disabled
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded bg-neutral-800/50"
                />
              </div>
            </div>
          </div>

          {/* Profile Image */}
          <div className="card">
            <h2 className="section-title mb-3 flex items-center gap-2">
              <FaUser className="w-3 h-3" />
              Profile Image
            </h2>
            <div className="flex items-center gap-4">
              {profile.image_url ? (
                <div className="flex items-center gap-2">
                  <img
                    src={`${API_BASE}${profile.image_url}`}
                    alt="Profile"
                    className="w-16 h-16 rounded-full object-cover border border-neutral-700"
                  />
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    className="text-sm px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-700/50 flex items-center gap-1"
                  >
                    <FaTrash className="w-3 h-3" />
                    Remove
                  </button>
                </div>
              ) : (
                <div className="w-16 h-16 rounded-full border-2 border-dashed border-neutral-700 flex items-center justify-center">
                  <FaUser className="w-5 h-5 text-neutral-500" />
                </div>
              )}
              <div>
                <label className="flex items-center gap-2 text-sm px-3 py-2 border border-neutral-700 rounded cursor-pointer hover:bg-neutral-700/50">
                  <FaUpload className="w-3 h-3" />
                  {uploading ? "Uploading..." : "Upload Image"}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    disabled={uploading}
                    className="hidden"
                  />
                </label>
                <p className="text-xs text-neutral-500 mt-1">PNG, JPG up to 5MB</p>
              </div>
            </div>
          </div>

          {/* Professional Info */}
          <div className="card">
            <h2 className="section-title mb-3 flex items-center gap-2">
              <FaBriefcase className="w-3 h-3" />
              Professional Info
            </h2>
            <div className="space-y-2">
              {isEmployer && (
                <div>
                  <label className="block text-sm text-neutral-300 mb-0.5">Company</label>
                  <input
                    type="text"
                    name="company"
                    value={profile.company}
                    onChange={handleChange}
                    placeholder="Company name"
                    className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">
                  {isEmployer ? "About your company" : "About you"}
                </label>
                <textarea
                  name="description"
                  value={profile.description}
                  onChange={handleChange}
                  placeholder={isEmployer ? "Company description..." : "About you..."}
                 rows={3}
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              {isEmployer && (
                <>
                  <div>
                    <label className="block text-sm text-neutral-300 mb-0.5">Industry</label>
                    <input
                      type="text"
                      name="industry"
                      value={profile.industry}
                      onChange={handleChange}
                      placeholder="e.g. Technology, Finance, Healthcare"
                      className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-neutral-300 mb-0.5">Company Size</label>
                    <input
                      type="text"
                      name="company_size"
                      value={profile.company_size}
                      onChange={handleChange}
                      placeholder="e.g. 1-10, 11-50"
                      className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Contact & Links */}
          <div className="card">
            <h2 className="section-title mb-3 flex items-center gap-2">
              <FaGlobe className="w-3 h-3" />
              Contact & Links
            </h2>
            <div className="space-y-2">
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">Website</label>
                <input
                  type="url"
                  name="website"
                  value={profile.website}
                  onChange={handleChange}
                  placeholder="https://..."
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">LinkedIn</label>
                <input
                  type="url"
                  name="linkedin"
                  value={profile.linkedin}
                  onChange={handleChange}
                  placeholder="https://linkedin.com/in/..."
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-300 mb-0.5">Twitter</label>
                <input
                  type="url"
                  name="twitter"
                  value={profile.twitter}
                  onChange={handleChange}
                  placeholder="https://twitter.com/..."
                  className="w-full px-3 py-2 text-sm border border-neutral-700 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Skills Section (only for job seekers) */}
          {isJobSeeker && (
            <div className="card">
              <h2 className="section-title mb-3 flex items-center gap-2">
                <FaUser className="w-3 h-3" />
                Skills (from CV)
              </h2>
              <p className="text-xs text-neutral-400 mb-1">
                Skills are automatically extracted from your uploaded CV.
                Upload or update your CV to change your skills.
              </p>
              <div className="text-sm text-neutral-400">
                Your skills will be analyzed when you upload your CV.
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 text-sm px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            <FaSave className="w-3 h-3" />
            {saving ? "Saving..." : "Save Profile"}
          </button>
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
