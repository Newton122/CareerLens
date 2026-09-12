"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import MessageDialog from "@/components/MessageDialog";

export default function PostNewJobPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    description: "",
    location: "",
    salary_min: "",
    salary_max: "",
    employment_type: "full-time",
    required_skills: "",
    experience_required: "",
    education_required: "",
    responsibilities: "",
    benefits: "",
  });
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.title || !formData.description || !formData.location) {
      setDialog({ open: true, title: 'Error', message: "Please fill in all required fields", type: 'error' });
      return;
    }

    setLoading(true);
    try {
      const jobData = {
        title: formData.title,
        description: formData.description,
        location: formData.location,
        salary_min: formData.salary_min ? parseInt(formData.salary_min) : undefined,
        salary_max: formData.salary_max ? parseInt(formData.salary_max) : undefined,
        employment_type: formData.employment_type,
        required_skills: formData.required_skills
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s),
        experience_required: formData.experience_required || undefined,
        education_required: formData.education_required || undefined,
        responsibilities: formData.responsibilities || undefined,
        benefits: formData.benefits
          .split(",")
          .map((b) => b.trim())
          .filter((b) => b),
      };

      const response = await apiCall("/api/jobs", {
        method: "POST",
        body: JSON.stringify(jobData),
      });

      const data = await response.json();

      if (response.ok) {
        setDialog({ open: true, title: 'Success', message: "Job posted successfully!", type: 'success' });
        setTimeout(() => router.push("/employer/jobs"), 1500);
      } else {
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Failed to create job posting"), type: 'error' });
      }
    } catch {
      setDialog({ open: true, title: 'Error', message: "Error creating job posting", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">Post a New Job</h1>
        <p className="page-subtitle mb-6">
          Create a job posting to attract talented candidates
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Basic Info */}
          <div className="card">
            <h2 className="section-title mb-3">
              Basic Information
            </h2>
            <div className="space-y-2">
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Job Title *"
                className="input-premium"
                required
              />
              <input
                type="text"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="Location *"
                className="input-premium"
                required
              />
              <select
                name="employment_type"
                value={formData.employment_type}
                onChange={handleChange}
                className="input-premium"
              >
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
                <option value="contract">Contract</option>
                <option value="freelance">Freelance</option>
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  name="salary_min"
                  value={formData.salary_min}
                  onChange={handleChange}
                  placeholder="Min Salary"
                  className="input-premium"
                />
                <input
                  type="number"
                  name="salary_max"
                  value={formData.salary_max}
                  onChange={handleChange}
                  placeholder="Max Salary"
                  className="input-premium"
                />
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="card">
            <h2 className="section-title mb-3">
              Job Description
            </h2>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Describe the role..."
              rows={4}
              className="input-premium"
              required
            />
            <textarea
              name="responsibilities"
              value={formData.responsibilities}
              onChange={handleChange}
              placeholder="Key responsibilities..."
              rows={3}
              className="input-premium mt-2"
            />
          </div>

          {/* Requirements */}
          <div className="card">
            <h2 className="section-title mb-3">
              Requirements
            </h2>
            <input
              type="text"
              name="required_skills"
              value={formData.required_skills}
              onChange={handleChange}
              placeholder="Required skills (comma-separated)"
              className="input-premium"
            />
            <input
              type="text"
              name="experience_required"
              value={formData.experience_required}
              onChange={handleChange}
              placeholder="Experience required (e.g., 3-5 years)"
              className="input-premium mt-2"
            />
            <input
              type="text"
              name="education_required"
              value={formData.education_required}
              onChange={handleChange}
              placeholder="Education required"
              className="input-premium mt-2"
            />
          </div>

          {/* Benefits */}
          <div className="card">
            <h2 className="section-title mb-3">
              Benefits
            </h2>
            <input
              type="text"
              name="benefits"
              value={formData.benefits}
              onChange={handleChange}
              placeholder="Benefits (comma-separated)"
              className="input-premium"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
            >
              {loading ? "Creating..." : "Post Job"}
            </button>
            <button
              type="button"
              onClick={() => router.push("/employer/jobs")}
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
