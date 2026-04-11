"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface Article {
  id: string;
  title: string;
  content: string;
  subject_id: string;
  level_id: string;
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

export default function StudentArticlesPage() {
  const supabase = createClient();
  const [articles, setArticles] = useState<Article[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [filterSubject, setFilterSubject] = useState<string>("");
  const [filterLevel, setFilterLevel] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSubjects();
    loadArticles();
  }, [filterSubject, filterLevel]);

  const loadSubjects = async () => {
    if (!supabase) return;
    
    try {
      const { data, error } = await supabase.from("subjects").select("*").eq("is_active", true);
      if (!error && data) {
        setSubjects(data);
      }
    } catch (error) {
      console.log("[v0] Error loading subjects:", error);
    }
  };

  const loadArticles = async () => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      const { data: userData } = await supabase.auth.getUser();
      const user = userData?.user;

      if (!user) return;

      // Get user profile to check role
      const { data: profile } = await supabase.from("profiles").select("role").eq("id", user.id).single();

      let query = supabase
        .from("articles")
        .select("*")
        .eq("is_published", true);

      // Apply role-based visibility
      if (profile?.role === "student") {
        query = query.eq("visible_to_students", true);
      } else if (profile?.role === "support_teacher") {
        query = query.eq("visible_to_support_teachers", true);
      } else if (profile?.role === "teacher") {
        query = query.eq("visible_to_teachers", true);
      }

      // Apply filters
      if (filterSubject) {
        query = query.eq("subject_id", filterSubject);
      }
      if (filterLevel) {
        query = query.eq("level_id", filterLevel);
      }

      const { data: articlesData, error } = await query.order("created_at", { ascending: false });

      if (!error && articlesData) {
        setArticles(articlesData);
        // Load levels for selected subject
        if (filterSubject) {
          const { data: levelData } = await supabase
            .from("levels")
            .select("*")
            .eq("subject_id", filterSubject)
            .order("order_index");
          if (levelData) {
            setLevels(levelData);
          }
        }
      }
    } catch (error) {
      console.log("[v0] Error loading articles:", error);
    } finally {
      setLoading(false);
    }
  };

  const getSubjectName = (subjectId: string) => {
    return subjects.find((s) => s.id === subjectId)?.name || "-";
  };

  const getLevelName = (levelId: string) => {
    return levels.find((l) => l.id === levelId)?.name || "-";
  };

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-4xl font-bold text-primary mb-8">Learning Articles</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar with Filters */}
        <div className="lg:col-span-1">
          <div className="bg-background border border-muted rounded-lg p-6 sticky top-6">
            <h2 className="text-xl font-bold text-foreground mb-6">Filters</h2>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Subject
                </label>
                <select
                  value={filterSubject}
                  onChange={(e) => {
                    setFilterSubject(e.target.value);
                    setFilterLevel("");
                  }}
                  className="w-full px-3 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                >
                  <option value="">All Subjects</option>
                  {subjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.name}
                    </option>
                  ))}
                </select>
              </div>

              {filterSubject && (
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Level
                  </label>
                  <select
                    value={filterLevel}
                    onChange={(e) => setFilterLevel(e.target.value)}
                    className="w-full px-3 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                  >
                    <option value="">All Levels</option>
                    {levels.map((level) => (
                      <option key={level.id} value={level.id}>
                        {level.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-3">
          {selectedArticle ? (
            // Article Detail View
            <div className="bg-background border border-muted rounded-lg p-8">
              <button
                onClick={() => setSelectedArticle(null)}
                className="text-primary hover:underline text-sm font-medium mb-6"
              >
                ← Back to Articles
              </button>

              <h2 className="text-3xl font-bold text-foreground mb-4">{selectedArticle.title}</h2>

              <div className="flex gap-4 mb-6 text-sm text-muted-foreground">
                <span>{getSubjectName(selectedArticle.subject_id)}</span>
                <span>•</span>
                <span>{getLevelName(selectedArticle.level_id)}</span>
                <span>•</span>
                <span>{new Date(selectedArticle.created_at).toLocaleDateString()}</span>
              </div>

              <div className="bg-muted rounded-lg p-6 text-foreground whitespace-pre-wrap leading-relaxed">
                {selectedArticle.content}
              </div>
            </div>
          ) : (
            // Articles List View
            <>
              {loading ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">Loading articles...</p>
                </div>
              ) : articles.length === 0 ? (
                <div className="bg-background border border-muted rounded-lg p-12 text-center">
                  <p className="text-muted-foreground mb-4">No articles available</p>
                  <p className="text-sm text-muted-foreground">
                    Try adjusting your filters or come back later
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {articles.map((article) => (
                    <button
                      key={article.id}
                      onClick={() => setSelectedArticle(article)}
                      className="w-full bg-background border border-muted rounded-lg p-6 hover:border-primary transition text-left"
                    >
                      <h3 className="text-xl font-bold text-foreground mb-2">
                        {article.title}
                      </h3>

                      <p className="text-muted-foreground mb-4 line-clamp-2">
                        {article.content}
                      </p>

                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <span className="px-2 py-1 bg-muted rounded">
                          {getSubjectName(article.subject_id)}
                        </span>
                        <span className="px-2 py-1 bg-muted rounded font-medium">
                          {getLevelName(article.level_id)}
                        </span>
                        <span className="px-2 py-1 bg-muted rounded">
                          {new Date(article.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
