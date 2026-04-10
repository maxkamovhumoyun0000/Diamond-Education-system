"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function TestsPage() {
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTests();
  }, []);

  const loadTests = async () => {
    try {
      const result = await api.tests.getAvailable();
      setTests(result);
    } catch (error) {
      console.log("[v0] Error loading tests:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">Available Tests</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tests.length === 0 ? (
          <div className="col-span-3 text-center py-12">
            <p className="text-muted-foreground">No tests available</p>
          </div>
        ) : (
          tests.map((test: any) => (
            <div key={test.id} className="border border-muted rounded-lg p-6">
              <h3 className="text-lg font-bold text-foreground mb-2">{test.title}</h3>
              <p className="text-sm text-muted-foreground mb-3">{test.subject}</p>
              <div className="text-sm space-y-1 mb-4">
                <p>Duration: {test.duration} min</p>
                <p>Questions: {test.question_count}</p>
                <p>Level: {test.level}</p>
              </div>
              <button className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded hover:opacity-90">
                Start Test
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
