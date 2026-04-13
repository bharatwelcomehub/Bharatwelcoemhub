import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { api, fetchCentersFromDB, isAdminUser } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Loader2, Plus, Save, Trash2, X, RefreshCw, Edit, Search,
  Image, Video, Calendar, BarChart3, Eye,
} from "lucide-react";

const STATUS_COLORS = {
  "Planned": "bg-blue-100 text-blue-800",
  "In Progress": "bg-yellow-100 text-yellow-800",
  "Ready": "bg-purple-100 text-purple-800",
  "Posted": "bg-green-100 text-green-800",
  "Cancelled": "bg-red-100 text-red-800",
};

export default function SocialMediaPlanner() {
  const { session } = useAuth();
  const isAdmin = isAdminUser(session);
  const [loading, setLoading] = useState(false);
  const [centersList, setCentersList] = useState([]);
  const [constants, setConstants] = useState({});
  const [activeTab, setActiveTab] = useState("dashboard");

  // Filters
  const [filterCenter, setFilterCenter] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterMonth, setFilterMonth] = useState("");
  const [search, setSearch] = useState("");

  // Data
  const [posts, setPosts] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [postForm, setPostForm] = useState(null);

  useEffect(() => {
    if (session?.token) {
      fetchCentersFromDB(session.token).then(setCentersList);
      api.post("/social-media/constants", { token: session.token })
        .then(r => setConstants(r.data)).catch(() => {});
    }
  }, [session?.token]);

  const loadPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/social-media/list", {
        token: session.token, center: filterCenter, status: filterStatus,
        platform: filterPlatform, month: filterMonth,
      });
      setPosts(res.data.posts || []);
    } catch { toast.error("Failed to load posts"); }
    finally { setLoading(false); }
  }, [session?.token, filterCenter, filterStatus, filterPlatform, filterMonth]);

  const loadDashboard = useCallback(async () => {
    try {
      const res = await api.post("/social-media/dashboard", {
        token: session.token, center: filterCenter,
      });
      setDashboard(res.data);
    } catch {}
  }, [session?.token, filterCenter]);

  useEffect(() => {
    if (session?.token && activeTab === "posts") loadPosts();
    if (session?.token && activeTab === "dashboard") loadDashboard();
  }, [activeTab, loadPosts, loadDashboard, session?.token]);

  const savePost = async () => {
    if (!postForm) return;
    try {
      await api.post("/social-media/save", { token: session.token, ...postForm });
      toast.success("Post saved");
      setPostForm(null);
      loadPosts();
      loadDashboard();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
  };

  const deletePost = async (post_id) => {
    if (!window.confirm("Delete this post?")) return;
    try {
      await api.post("/social-media/delete", { token: session.token, post_id });
      toast.success("Post deleted");
      loadPosts();
    } catch (e) { toast.error("Delete failed"); }
  };

  const filteredPosts = posts.filter(p => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (p.post_title || "").toLowerCase().includes(q)
      || (p.caption || "").toLowerCase().includes(q)
      || (p.center || "").toLowerCase().includes(q)
      || (p.platform || "").toLowerCase().includes(q);
  });

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: BarChart3 },
    { id: "posts", label: "Content List", icon: Image },
    { id: "calendar", label: "Calendar", icon: Calendar },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="social-media-title">Social Media Planner</h1>
          <p className="text-muted-foreground mt-1">Content planning & tracking for franchise centers</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setPostForm({
            center: filterCenter || centersList[0]?.code || "", content_type: "Static Post",
            platform: "Instagram", post_title: "", caption: "", hashtags: "", status: "Planned",
            campaign_category: "Daily", planned_date: new Date().toISOString().split("T")[0],
            post_date: "", remarks: "",
          })} data-testid="new-post-btn">
            <Plus className="w-4 h-4 mr-2" /> New Post
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`} data-testid={`sm-tab-${tab.id}`}>
            <tab.icon className="w-4 h-4" /> {tab.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-3 pb-3">
          <div className="flex flex-wrap gap-2 items-end">
            {isAdmin && (
              <div className="space-y-1">
                <Label className="text-xs">Center</Label>
                <select value={filterCenter} onChange={e => setFilterCenter(e.target.value)}
                  className="h-9 px-2 rounded-md border border-input bg-background text-xs">
                  <option value="">All Centers</option>
                  {centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
                </select>
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-xs">Status</Label>
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                className="h-9 px-2 rounded-md border border-input bg-background text-xs">
                <option value="">All</option>
                {(constants.statuses || []).map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Platform</Label>
              <select value={filterPlatform} onChange={e => setFilterPlatform(e.target.value)}
                className="h-9 px-2 rounded-md border border-input bg-background text-xs">
                <option value="">All</option>
                {(constants.platforms || []).map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Month</Label>
              <Input type="month" value={filterMonth} onChange={e => setFilterMonth(e.target.value)} className="h-9 text-xs w-[140px]" />
            </div>
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
              <Input placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)} className="h-9 text-xs pl-7 w-[150px]" />
            </div>
            <Button size="sm" variant="outline" onClick={() => { loadPosts(); loadDashboard(); }} disabled={loading}>
              <RefreshCw className={`w-3 h-3 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Post Form (Admin only) */}
      {postForm && isAdmin && (
        <Card className="border-2 border-primary">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center justify-between">
              {postForm.post_id ? "Edit Post" : "New Social Media Post"}
              <Button variant="ghost" size="sm" onClick={() => setPostForm(null)}><X className="w-4 h-4" /></Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Center *</Label>
                <select value={postForm.center} onChange={e => setPostForm(p => ({ ...p, center: e.target.value }))}
                  className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                  {centersList.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Content Type</Label>
                <select value={postForm.content_type} onChange={e => setPostForm(p => ({ ...p, content_type: e.target.value }))}
                  className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                  {(constants.content_types || []).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Platform</Label>
                <select value={postForm.platform} onChange={e => setPostForm(p => ({ ...p, platform: e.target.value }))}
                  className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                  {(constants.platforms || []).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Status</Label>
                <select value={postForm.status} onChange={e => setPostForm(p => ({ ...p, status: e.target.value }))}
                  className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                  {(constants.statuses || []).map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Campaign Category</Label>
                <select value={postForm.campaign_category} onChange={e => setPostForm(p => ({ ...p, campaign_category: e.target.value }))}
                  className="w-full h-9 px-2 rounded-md border border-input bg-background text-xs">
                  {(constants.campaign_categories || []).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Planned Date</Label>
                <Input type="date" value={postForm.planned_date} className="h-9 text-xs"
                  onChange={e => setPostForm(p => ({ ...p, planned_date: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Post Date (if posted)</Label>
                <Input type="date" value={postForm.post_date} className="h-9 text-xs"
                  onChange={e => setPostForm(p => ({ ...p, post_date: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Post Title</Label>
                <Input value={postForm.post_title} className="h-9 text-xs" placeholder="Title"
                  onChange={e => setPostForm(p => ({ ...p, post_title: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Caption</Label>
                <Textarea value={postForm.caption} rows={2} className="text-xs"
                  onChange={e => setPostForm(p => ({ ...p, caption: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Hashtags</Label>
                <Textarea value={postForm.hashtags} rows={2} className="text-xs" placeholder="#purnabramha #food"
                  onChange={e => setPostForm(p => ({ ...p, hashtags: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Remarks / Notes</Label>
              <Input value={postForm.remarks} className="h-9 text-xs"
                onChange={e => setPostForm(p => ({ ...p, remarks: e.target.value }))} />
            </div>
            <Button onClick={savePost} size="sm" data-testid="save-post-btn">
              <Save className="w-4 h-4 mr-1" /> Save Post
            </Button>
          </CardContent>
        </Card>
      )}

      {/* DASHBOARD TAB */}
      {activeTab === "dashboard" && dashboard && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card><CardContent className="pt-4 text-center">
              <p className="text-xs text-muted-foreground">Total Posts</p>
              <p className="text-2xl font-bold">{dashboard.total_posts}</p>
            </CardContent></Card>
            <Card><CardContent className="pt-4 text-center">
              <p className="text-xs text-muted-foreground">Posted</p>
              <p className="text-2xl font-bold text-green-600">{dashboard.posted_count}</p>
            </CardContent></Card>
            <Card><CardContent className="pt-4 text-center">
              <p className="text-xs text-muted-foreground">Planned / In Progress</p>
              <p className="text-2xl font-bold text-blue-600">{dashboard.planned_count}</p>
            </CardContent></Card>
            <Card><CardContent className="pt-4 text-center">
              <p className="text-xs text-muted-foreground">Posted vs Planned</p>
              <p className="text-2xl font-bold">
                {dashboard.total_posts > 0 ? `${Math.round((dashboard.posted_count / dashboard.total_posts) * 100)}%` : "0%"}
              </p>
            </CardContent></Card>
          </div>

          {/* Status + Platform breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">By Status</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(dashboard.status_counts || {}).map(([st, ct]) => (
                    <div key={st} className="flex items-center justify-between">
                      <Badge className={STATUS_COLORS[st] || "bg-gray-100"}>{st}</Badge>
                      <span className="font-bold">{ct}</span>
                    </div>
                  ))}
                  {Object.keys(dashboard.status_counts || {}).length === 0 && (
                    <p className="text-sm text-muted-foreground">No data</p>
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">By Platform</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(dashboard.platform_counts || {}).map(([pl, ct]) => (
                    <div key={pl} className="flex items-center justify-between">
                      <span className="text-sm">{pl}</span>
                      <Badge variant="outline">{ct}</Badge>
                    </div>
                  ))}
                  {Object.keys(dashboard.platform_counts || {}).length === 0 && (
                    <p className="text-sm text-muted-foreground">No data</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Upcoming */}
          {dashboard.upcoming?.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Upcoming Scheduled</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {dashboard.upcoming.map((p, i) => (
                    <div key={i} className="flex items-center justify-between p-2 border rounded hover:bg-muted/30">
                      <div className="flex items-center gap-2">
                        <Badge className={STATUS_COLORS[p.status] || ""}>{p.status}</Badge>
                        <span className="text-sm font-medium">{p.post_title || p.content_type}</span>
                        <span className="text-xs text-muted-foreground">{p.platform}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{p.planned_date} | {p.center}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* POSTS TAB */}
      {activeTab === "posts" && (
        <div className="border rounded-lg overflow-hidden">
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-sm">
              <thead className="bg-muted sticky top-0 z-10">
                <tr>
                  <th className="p-3 text-left font-bold">Center</th>
                  <th className="p-3 text-left font-bold">Title</th>
                  <th className="p-3 text-left font-bold">Type</th>
                  <th className="p-3 text-left font-bold">Platform</th>
                  <th className="p-3 text-left font-bold">Status</th>
                  <th className="p-3 text-left font-bold">Category</th>
                  <th className="p-3 text-left font-bold">Planned</th>
                  <th className="p-3 text-left font-bold">Posted</th>
                  {isAdmin && <th className="p-3 text-center font-bold">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filteredPosts.map((p, idx) => (
                  <tr key={p.post_id || idx} className="border-t hover:bg-muted/30" data-testid={`sm-post-${idx}`}>
                    <td className="p-3"><Badge variant="outline">{p.center}</Badge></td>
                    <td className="p-3 font-medium max-w-[200px] truncate">{p.post_title || "-"}</td>
                    <td className="p-3 text-xs">{p.content_type}</td>
                    <td className="p-3 text-xs">{p.platform}</td>
                    <td className="p-3"><Badge className={STATUS_COLORS[p.status] || ""}>{p.status}</Badge></td>
                    <td className="p-3 text-xs">{p.campaign_category}</td>
                    <td className="p-3 text-xs">{p.planned_date || "-"}</td>
                    <td className="p-3 text-xs">{p.post_date || "-"}</td>
                    {isAdmin && (
                      <td className="p-3 text-center">
                        <div className="flex gap-1 justify-center">
                          <Button size="sm" variant="ghost" onClick={() => setPostForm({ ...p })}>
                            <Edit className="w-3 h-3" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => deletePost(p.post_id)}>
                            <Trash2 className="w-3 h-3 text-red-500" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
                {filteredPosts.length === 0 && (
                  <tr><td colSpan={9} className="p-8 text-center text-muted-foreground">
                    No posts found. {isAdmin ? "Click 'New Post' to create one." : "Content will appear here once the admin team uploads it."}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CALENDAR TAB */}
      {activeTab === "calendar" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Content Calendar</CardTitle>
            <CardDescription>Planned and posted content timeline</CardDescription>
          </CardHeader>
          <CardContent>
            {posts.length > 0 ? (
              <div className="space-y-2">
                {posts.filter(p => p.planned_date || p.post_date).slice(0, 30).map((p, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 border rounded hover:bg-muted/30">
                    <div className="w-20 text-xs text-muted-foreground font-mono">{p.planned_date || p.post_date}</div>
                    <Badge className={STATUS_COLORS[p.status] || ""} >{p.status}</Badge>
                    <Badge variant="outline">{p.center}</Badge>
                    <span className="text-sm font-medium">{p.post_title || p.content_type}</span>
                    <span className="text-xs text-muted-foreground ml-auto">{p.platform}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center py-8 text-muted-foreground">No content scheduled yet</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
