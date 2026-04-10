"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface Transaction {
  id: string;
  student_id: string;
  amount: number;
  transaction_type: string;
  reason: string;
  created_at: string;
}

interface Student {
  id: string;
  full_name: string;
}

interface Balance {
  id: string;
  student_id: string;
  balance: number;
}

export default function DCoinPage() {
  const supabase = createClient();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [balances, setBalances] = useState<Map<string, number>>(new Map());
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [totals, setTotals] = useState({
    totalCoins: 0,
    rewards: 0,
    deductions: 0,
  });

  const [formData, setFormData] = useState({
    studentId: "",
    amount: "",
    type: "reward",
    reason: "",
  });

  useEffect(() => {
    loadStudents();
    loadTransactions();
  }, []);

  const loadStudents = async () => {
    if (!supabase) return;
    
    try {
      const { data, error } = await supabase
        .from("profiles")
        .select("id, full_name")
        .eq("role", "student");
      if (!error && data) {
        setStudents(data);
      }
    } catch (error) {
      console.log("[v0] Error loading students:", error);
    }
  };

  const loadTransactions = async () => {
    if (!supabase) return;
    
    try {
      const { data, error } = await supabase
        .from("dcoin_transactions")
        .select("*")
        .order("created_at", { ascending: false });

      if (!error && data) {
        setTransactions(data);
        calculateTotals(data);
      }
    } catch (error) {
      console.log("[v0] Error loading transactions:", error);
    }
  };

  const calculateTotals = (txns: Transaction[]) => {
    let total = 0;
    let rewards = 0;
    let deductions = 0;

    txns.forEach((txn) => {
      if (txn.transaction_type === "reward" || txn.transaction_type === "bonus") {
        total += txn.amount;
        rewards += txn.amount;
      } else if (txn.transaction_type === "deduction") {
        total -= txn.amount;
        deductions += txn.amount;
      }
    });

    setTotals({ totalCoins: total, rewards, deductions });
  };

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supabase) return;
    
    setLoading(true);

    try {
      const { data } = await supabase.auth.getUser();
      const user = data?.user;

      if (!user) return;

      const amount = parseInt(formData.amount);
      const { error } = await supabase.from("dcoin_transactions").insert({
        student_id: formData.studentId,
        amount: formData.type === "deduction" ? -amount : amount,
        transaction_type: formData.type,
        reason: formData.reason,
        created_by: user.id,
      });

      if (!error) {
        console.log("[v0] Transaction added");
        setFormData({
          studentId: "",
          amount: "",
          type: "reward",
          reason: "",
        });
        setShowForm(false);
        loadTransactions();
      } else {
        console.log("[v0] Error adding transaction:", error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStudentName = (studentId: string) => {
    return students.find((s) => s.id === studentId)?.full_name || "Unknown";
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "reward":
      case "bonus":
        return "bg-green-100 text-green-800";
      case "deduction":
        return "bg-red-100 text-red-800";
      case "transfer":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-primary">D&apos;coin System</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition"
        >
          {showForm ? "Cancel" : "Add Transaction"}
        </button>
      </div>

      {showForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">
            Add D&apos;coin Transaction
          </h2>
          <form onSubmit={handleAddTransaction} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Student
                </label>
                <select
                  value={formData.studentId}
                  onChange={(e) =>
                    setFormData({ ...formData, studentId: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  required
                >
                  <option value="">Select Student</option>
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.full_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Amount
                </label>
                <input
                  type="number"
                  value={formData.amount}
                  onChange={(e) =>
                    setFormData({ ...formData, amount: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  placeholder="Enter amount"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Transaction Type
                </label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                >
                  <option value="reward">Reward</option>
                  <option value="deduction">Deduction</option>
                  <option value="transfer">Transfer</option>
                  <option value="bonus">Bonus</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Reason
                </label>
                <input
                  type="text"
                  value={formData.reason}
                  onChange={(e) =>
                    setFormData({ ...formData, reason: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  placeholder="e.g., Class participation"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Adding..." : "Add Transaction"}
            </button>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Total D&apos;coins (Net)</h3>
          <p className="text-3xl font-bold text-secondary mt-2">{totals.totalCoins}</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Rewards Given</h3>
          <p className="text-3xl font-bold text-green-600 mt-2">+{totals.rewards}</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Deductions Made</h3>
          <p className="text-3xl font-bold text-red-600 mt-2">-{totals.deductions}</p>
        </div>
      </div>

      {/* Transactions List */}
      <div className="bg-background border border-muted rounded-lg p-6">
        <h2 className="text-2xl font-bold text-foreground mb-6">Recent Transactions</h2>

        {transactions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No transactions yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-muted">
                  <th className="text-left py-3 px-4 font-semibold text-foreground">
                    Student
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground">
                    Amount
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground">
                    Reason
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-foreground">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-muted hover:bg-muted/50">
                    <td className="py-3 px-4 text-foreground">{getStudentName(txn.student_id)}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(txn.transaction_type)}`}>
                        {txn.transaction_type}
                      </span>
                    </td>
                    <td className={`py-3 px-4 font-semibold ${txn.amount > 0 ? "text-green-600" : "text-red-600"}`}>
                      {txn.amount > 0 ? "+" : ""}{txn.amount}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">{txn.reason}</td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {new Date(txn.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
