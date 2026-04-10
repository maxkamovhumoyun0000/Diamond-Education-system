"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface Article {
  id: string;
  title: string;
  content: string;
  subject_id: string;
  level_id: string;
  author_id: string;
  is_published: boolean;
  visible_to_teachers: boolean;
  visible_to_support_teachers: boolean;
  visible_to_students: boolean;
  created_at: string;
}

interface Subject {
  id: string;
  name: string;
}

interface Level {
  id: string;
  name: string;
}

export default function ArticlesPage() {
  const supabase = createClient();
  const [articles, setArticles] = useState<Article[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    subjectId: "",
    levelId: "",
    forTeachers: true,
    forSupportTeachers: false,
    forStudents: false,
    isPublished: false,
  });

  useEffect(() => {
    loadSubjects();
    loadArticles();
  }, []);

  useEffect(() => {
    loadLevels();
  }, [formData.subjectId]);

  const loadSubjects = async () => {
    try {
      const { data, error } = await supabase.from("subjects").select("*");
      if (!error && data) {
        setSubjects(data);
      }
    } catch (error) {
      console.log("[v0] Error loading subjects:", error);
    }
  };

  const loadLevels = async () => {
    if (!formData.subjectId) {
      setLevels([]);
      return;
    }

    try {
      const { data, error } = await supabase
        .from("levels")
        .select("*")
        .eq("subject_id", formData.subjectId)
        .order("order_index");

      if (!error && data) {
        setLevels(data);
      }
    } catch (error) {
      console.log("[v0] Error loading levels:", error);
    }
  };

  const loadArticles = async () => {
    try {
      const { data, error } = await supabase
        .from("articles")
        .select("*")
        .order("created_at", { ascending: false });

      if (!error && data) {
        setArticles(data);
      }
    } catch (error) {
      console.log("[v0] Error loading articles:", error);
    }
  };

  const handleAddArticle = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) return;

      const { error } = await supabase.from("articles").insert({
        title: formData.title,
        content: formData.content,
        subject_id: formData.subjectId,
        level_id: formData.levelId,
        author_id: user.id,
        is_published: formData.isPublished,
        visible_to_teachers: formData.forTeachers,
        visible_to_support_teachers: formData.forSupportTeachers,
        visible_to_students: formData.forStudents,
      });

      if (!error) {
        console.log("[v0] Article created");
        setFormData({
          title: "",
          content: "",
          subjectId: "",
          levelId: "",
          forTeachers: true,
          forSupportTeachers: false,
          forStudents: false,
          isPublished: false,
        });
        setShowForm(false);
        loadArticles();
      } else {
        console.log("[v0] Error creating article:", error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteArticle = async (articleId: string) => {
    if (!confirm("Delete this article?")) return;

    try {
      const { error } = await supabase.from("articles").delete().eq("id", articleId);

      if (!error) {
        loadArticles();
        setSelectedArticle(null);
        console.log("[v0] Article deleted");
      }
    } catch (error) {
      console.log("[v0] Error deleting article:", error);
    }
  };

  const handlePublishToggle = async (article: Article) => {
    try {
      const { error } = await supabase
        .from("articles")
        .update({ is_published: !article.is_published })
        .eq("id", article.id);

      if (!error) {
        loadArticles();
        console.log("[v0] Article status updated");
      }
    } catch (error) {
      console.log("[v0] Error updating article:", error);
    }
  };

  const getSubjectName = (subjectId: string) => {
    return subjects.find((s) => s.id === subjectId)?.name || "-";
  };

  const getLevelName = (levelId: string) => {
    return levels.find((l) => l.id === levelId)?.name || "-";
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-primary">Articles Management</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition"
        >
          {showForm ? "Cancel" : "Create Article"}
        </button>
      </div>

      {showForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">Create New Article</h2>
          <form onSubmit={handleAddArticle} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Title
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Subject
                </label>
                <select
                  value={formData.subjectId}
                  onChange={(e) =>
                    setFormData({ ...formData, subjectId: e.target.value, levelId: "" })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  required
                >
                  <option value="">Select Subject</option>
                  {subjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Level
                </label>
                <select
                  value={formData.levelId}
                  onChange={(e) =>
                    setFormData({ ...formData, levelId: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  required
                >
                  <option value="">Select Level</option>
                  {levels.map((level) => (
                    <option key={level.id} value={level.id}>
                      {level.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Content
              </label>
              <textarea
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary h-40"
                required
              />
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-foreground mb-3">
                Visible To
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="forTeachers"
                  checked={formData.forTeachers}
                  onChange={(e) =>
                    setFormData({ ...formData, forTeachers: e.target.checked })
                  }
                  className="w-4 h-4"
                />
                <label htmlFor="forTeachers" className="text-foreground cursor-pointer">
                  Teachers
                </label>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="forSupportTeachers"
                  checked={formData.forSupportTeachers}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      forSupportTeachers: e.target.checked,
                    })
                  }
                  className="w-4 h-4"
                />
                <label
                  htmlFor="forSupportTeachers"
                  className="text-foreground cursor-pointer"
                >
                  Support Teachers
                </label>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="forStudents"
                  checked={formData.forStudents}
                  onChange={(e) =>
                    setFormData({ ...formData, forStudents: e.target.checked })
                  }
                  className="w-4 h-4"
                />
                <label htmlFor="forStudents" className="text-foreground cursor-pointer">
                  Students
                </label>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="isPublished"
                checked={formData.isPublished}
                onChange={(e) =>
                  setFormData({ ...formData, isPublished: e.target.checked })
                }
                className="w-4 h-4"
              />
              <label htmlFor="isPublished" className="text-foreground cursor-pointer font-medium">
                Publish Immediately
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Article"}
            </button>
          </form>
        </div>
      )}

      {/* Articles List */}
      <div className="bg-background border border-muted rounded-lg p-6">
        <h2 className="text-2xl font-bold text-foreground mb-6">Articles List</h2>

        {articles.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No articles created yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {articles.map((article) => (
              <div
                key={article.id}
                className="border border-muted rounded-lg p-4 bg-background hover:border-primary transition"
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-bold text-foreground flex-1 pr-3">{article.title}</h3>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                      article.is_published
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {article.is_published ? "Published" : "Draft"}
                  </span>
                </div>

                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                  {article.content}
                </p>

                <div className="mb-3 space-y-1 text-xs text-muted-foreground">
                  <p>Subject: {getSubjectName(article.subject_id)}</p>
                  <p>Level: {getLevelName(article.level_id)}</p>
                  <p>Created: {new Date(article.created_at).toLocaleDateString()}</p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handlePublishToggle(article)}
                    className="flex-1 text-xs px-2 py-2 bg-primary text-primary-foreground rounded hover:opacity-90 transition"
                  >
                    {article.is_published ? "Unpublish" : "Publish"}
                  </button>
                  <button
                    onClick={() => handleDeleteArticle(article.id)}
                    className="text-xs px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
