"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface Profile {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: string;
  avatar_url?: string;
  created_at: string;
}

export default function ProfilesPage() {
  const supabase = createClient();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [editData, setEditData] = useState({
    fullName: "",
    phone: "",
    role: "",
  });

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    if (!supabase) return;
    
    try {
      const { data, error } = await supabase.from("profiles").select("*").order("created_at", { ascending: false });

      if (!error && data) {
        setProfiles(data);
      }
    } catch (error) {
      console.log("[v0] Error loading profiles:", error);
    }
  };

  const handleSelectProfile = (profile: Profile) => {
    setSelectedProfile(profile);
    setEditData({
      fullName: profile.full_name,
      phone: profile.phone || "",
      role: profile.role,
    });
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProfile || !supabase) return;

    setLoading(true);

    try {
      const { error } = await supabase
        .from("profiles")
        .update({
          full_name: editData.fullName,
          phone: editData.phone,
          role: editData.role,
        })
        .eq("id", selectedProfile.id);

      if (!error) {
        console.log("[v0] Profile updated");
        loadProfiles();
        setSelectedProfile(null);
      } else {
        console.log("[v0] Error updating profile:", error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProfile = async (profileId: string) => {
    if (!confirm("Delete this profile? This action cannot be undone.") || !supabase) return;

    try {
      const { error } = await supabase.from("profiles").delete().eq("id", profileId);

      if (!error) {
        loadProfiles();
        setSelectedProfile(null);
        console.log("[v0] Profile deleted");
      }
    } catch (error) {
      console.log("[v0] Error deleting profile:", error);
    }
  };

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">User Profiles</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Profiles List */}
        <div className="lg:col-span-1">
          <div className="bg-background border border-muted rounded-lg p-6 sticky top-6">
            <h2 className="text-xl font-bold text-foreground mb-4">Users</h2>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => handleSelectProfile(profile)}
                  className={`w-full text-left p-3 rounded-lg transition ${
                    selectedProfile?.id === profile.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted/80 text-foreground"
                  }`}
                >
                  <p className="font-medium truncate">{profile.full_name}</p>
                  <p className="text-xs opacity-75 truncate">{profile.email}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Profile Detail */}
        <div className="lg:col-span-2">
          {selectedProfile ? (
            <div className="bg-background border border-muted rounded-lg p-6">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-2xl font-bold text-foreground">Profile Details</h2>
                <button
                  onClick={() => setSelectedProfile(null)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleUpdateProfile} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={editData.fullName}
                    onChange={(e) =>
                      setEditData({ ...editData, fullName: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={selectedProfile.email}
                    disabled
                    className="w-full px-4 py-2 border border-muted rounded-lg bg-muted text-muted-foreground cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    value={editData.phone}
                    onChange={(e) =>
                      setEditData({ ...editData, phone: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Role
                  </label>
                  <select
                    value={editData.role}
                    onChange={(e) =>
                      setEditData({ ...editData, role: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="support_teacher">Support Teacher</option>
                    <option value="admin">Admin</option>
                    <option value="super_admin">Super Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Joined
                  </label>
                  <p className="px-4 py-2 text-muted-foreground">
                    {new Date(selectedProfile.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
                  >
                    {loading ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      handleDeleteProfile(selectedProfile.id)
                    }
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                  >
                    Delete
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <div className="bg-background border border-muted rounded-lg p-12 text-center">
              <p className="text-muted-foreground">Select a user to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
