"use client";

import { useState } from "react";

export default function GroupsPage() {
  const [groups, setGroups] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    subject: "",
    level: "",
    teacher: "",
    description: "",
  });

  const handleAddGroup = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("[v0] Adding group:", formData);
    setFormData({
      name: "",
      subject: "",
      level: "",
      teacher: "",
      description: "",
    });
    setShowForm(false);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-primary">Groups Management</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-2 bg-accent text-accent-foreground rounded-lg hover:opacity-90 transition"
        >
          {showForm ? "Cancel" : "Create Group"}
        </button>
      </div>

      {showForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">Create New Group</h2>
          <form onSubmit={handleAddGroup} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Group Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="e.g., Advanced English Group"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Subject
                </label>
                <select
                  value={formData.subject}
                  onChange={(e) =>
                    setFormData({ ...formData, subject: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                  required
                >
                  <option value="">Select Subject</option>
                  <option value="english">English</option>
                  <option value="math">Math</option>
                  <option value="science">Science</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Level
                </label>
                <select
                  value={formData.level}
                  onChange={(e) =>
                    setFormData({ ...formData, level: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                  required
                >
                  <option value="">Select Level</option>
                  <option value="a1">A1</option>
                  <option value="a2">A2</option>
                  <option value="b1">B1</option>
                  <option value="b2">B2</option>
                  <option value="c1">C1</option>
                  <option value="c2">C2</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Teacher
                </label>
                <input
                  type="text"
                  value={formData.teacher}
                  onChange={(e) =>
                    setFormData({ ...formData, teacher: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Teacher name"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-accent h-32"
                placeholder="Group description"
              />
            </div>

            <button
              type="submit"
              className="w-full px-4 py-2 bg-accent text-accent-foreground rounded-lg hover:opacity-90 transition"
            >
              Create Group
            </button>
          </form>
        </div>
      )}

      {/* Groups List */}
      <div className="bg-background border border-muted rounded-lg p-6">
        <h2 className="text-2xl font-bold text-foreground mb-6">Groups List</h2>

        {groups.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No groups created yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Group cards will be displayed here */}
          </div>
        )}
      </div>
    </div>
  );
}
