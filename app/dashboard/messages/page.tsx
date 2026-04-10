"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface Message {
  id: string;
  sender_id: string;
  recipient_id: string;
  subject: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
}

export default function MessagesPage() {
  const supabase = createClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"inbox" | "sent">("inbox");

  const [formData, setFormData] = useState({
    recipientId: "",
    subject: "",
    content: "",
  });

  useEffect(() => {
    loadUsers();
    loadMessages();
  }, [activeTab]);

  const loadUsers = async () => {
    try {
      const { data, error } = await supabase.from("profiles").select("*");
      if (!error && data) {
        setUsers(data);
      }
    } catch (error) {
      console.log("[v0] Error loading users:", error);
    }
  };

  const loadMessages = async () => {
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) return;

      let query = supabase.from("messages").select("*");

      if (activeTab === "inbox") {
        query = query.eq("recipient_id", user.id);
      } else {
        query = query.eq("sender_id", user.id);
      }

      const { data, error } = await query.order("created_at", { ascending: false });

      if (!error && data) {
        setMessages(data);
      }
    } catch (error) {
      console.log("[v0] Error loading messages:", error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) return;

      const { error } = await supabase.from("messages").insert({
        sender_id: user.id,
        recipient_id: formData.recipientId,
        subject: formData.subject,
        content: formData.content,
        is_read: false,
      });

      if (!error) {
        console.log("[v0] Message sent");
        setFormData({ recipientId: "", subject: "", content: "" });
        setShowForm(false);
        loadMessages();
      } else {
        console.log("[v0] Error sending message:", error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (messageId: string) => {
    try {
      const { error } = await supabase
        .from("messages")
        .update({ is_read: true })
        .eq("id", messageId);

      if (!error) {
        loadMessages();
      }
    } catch (error) {
      console.log("[v0] Error marking as read:", error);
    }
  };

  const handleDeleteMessage = async (messageId: string) => {
    if (!confirm("Delete this message?")) return;

    try {
      const { error } = await supabase.from("messages").delete().eq("id", messageId);

      if (!error) {
        loadMessages();
        setShowDetail(false);
      }
    } catch (error) {
      console.log("[v0] Error deleting message:", error);
    }
  };

  const getSenderName = (senderId: string) => {
    const user = users.find((u) => u.id === senderId);
    return user?.full_name || "Unknown";
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-primary">Internal Messages</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
        >
          {showForm ? "Cancel" : "Send Message"}
        </button>
      </div>

      {showForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">Send Message</h2>
          <form onSubmit={handleSendMessage} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Recipient
              </label>
              <select
                value={formData.recipientId}
                onChange={(e) =>
                  setFormData({ ...formData, recipientId: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                required
              >
                <option value="">Select Recipient</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name} ({user.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Subject
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) =>
                  setFormData({ ...formData, subject: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Message subject"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Message
              </label>
              <textarea
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary h-40"
                placeholder="Message content"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send Message"}
            </button>
          </form>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 mb-8 border-b border-muted">
        <button
          onClick={() => setActiveTab("inbox")}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === "inbox"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Inbox ({messages.filter((m) => !m.is_read).length})
        </button>
        <button
          onClick={() => setActiveTab("sent")}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === "sent"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Sent ({messages.length})
        </button>
      </div>

      {/* Message List / Detail */}
      {showDetail && selectedMessage ? (
        <div className="bg-background border border-muted rounded-lg p-6">
          <button
            onClick={() => setShowDetail(false)}
            className="text-primary hover:underline text-sm font-medium mb-4"
          >
            ← Back to Messages
          </button>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">From</p>
              <p className="text-lg font-semibold text-foreground">
                {getSenderName(selectedMessage.sender_id)}
              </p>
            </div>

            <div>
              <p className="text-sm text-muted-foreground">Subject</p>
              <p className="text-lg font-semibold text-foreground">{selectedMessage.subject}</p>
            </div>

            <div>
              <p className="text-sm text-muted-foreground">Date</p>
              <p className="text-foreground">
                {new Date(selectedMessage.created_at).toLocaleString()}
              </p>
            </div>

            <div className="bg-muted rounded-lg p-4">
              <p className="text-foreground whitespace-pre-wrap">{selectedMessage.content}</p>
            </div>

            <div className="flex gap-3">
              {!selectedMessage.is_read && (
                <button
                  onClick={() => {
                    handleMarkAsRead(selectedMessage.id);
                    setShowDetail(false);
                  }}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
                >
                  Mark as Read
                </button>
              )}
              <button
                onClick={() => handleDeleteMessage(selectedMessage.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-2xl font-bold text-foreground mb-6">
            {activeTab === "inbox" ? "Inbox" : "Sent"}
          </h2>

          {messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No messages</p>
            </div>
          ) : (
            <div className="space-y-2">
              {messages.map((message) => (
                <div
                  key={message.id}
                  onClick={() => {
                    setSelectedMessage(message);
                    setShowDetail(true);
                  }}
                  className={`p-4 rounded-lg border cursor-pointer transition ${
                    message.is_read
                      ? "border-muted hover:border-primary"
                      : "border-primary bg-primary/5"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className={`font-semibold ${message.is_read ? "text-muted-foreground" : "text-foreground"}`}>
                        {getSenderName(message.sender_id)}
                      </p>
                      <p className="text-sm text-muted-foreground">{message.subject}</p>
                    </div>
                    <p className="text-xs text-muted-foreground ml-4">
                      {new Date(message.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
