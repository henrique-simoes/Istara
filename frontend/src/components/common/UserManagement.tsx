"use client";

import { useEffect, useState, useRef } from "react";
import {
  Users,
  UserPlus,
  Trash2,
  Eye,
  EyeOff,
  Check,
  Copy,
  ChevronDown,
  Shield,
  BookOpen,
  EyeIcon,
  X,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { users as usersApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { ListSkeleton } from "./LoadingSkeleton";
import ConfirmDialog from "./ConfirmDialog";
import type { ReclawUser } from "@/lib/types";

// --- Role config ---

const ROLE_CONFIG: Record<
  string,
  { label: string; description: string; color: string; bgColor: string; icon: typeof Shield }
> = {
  admin: {
    label: "Admin",
    description: "Full system access",
    color: "text-purple-700 dark:text-purple-300",
    bgColor: "bg-purple-100 dark:bg-purple-900/30",
    icon: Shield,
  },
  researcher: {
    label: "Researcher",
    description: "Can create and edit projects",
    color: "text-blue-700 dark:text-blue-300",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
    icon: BookOpen,
  },
  viewer: {
    label: "Viewer",
    description: "Read-only access",
    color: "text-slate-600 dark:text-slate-400",
    bgColor: "bg-slate-100 dark:bg-slate-700",
    icon: EyeIcon,
  },
};

// --- Role Badge ---

function RoleBadge({ role }: { role: string }) {
  const config = ROLE_CONFIG[role] || ROLE_CONFIG.viewer;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5",
        config.bgColor,
        config.color
      )}
    >
      {config.label}
    </span>
  );
}

// --- Role Dropdown ---

