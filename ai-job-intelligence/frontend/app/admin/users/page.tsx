"use client";
import { useEffect, useState } from "react";
import { apiCall } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaSearch, FaFilter } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface UserDetail {
  id: number;
  email: string;
  role: string;
  company?: string;
  name?: string;
  cvs: Array<{ id: number; filename: string }>;
  applications: Array<{ id: number; job_title: string; status: string }>;
  saved_jobs_count: number;
}

interface UserSummary {
  id: number;
  email: string;
  role: string;
  cv_count: number;
  jobs_posted: number;
  applications: number;
  created_at: string;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const [confirmState, setConfirmState] = useState<{ open: boolean; message: string; onConfirm: () => void }>({
    open: false,
    message: '',
    onConfirm: () => {},
  });

  // State is set only after the request returns, and never once the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await apiCall("/api/admin/users");
        if (response.ok) {
          const data = await response.json();
          if (active) setUsers(data);
        }
      } catch {
        if (active) setDialog({ open: true, title: 'Error', message: "Error loading users", type: 'error' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const fetchUserDetail = async (userId: number) => {
    try {
      const response = await apiCall(`/api/admin/users/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedUser(data);
        setShowDetail(true);
      }
    } catch {
      setDialog({ open: true, title: 'Error', message: "Error loading user details", type: 'error' });
    }
  };

  const filteredUsers = users.filter((user) => {
    const matchesSearch = user.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "" || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleDelete = async (userId: number) => {
    setConfirmState({
      open: true,
      message: "Are you sure you want to delete this user?",
      onConfirm: async () => {
        try {
          const response = await apiCall(`/api/admin/users/${userId}`, {
            method: "DELETE",
          });
          if (response.ok) {
            setDialog({ open: true, title: 'Success', message: "User deleted", type: 'success' });
            setUsers(users.filter((u) => u.id !== userId));
          }
        } catch {
          setDialog({ open: true, title: 'Error', message: "Error deleting user", type: 'error' });
        }
      },
    });
  };

  if (showDetail && selectedUser) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <button
            onClick={() => setShowDetail(false)}
            className="text-sm text-blue-600 mb-3"
          >
            Back to Users
          </button>

          <h1 className="text-sm font-bold text-rose-300 mb-1">
            User Details
          </h1>

          <div className="card mb-4">
            <div className="flex justify-between">
              <div>
                <p className="text-sm font-medium">{selectedUser.email}</p>
                <p className="text-sm text-neutral-400">
                  Name: {selectedUser.name || "N/A"}
                </p>
                <p className="text-sm text-neutral-400">
                  Company: {selectedUser.company || "N/A"}
                </p>
              </div>
              <span className={`text-xs px-1.5 py-0.5 rounded border ${getRoleTag(selectedUser.role)}`}>
                {selectedUser.role}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="card">
              <h2 className="section-title mb-2">
                Applications ({selectedUser.applications.length})
              </h2>
              <div className="space-y-1">
                {selectedUser.applications.map((app) => (
                  <div key={app.id} className="text-sm">
                    <p className="font-medium">{app.job_title}</p>
                    <p className="text-neutral-400">{app.status}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h2 className="section-title mb-2">
                CVs ({selectedUser.cvs.length})
              </h2>
              <div className="space-y-1">
                {selectedUser.cvs.map((cv) => (
                  <div key={cv.id} className="text-sm text-neutral-200">
                    {cv.filename}
                  </div>
                ))}
              </div>
              <p className="text-sm text-neutral-400 mt-2">
                Saved jobs: {selectedUser.saved_jobs_count}
              </p>
          </div>
        </div>
        <MessageDialog
          open={dialog.open}
          onClose={() => setDialog({ ...dialog, open: false })}
          title={dialog.title}
          message={dialog.message}
          type={dialog.type}
        />
        <MessageDialog
          open={confirmState.open}
          onClose={() => setConfirmState({ ...confirmState, open: false })}
          title="Confirm"
          message={confirmState.message}
          type="warning"
          confirmText="Yes"
          cancelText="No"
          onConfirm={confirmState.onConfirm}
        />
      </div>
    </div>
  );
}

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="text-sm font-bold mb-1 text-rose-300">User Management</h1>
        <p className="text-sm text-neutral-400 mb-3">
          Manage all users on the platform
        </p>

        <div className="mb-3">
          <div className="flex items-center gap-1 border border-neutral-700 rounded px-2">
            <FaSearch className="w-3 h-3 text-neutral-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by email..."
              className="w-full px-2 py-2 text-base border-0 focus:outline-none focus:ring-0"
            />
          </div>
        </div>

        <div className="flex gap-1 mb-3 flex-wrap items-center">
          <FaFilter className="w-3 h-3 text-neutral-500" />
          <span className="text-sm text-neutral-400 mr-1">Role:</span>
          <button
            onClick={() => setRoleFilter("")}
            className={`text-sm px-2 py-1 border rounded ${
              roleFilter === ""
                ? "bg-red-600 text-white border-red-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setRoleFilter("admin")}
            className={`text-sm px-2 py-1 border rounded ${
              roleFilter === "admin"
                ? "bg-red-600 text-white border-red-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Admin
          </button>
          <button
            onClick={() => setRoleFilter("employer")}
            className={`text-sm px-2 py-1 border rounded ${
              roleFilter === "employer"
                ? "bg-emerald-600 text-white border-emerald-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Employer
          </button>
          <button
            onClick={() => setRoleFilter("job_seeker")}
            className={`text-sm px-2 py-1 border rounded ${
              roleFilter === "job_seeker"
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Job Seeker
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : filteredUsers.length > 0 ? (
          <div className="border border-neutral-700/50 rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-800/50 border-b border-neutral-700/50">
                <tr>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    Email
                  </th>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    Role
                  </th>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    CVs
                  </th>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    Jobs
                  </th>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    Apps
                  </th>
                  <th className="px-3 py-1.5 text-left font-medium text-neutral-200">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr
                    key={user.id}
                    className="border-t border-neutral-700/50 hover:bg-neutral-700/50"
                  >
                    <td className="px-3 py-1.5 text-sm">{user.email}</td>
                    <td className="px-3 py-1.5">
                      <span className={`text-xs px-1.5 py-0.5 rounded border ${getRoleTag(user.role)}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-neutral-400">{user.cv_count}</td>
                    <td className="px-3 py-1.5 text-neutral-400">{user.jobs_posted}</td>
                    <td className="px-3 py-1.5 text-neutral-400">{user.applications}</td>
                    <td className="px-3 py-1.5">
                      <div className="flex gap-1">
                        <button
                          onClick={() => fetchUserDetail(user.id)}
                          className="text-xs px-1.5 py-0.5 text-blue-600 hover:text-blue-300"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleDelete(user.id)}
                          className="text-xs px-1.5 py-0.5 text-red-600 hover:text-rose-300"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">No users found</p>
        )}
        <MessageDialog
          open={dialog.open}
          onClose={() => setDialog({ ...dialog, open: false })}
          title={dialog.title}
          message={dialog.message}
          type={dialog.type}
        />
        <MessageDialog
          open={confirmState.open}
          onClose={() => setConfirmState({ ...confirmState, open: false })}
          title="Confirm"
          message={confirmState.message}
          type="warning"
          confirmText="Yes"
          cancelText="No"
          onConfirm={confirmState.onConfirm}
        />
      </div>
    </div>
  );
}

function getRoleTag(role: string) {
  switch (role) {
    case "admin":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "employer":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    default:
      return "bg-blue-500/15 text-blue-300 border-blue-500/30";
  }
}
