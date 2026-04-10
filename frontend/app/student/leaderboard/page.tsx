"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function LeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLeaderboard();
  }, []);

  const loadLeaderboard = async () => {
    try {
      const result = await api.leaderboard.getGlobal();
      setLeaderboard(result);
    } catch (error) {
      console.log("[v0] Error loading leaderboard:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">Global Leaderboard</h1>

      <div className="bg-background border border-muted rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-muted bg-muted">
              <th className="text-left px-6 py-3 font-semibold">Rank</th>
              <th className="text-left px-6 py-3 font-semibold">Student</th>
              <th className="text-left px-6 py-3 font-semibold">Score</th>
              <th className="text-left px-6 py-3 font-semibold">D'coins</th>
              <th className="text-left px-6 py-3 font-semibold">Tests Completed</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((entry: any, index: number) => (
              <tr key={entry.id} className="border-b border-muted hover:bg-muted/50">
                <td className="px-6 py-4">
                  <span className={`text-lg font-bold ${
                    index === 0 ? "text-yellow-600" : 
                    index === 1 ? "text-gray-500" : 
                    index === 2 ? "text-orange-600" : 
                    "text-foreground"
                  }`}>
                    {index + 1}
                  </span>
                </td>
                <td className="px-6 py-4">{entry.full_name}</td>
                <td className="px-6 py-4 font-semibold">{entry.total_score}</td>
                <td className="px-6 py-4 text-green-600">{entry.dcoin_balance}</td>
                <td className="px-6 py-4">{entry.completed_tests}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