function RoleDropdown({
  currentRole,
  onChange,
  disabled,
}: {
  currentRole: string;
  onChange: (role: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={cn(
          "inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5 transition-colors",
          ROLE_CONFIG[currentRole]?.bgColor || "bg-slate-100 dark:bg-slate-700",
          ROLE_CONFIG[currentRole]?.color || "text-slate-600",
          disabled
            ? "opacity-60 cursor-not-allowed"
            : "hover:ring-2 hover:ring-istara-300 cursor-pointer"
        )}
        aria-label="Change role"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {ROLE_CONFIG[currentRole]?.label || currentRole}
        {!disabled && <ChevronDown size={12} />}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1 z-20 w-56 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1"
          role="listbox"
          aria-label="Select role"
        >
          {Object.entries(ROLE_CONFIG).map(([roleKey, config]) => (
            <button
              key={roleKey}
              role="option"
              aria-selected={currentRole === roleKey}
              onClick={() => {
                if (roleKey !== currentRole) onChange(roleKey);
                setOpen(false);
              }}
              className={cn(
                "w-full text-left px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 flex items-center gap-3 transition-colors",
                currentRole === roleKey && "bg-slate-50 dark:bg-slate-700/30"
              )}
            >
              <config.icon size={14} className={config.color} />
              <div className="flex-1">
                <div className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
                  {config.label}
                  {currentRole === roleKey && (
                    <Check size={12} className="text-istara-600" />
                  )}
                </div>
                <div className="text-xs text-slate-500">{config.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Avatar ---

function UserAvatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const letter = (name || "?").charAt(0).toUpperCase();
  const colors = [
    "bg-istara-100 text-istara-700 dark:bg-istara-900/40 dark:text-istara-300",
    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    "bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300",
  ];
  const colorIndex = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % colors.length;

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full font-semibold shrink-0",
        size === "sm" ? "w-7 h-7 text-xs" : "w-9 h-9 text-sm",
        colors[colorIndex]
      )}
      aria-hidden="true"
    >
      {letter}
    </div>
  );
}

// --- Success Card ---

function CredentialsCard({
  username,
  password,
  onDismiss,
}: {
  username: string;
  password: string;
  onDismiss: () => void;
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Clipboard API not available
    }
  };

  return (
    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Check size={16} className="text-green-600" />
          <span className="text-sm font-medium text-green-800 dark:text-green-300">
            Team member invited successfully
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="p-0.5 rounded hover:bg-green-100 dark:hover:bg-green-800/40 text-green-600"
          aria-label="Dismiss success message"
        >
          <X size={14} />
        </button>
      </div>
      <p className="text-xs text-green-700 dark:text-green-400 mb-3">
        Share these credentials with your team member. They can change their password after first login.
      </p>
      <div className="space-y-2">
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 rounded px-3 py-1.5 border border-green-200 dark:border-green-800">
          <div>
            <span className="text-xs text-slate-500">Username: </span>
            <span className="text-sm font-mono font-medium text-slate-900 dark:text-white">
              {username}
            </span>
          </div>
          <button
            onClick={() => copyToClipboard(username, "username")}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600"
            aria-label="Copy username"
          >
            {copiedField === "username" ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
          </button>
        </div>
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 rounded px-3 py-1.5 border border-green-200 dark:border-green-800">
          <div>
            <span className="text-xs text-slate-500">Password: </span>
            <span className="text-sm font-mono font-medium text-slate-900 dark:text-white">
              {password}
            </span>
          </div>
          <button
            onClick={() => copyToClipboard(password, "password")}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600"
            aria-label="Copy password"
          >
            {copiedField === "password" ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Invite Form ---

function InviteForm({
  onCreated,
  onCancel,
}: {
  onCreated: (user: ReclawUser, password: string) => void;
  onCancel: () => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("researcher");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const usernameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    usernameRef.current?.focus();
  }, []);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!username.trim()) newErrors.username = "Username is required";
    else if (!/^[a-zA-Z0-9_.-]+$/.test(username.trim()))
      newErrors.username = "Only letters, numbers, dots, dashes, and underscores";
    if (!email.trim()) newErrors.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      newErrors.email = "Enter a valid email address";
    if (!password) newErrors.password = "Password is required";
    else if (password.length < 6) newErrors.password = "At least 6 characters";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    setErrors({});
    try {
      const user = await usersApi.create({
        username: username.trim(),
        email: email.trim(),
        password,
        display_name: displayName.trim() || undefined,
      });
      onCreated(user, password);
    } catch (err: any) {
      setErrors({ form: err.message || "Failed to create account" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 mb-4 border border-slate-200 dark:border-slate-700"
    >
      <h4 className="text-sm font-medium text-slate-900 dark:text-white mb-3">
        Invite a new team member
      </h4>

      {errors.form && (
        <div className="mb-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
          {errors.form}
        </div>
      )}

      <div className="space-y-3">
        {/* Display Name */}
        <div>
          <label htmlFor="invite-display-name" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
            Display Name <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <input
            id="invite-display-name"
            type="text"
            placeholder="e.g., Sarah Chen"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent"
          />
        </div>

        {/* Username */}
        <div>
          <label htmlFor="invite-username" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
            Username <span className="text-red-500">*</span>
          </label>
          <input
            ref={usernameRef}
            id="invite-username"
            type="text"
            placeholder="e.g., sarah"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (errors.username) setErrors((prev) => ({ ...prev, username: "" }));
            }}
            className={cn(
              "w-full px-3 py-2 text-sm rounded-lg border bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent",
              errors.username
                ? "border-red-400 dark:border-red-600 focus:ring-red-500"
                : "border-slate-300 dark:border-slate-600 focus:ring-istara-500"
            )}
            aria-invalid={!!errors.username}
            aria-describedby={errors.username ? "invite-username-error" : undefined}
          />
          {errors.username && (
            <p id="invite-username-error" className="mt-1 text-xs text-red-600 dark:text-red-400">
              {errors.username}
            </p>
          )}
        </div>

        {/* Email */}
        <div>
          <label htmlFor="invite-email" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
            Email <span className="text-red-500">*</span>
          </label>
          <input
            id="invite-email"
            type="email"
            placeholder="e.g., sarah@company.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
            }}
            className={cn(
              "w-full px-3 py-2 text-sm rounded-lg border bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent",
              errors.email
                ? "border-red-400 dark:border-red-600 focus:ring-red-500"
                : "border-slate-300 dark:border-slate-600 focus:ring-istara-500"
            )}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? "invite-email-error" : undefined}
          />
          {errors.email && (
            <p id="invite-email-error" className="mt-1 text-xs text-red-600 dark:text-red-400">
              {errors.email}
            </p>
          )}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="invite-password" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
            Password <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <input
              id="invite-password"
              type={showPassword ? "text" : "password"}
              placeholder="Temporary password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errors.password) setErrors((prev) => ({ ...prev, password: "" }));
              }}
              className={cn(
                "w-full px-3 py-2 pr-10 text-sm rounded-lg border bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent",
                errors.password
                  ? "border-red-400 dark:border-red-600 focus:ring-red-500"
                  : "border-slate-300 dark:border-slate-600 focus:ring-istara-500"
              )}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? "invite-password-error" : undefined}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.password && (
            <p id="invite-password-error" className="mt-1 text-xs text-red-600 dark:text-red-400">
              {errors.password}
            </p>
          )}
        </div>

        {/* Role Selector */}
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-2">
            Role
          </label>
          <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Select role for new team member">
            {Object.entries(ROLE_CONFIG).map(([roleKey, config]) => (
              <button
                key={roleKey}
                type="button"
                role="radio"
                aria-checked={role === roleKey}
                onClick={() => setRole(roleKey)}
                className={cn(
                  "flex flex-col items-center gap-1 p-2.5 rounded-lg border text-center transition-all",
                  role === roleKey
                    ? "border-istara-500 bg-istara-50 dark:bg-istara-900/20 ring-1 ring-istara-500"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                )}
              >
                <config.icon
                  size={16}
                  className={role === roleKey ? "text-istara-600" : "text-slate-400"}
                />
                <span
                  className={cn(
                    "text-xs font-medium",
                    role === roleKey
                      ? "text-istara-700 dark:text-istara-300"
                      : "text-slate-700 dark:text-slate-300"
                  )}
                >
                  {config.label}
                </span>
                <span className="text-[10px] text-slate-500 leading-tight">
                  {config.description}
                </span>
                {roleKey === "researcher" && role !== roleKey && (
                  <span className="text-[10px] text-istara-600 dark:text-istara-400 font-medium">
                    Recommended
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Helper text */}
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Share the username and password with your team member. They can change their password after first login.
        </p>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={onCancel}
            className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              submitting
                ? "bg-istara-400 text-white cursor-not-allowed"
                : "bg-istara-600 hover:bg-istara-700 text-white"
            )}
          >
            {submitting ? "Creating..." : "Create Account"}
          </button>
        </div>
      </div>
    </form>
  );
}

