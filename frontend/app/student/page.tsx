"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

export default function StudentDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalScore: 0,
    rank: 0,
    dCoins: 0,
    completedTests: 0,
    groups: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const result = await api.students.getStats();
      setStats(result);
    } catch (error) {
      console.log("[v0] Error loading stats:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">
        Welcome, {user?.full_name}!
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm">Total Score</p>
          <p className="text-3xl font-bold text-primary">{stats.totalScore}</p>
        </div>
        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm">Current Rank</p>
          <p className="text-3xl font-bold text-secondary">#{stats.rank}</p>
        </div>
        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm">D'coins</p>
          <p className="text-3xl font-bold text-green-600">{stats.dCoins}</p>
        </div>
        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm">Tests Completed</p>
          <p className="text-3xl font-bold text-blue-600">{stats.completedTests}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-2xl font-bold text-foreground mb-4">My Groups</h2>
          {stats.groups.length === 0 ? (
            <p className="text-muted-foreground">No groups yet</p>
          ) : (
            <ul className="space-y-2">
              {stats.groups.map((group: any) => (
                <li key={group.id} className="p-2 bg-muted rounded">
                  <p className="font-medium">{group.name}</p>
                  <p className="text-sm text-muted-foreground">{group.subject}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-2xl font-bold text-foreground mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button className="w-full px-4 py-2 bg-primary text-primary-foreground rounded hover:opacity-90">
              Take Daily Test
            </button>
            <button className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded hover:opacity-90">
              Join Arena
            </button>
            <button className="w-full px-4 py-2 bg-accent text-accent-foreground rounded hover:opacity-90">
              Learn Vocabulary
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
