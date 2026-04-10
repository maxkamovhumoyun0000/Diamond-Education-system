"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ArenaPage() {
  const [battles, setBattles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBattles();
  }, []);

  const loadBattles = async () => {
    try {
      const result = await api.arena.getAvailableBattles();
      setBattles(result);
    } catch (error) {
      console.log("[v0] Error loading battles:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">Arena Battles</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {battles.length === 0 ? (
          <div className="col-span-2 text-center py-12">
            <p className="text-muted-foreground">No battles available</p>
          </div>
        ) : (
          battles.map((battle: any) => (
            <div key={battle.id} className="border border-muted rounded-lg p-6">
              <h3 className="text-xl font-bold text-foreground mb-2">{battle.title}</h3>
              <p className="text-muted-foreground mb-4">{battle.description}</p>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">
                  Prize: {battle.reward} D'coins
                </span>
                <button className="px-4 py-2 bg-primary text-primary-foreground rounded hover:opacity-90">
                  Join Battle
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