// --- Main Component ---

export default function UserManagement() {
  const { user: currentUser, teamMode } = useAuthStore();
  const isAdmin = currentUser?.role === "admin";

  const [userList, setUserList] = useState<ReclawUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState<{
    username: string;
    password: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ReclawUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const data = await usersApi.list();
      setUserList(data);
      setError(null);
    } catch (err: any) {
      // Non-admin or team mode disabled -- silently handle
      if (err.message?.includes("401") || err.message?.includes("403")) {
        setUserList([]);
      } else {
        setError(err.message || "Could not load team members");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (teamMode) {
      fetchUsers();
    } else {
      setLoading(false);
    }
  }, [teamMode]);

  // Don't render if team mode is not active
  if (!teamMode) return null;

  const handleCreated = (user: ReclawUser, password: string) => {
    setCreatedCredentials({ username: user.username, password });
    setShowInviteForm(false);
    fetchUsers();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await usersApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      await fetchUsers();
    } catch (err: any) {
      setError(err.message || "Failed to remove team member");
      setDeleteTarget(null);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await usersApi.changeRole(userId, newRole);
      await fetchUsers();
    } catch (err: any) {
      setError(err.message || "Failed to update role");
    }
  };

  const otherUsers = userList.filter((u) => u.id !== currentUser?.id);
  const isEmpty = otherUsers.length === 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Users size={18} />
          Team Members
        </h3>
        {isAdmin && !showInviteForm && (
          <button
            onClick={() => {
              setShowInviteForm(true);
              setCreatedCredentials(null);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors"
            aria-label="Invite a new team member"
          >
            <UserPlus size={14} />
            Invite Member
          </button>
        )}
      </div>

      {/* Success card */}
      {createdCredentials && (
        <CredentialsCard
          username={createdCredentials.username}
          password={createdCredentials.password}
          onDismiss={() => setCreatedCredentials(null)}
        />
      )}

      {/* Invite form */}
      {showInviteForm && (
        <InviteForm
          onCreated={handleCreated}
          onCancel={() => setShowInviteForm(false)}
        />
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-800/40"
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <ListSkeleton count={3} />
      ) : (
        <>
          {/* Non-admin notice */}
          {!isAdmin && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 bg-slate-50 dark:bg-slate-900 rounded-lg px-3 py-2">
              Contact your admin to manage team members.
            </p>
          )}

          {/* Current user */}
          {currentUser && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-istara-50/50 dark:bg-istara-900/10 border border-istara-100 dark:border-istara-900/30 mb-2">
              <UserAvatar name={currentUser.display_name || currentUser.username} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-900 dark:text-white truncate">
                    {currentUser.display_name || currentUser.username}
                  </span>
                  <span className="text-xs text-istara-600 dark:text-istara-400 font-medium shrink-0">
                    (You)
                  </span>
                </div>
                <p className="text-xs text-slate-500 truncate">{currentUser.email}</p>
              </div>
              <RoleBadge role={currentUser.role} />
            </div>
          )}

          {/* Other users */}
          {isEmpty && !loading && !error ? (
            <div className="text-center py-6">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                You&apos;re the only team member.
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Invite a team member to collaborate on research projects.
              </p>
              {isAdmin && !showInviteForm && (
                <button
                  onClick={() => {
                    setShowInviteForm(true);
                    setCreatedCredentials(null);
                  }}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors"
                  aria-label="Invite a new team member"
                >
                  <UserPlus size={14} />
                  Invite Member
                </button>
              )}
            </div>
          ) : error && !loading ? (
            <div className="text-center py-4">
              <p className="text-sm text-red-600 dark:text-red-400 mb-2">{error}</p>
              <button
                onClick={fetchUsers}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors"
              >
                <RefreshCw size={14} />
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-1">
              {otherUsers.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors group"
                >
                  <UserAvatar name={u.display_name || u.username} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-slate-900 dark:text-white truncate block">
                      {u.display_name || u.username}
                    </span>
                    <p className="text-xs text-slate-500 truncate">{u.email}</p>
                  </div>

                  {/* Role -- dropdown for admins, badge for everyone else */}
                  {isAdmin ? (
                    <RoleDropdown
                      currentRole={u.role}
                      onChange={(newRole) => handleRoleChange(u.id, newRole)}
                    />
                  ) : (
                    <RoleBadge role={u.role} />
                  )}

                  {/* Delete button -- admin only, can't delete self */}
                  {isAdmin && (
                    <button
                      onClick={() => setDeleteTarget(u)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all"
                      aria-label={`Remove ${u.display_name || u.username}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Confirm delete dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Remove team member"
        message={`Are you sure you want to remove ${deleteTarget?.display_name || deleteTarget?.username}? They will lose access to all projects and data.`}
        confirmLabel="Remove"
        cancelLabel="Keep"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
