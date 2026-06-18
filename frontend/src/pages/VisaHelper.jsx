import { useState, useEffect, useMemo, useCallback } from "react";
import { api, isAdminUser, API_URL } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Globe, FileText, Loader2, Sparkles, Download, Plus, Trash2,
  ChevronLeft, ChevronRight, RefreshCw, FilePlus2, Users,
  Flag, BookOpen, Building2, PenSquare, ListChecks, Award,
  Ban, CheckCircle2, ArrowLeft, FileArchive, Send, Briefcase, AlertTriangle,
} from "lucide-react";

const STEPS = [
  { id: 1, label: "Country", icon: Flag },
  { id: 2, label: "Applicant", icon: Users },
  { id: 3, label: "Education & Skills", icon: Award },
  { id: 4, label: "Experience", icon: BookOpen },
  { id: 5, label: "Family", icon: Users },
  { id: 6, label: "Business / Role", icon: Building2 },
  { id: 7, label: "Signatory & Entity", icon: PenSquare },
  { id: 8, label: "Documents Ready", icon: ListChecks },
  { id: 9, label: "Goals & Notes", icon: FileText },
  { id: 10, label: "Review & Save", icon: CheckCircle2 },
];

function getToken() {
  try {
    const s = JSON.parse(localStorage.getItem("pb_session_v2") || "{}");
    return s?.token || "";
  } catch {
    return "";
  }
}

function downloadBlob(url, filename) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function downloadAuthed(path, filename) {
  const token = getToken();
  const url = `${API_URL}${path}${path.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Download failed (${res.status}): ${txt.slice(0, 120)}`);
  }
  const blob = await res.blob();
  const objUrl = URL.createObjectURL(blob);
  downloadBlob(objUrl, filename);
  setTimeout(() => URL.revokeObjectURL(objUrl), 5000);
}

async function downloadAuthedPost(path, body, filename) {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, ...body }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Download failed (${res.status}): ${txt.slice(0, 160)}`);
  }
  const blob = await res.blob();
  const objUrl = URL.createObjectURL(blob);
  downloadBlob(objUrl, filename);
  setTimeout(() => URL.revokeObjectURL(objUrl), 5000);
}

export default function VisaHelper() {
  const session = useMemo(() => {
    try { return JSON.parse(localStorage.getItem("pb_session_v2") || "{}"); }
    catch { return {}; }
  }, []);
  const isAdmin = isAdminUser(session);

  const [tab, setTab] = useState("recommender");
  const [countries, setCountries] = useState([]);
  const [pathways, setPathways] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [entities, setEntities] = useState([]);
  const [signatories, setSignatories] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(false);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      const [c, t, e, s, apps] = await Promise.all([
        api.get("/visa/countries"),
        api.get("/visa/letter-templates"),
        api.get("/visa/entities"),
        api.get("/visa/signatories"),
        api.get("/visa/applications"),
      ]);
      setCountries(c.data?.countries || []);
      setTemplates(t.data?.templates || []);
      setEntities(e.data?.entities || []);
      setSignatories(s.data?.signatories || []);
      setApplications(apps.data?.applications || []);
    } catch (err) {
      toast.error("Failed to load Visa Helper data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshPathways = useCallback(async (countryCode) => {
    try {
      const q = countryCode ? `?country_code=${encodeURIComponent(countryCode)}` : "";
      const r = await api.get(`/visa/pathways${q}`);
      setPathways(r.data?.pathways || []);
    } catch {
      setPathways([]);
    }
  }, []);

  useEffect(() => { refreshAll(); }, [refreshAll]);
  useEffect(() => { refreshPathways(); }, [refreshPathways]);

  return (
    <div className="space-y-6" data-testid="visa-helper-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary flex items-center gap-2" data-testid="visa-helper-title">
            <Globe className="h-8 w-8" /> Visa Helper / Global Mobility
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generate visa-readiness reports, document checklists and AI-drafted immigration letters.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refreshAll} disabled={loading} data-testid="visa-refresh-btn">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList data-testid="visa-tabs">
          <TabsTrigger value="recommender" data-testid="visa-tab-recommender">
            <Sparkles className="h-4 w-4 mr-1" /> AI Recommender
          </TabsTrigger>
          <TabsTrigger value="applications" data-testid="visa-tab-applications">Applications</TabsTrigger>
          <TabsTrigger value="new" data-testid="visa-tab-new">Manual Wizard</TabsTrigger>
          {isAdmin && <TabsTrigger value="admin" data-testid="visa-tab-admin">Admin Panel</TabsTrigger>}
        </TabsList>

        <TabsContent value="recommender" className="mt-4">
          <RecommenderSection
            countries={countries}
            entities={entities}
            signatories={signatories}
            onProceedToWizard={(seed) => {
              window.__visa_recommender_seed = seed;
              setTab("new");
            }}
          />
        </TabsContent>

        <TabsContent value="applications" className="mt-4">
          <ApplicationsList
            applications={applications}
            countries={countries}
            loading={loading}
            onRefresh={refreshAll}
            onOpen={(app) => { setTab("new"); window.__visa_open_app = app; }}
          />
        </TabsContent>

        <TabsContent value="new" className="mt-4">
          <WizardSection
            countries={countries}
            pathways={pathways}
            templates={templates}
            entities={entities}
            signatories={signatories}
            refreshPathways={refreshPathways}
            onSaved={() => refreshAll()}
            prefill={typeof window !== "undefined" ? window.__visa_open_app : null}
          />
        </TabsContent>

        {isAdmin && (
          <TabsContent value="admin" className="mt-4">
            <AdminPanel
              countries={countries}
              templates={templates}
              entities={entities}
              signatories={signatories}
              pathways={pathways}
              refreshPathways={refreshPathways}
              onRefresh={refreshAll}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Applications List                                          */
/* ────────────────────────────────────────────────────────── */
function ApplicationsList({ applications, countries, loading, onRefresh, onOpen }) {
  const countryName = (code) => countries.find((c) => c.code === code)?.name || code;

  const del = async (aid) => {
    if (!window.confirm(`Delete application ${aid}? This cannot be undone.`)) return;
    try {
      await api.delete(`/visa/application/${aid}`);
      toast.success("Application deleted");
      onRefresh();
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <Card data-testid="visa-applications-card">
      <CardHeader>
        <CardTitle>Saved Applications</CardTitle>
        <CardDescription>
          Resume an in-progress visa workup or regenerate a readiness report.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center text-sm text-muted-foreground"><Loader2 className="h-4 w-4 mr-2 animate-spin" />Loading…</div>
        ) : applications.length === 0 ? (
          <div className="text-sm text-muted-foreground py-8 text-center" data-testid="visa-applications-empty">
            No applications yet. Click <b>+ New Wizard</b> to start.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border" data-testid="visa-applications-table">
              <thead className="bg-slate-100">
                <tr>
                  <th className="p-2 text-left">App ID</th>
                  <th className="p-2 text-left">Applicant</th>
                  <th className="p-2 text-left">Country</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="p-2 text-left">Updated</th>
                  <th className="p-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((a) => (
                  <tr key={a.application_id} className="border-t" data-testid={`visa-app-row-${a.application_id}`}>
                    <td className="p-2 font-mono text-xs">{a.application_id}</td>
                    <td className="p-2">{a.applicant?.name || "—"}</td>
                    <td className="p-2">{countryName(a.country_code)}</td>
                    <td className="p-2"><Badge variant="outline">{a.status}</Badge></td>
                    <td className="p-2 text-xs text-muted-foreground">{(a.updated_at || "").slice(0, 16).replace("T", " ")}</td>
                    <td className="p-2 text-right space-x-1">
                      <Button size="sm" variant="outline" onClick={() => onOpen(a)} data-testid={`visa-app-open-${a.application_id}`}>Open</Button>
                      <Button size="sm" variant="ghost" onClick={() => del(a.application_id)} data-testid={`visa-app-delete-${a.application_id}`}>
                        <Trash2 className="h-3.5 w-3.5 text-red-600" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Wizard                                                     */
/* ────────────────────────────────────────────────────────── */
const EMPTY_APPLICANT = {
  name: "", date_of_birth: "", age: "", nationality: "Indian",
  marital_status: "Married", english_test_status: "Not Started",
  english_test_score: "", current_role: "", current_location: "Pune, India",
  passport_number: "", passport_expiry: "", education_highest: "",
  education_institution: "", years_of_experience: "", skills: "",
  family_included: false, spouse_name: "", spouse_dob: "",
  children: "",   // free text "1 (age 8), 1 (age 5)"
};

const EMPTY_BUSINESS = {
  role_offered: "", proposed_salary: "", proposed_start_date: "",
  proposed_centre: "", proposed_centre_address: "",
  role_responsibilities: "", reporting_to: "",
  signatory_id: "", entity_id: "",
  franchise_letter_available: false, business_plan_available: false,
  financial_proof_available: false,
  goal_summary: "", consultant_notes: "",
};

function WizardSection({ countries, pathways, templates, entities, signatories, refreshPathways, onSaved, prefill }) {
  const [step, setStep] = useState(1);
  const [countryCode, setCountryCode] = useState("");
  const [applicant, setApplicant] = useState({ ...EMPTY_APPLICANT });
  const [business, setBusiness] = useState({ ...EMPTY_BUSINESS });
  const [applicationId, setApplicationId] = useState("");
  const [report, setReport] = useState(null);
  const [letters, setLetters] = useState([]);
  const [saving, setSaving] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [generatingLetters, setGeneratingLetters] = useState(false);
  const [letterScope, setLetterScope] = useState("all");

  // Lawyer-bundle dialog state
  const [lawyerOpen, setLawyerOpen] = useState(false);
  const [lawyerPreview, setLawyerPreview] = useState(null);
  const [lawyerForm, setLawyerForm] = useState({ lawyer_name: "", lawyer_firm: "", notes: "" });
  const [lawyerLoading, setLawyerLoading] = useState(false);
  const [lawyerDownloading, setLawyerDownloading] = useState(false);

  // Hydrate from prefill (if user opened a saved app)
  useEffect(() => {
    if (prefill && prefill.application_id) {
      setApplicationId(prefill.application_id);
      setCountryCode(prefill.country_code || "");
      setApplicant({ ...EMPTY_APPLICANT, ...(prefill.applicant || {}) });
      setBusiness({ ...EMPTY_BUSINESS, ...(prefill.business || {}) });
      setReport(prefill.report || null);
      setLetters(prefill.letters || []);
      setStep(10);
      try { window.__visa_open_app = null; } catch { /* noop */ }
    }
  }, [prefill]);

  // Hydrate from AI Recommender (country + applicant snapshot + selected pathway)
  useEffect(() => {
    const seed = typeof window !== "undefined" ? window.__visa_recommender_seed : null;
    if (seed) {
      setCountryCode(seed.country_code || "");
      setApplicant((prev) => ({ ...prev, ...(seed.applicant || {}) }));
      setBusiness((prev) => ({
        ...prev,
        ...(seed.business || {}),
        selected_pathway_id: seed.pathway_id || prev.selected_pathway_id,
      }));
      setStep(2);
      try { window.__visa_recommender_seed = null; } catch { /* noop */ }
    }
  }, []);

  // Auto-bundle (complete-bundle build + download) state
  const [building, setBuilding] = useState(false);
  const buildCompleteBundle = async () => {
    let aid = applicationId;
    if (!aid) aid = await saveApplication(true);
    if (!aid) return;
    if (!business.signatory_id || !business.entity_id) {
      toast.error("Pick a Signatory and Entity (step 7) before building the complete bundle.");
      return;
    }
    setBuilding(true);
    try {
      const applicantSafe = (applicant.name || "Applicant").replace(/\s+/g, "_");
      await downloadAuthedPost(
        `/visa/application/${aid}/build-complete-bundle`,
        {
          signatory_id: business.signatory_id,
          entity_id: business.entity_id,
          pathway_id: business.selected_pathway_id,
        },
        `PB_CompleteBundle_${applicantSafe}_${countryCode}_${aid}.zip`,
      );
      toast.success("Complete bundle generated & downloaded · 30 most recent kept in Admin → Bundle History");
      onSaved?.();
    } catch (e) {
      toast.error(e.message || "Bundle build failed");
    } finally {
      setBuilding(false);
    }
  };

  useEffect(() => {
    if (countryCode) refreshPathways(countryCode);
  }, [countryCode, refreshPathways]);

  const update = (obj) => setApplicant((p) => ({ ...p, ...obj }));
  const updateBiz = (obj) => setBusiness((p) => ({ ...p, ...obj }));

  const canNext = () => {
    if (step === 1) return !!countryCode;
    if (step === 2) return applicant.name && applicant.age;
    if (step === 7) return business.signatory_id && business.entity_id;
    return true;
  };

  const saveApplication = async (silent = false) => {
    if (!countryCode) {
      toast.error("Pick a country first");
      return null;
    }
    setSaving(true);
    try {
      const res = await api.post("/visa/application", {
        token: getToken(),
        application_id: applicationId || undefined,
        country_code: countryCode,
        applicant,
        business,
        status: applicationId ? "draft" : "draft",
      });
      const aid = res.data?.application_id;
      if (aid) {
        setApplicationId(aid);
        if (!silent) toast.success(`Saved · ${aid}`);
        onSaved?.();
        return aid;
      }
    } catch (err) {
      toast.error("Save failed");
      console.error(err);
    } finally {
      setSaving(false);
    }
    return null;
  };

  const generateReport = async () => {
    const aid = applicationId || await saveApplication(true);
    if (!aid) return;
    setGeneratingReport(true);
    try {
      const res = await api.post(`/visa/application/${aid}/generate-report`, { token: getToken() });
      setReport(res.data?.report || null);
      toast.success("Readiness report generated");
    } catch {
      toast.error("Report generation failed");
    } finally {
      setGeneratingReport(false);
    }
  };

  const generateLetters = async () => {
    const aid = applicationId || await saveApplication(true);
    if (!aid) return;
    setGeneratingLetters(true);
    try {
      const res = await api.post(`/visa/application/${aid}/generate-letters`, {
        token: getToken(),
        application_id: aid,
        scope: letterScope,
      });
      setLetters(res.data?.letters || []);
      toast.success(`Drafted ${res.data?.letters?.length || 0} letters with Claude Sonnet 4.5`);
    } catch {
      toast.error("Letter generation failed");
    } finally {
      setGeneratingLetters(false);
    }
  };

  const downloadReport = () => {
    if (!applicationId) return;
    downloadAuthed(`/visa/application/${applicationId}/report-pdf`, `VisaReport_${applicationId}.pdf`)
      .catch((e) => toast.error(e.message));
  };
  const downloadChecklist = () => {
    if (!applicationId) return;
    downloadAuthed(`/visa/application/${applicationId}/checklist-excel`, `VisaChecklist_${applicationId}.xlsx`)
      .catch((e) => toast.error(e.message));
  };
  const downloadZip = () => {
    if (!applicationId) return;
    downloadAuthed(`/visa/application/${applicationId}/zip`, `VisaBundle_${applicationId}.zip`)
      .catch((e) => toast.error(e.message));
  };
  const downloadLetterWord = (letter_key, letter_name) => {
    if (!applicationId) return;
    downloadAuthed(
      `/visa/application/${applicationId}/letter/${letter_key}/word`,
      `${letter_name}_${applicationId}.docx`,
    ).catch((e) => toast.error(e.message));
  };

  const openLawyerBundle = async () => {
    if (!applicationId) {
      toast.error("Save the application first");
      return;
    }
    setLawyerOpen(true);
    setLawyerLoading(true);
    setLawyerPreview(null);
    try {
      const res = await api.post(`/visa/application/${applicationId}/lawyer-bundle-preview`, {
        token: getToken(),
        lawyer_name: lawyerForm.lawyer_name,
        lawyer_firm: lawyerForm.lawyer_firm,
        notes: lawyerForm.notes,
      });
      setLawyerPreview(res.data);
    } catch (err) {
      toast.error("Failed to load bundle preview");
      console.error(err);
    } finally {
      setLawyerLoading(false);
    }
  };

  const downloadLawyerBundle = async () => {
    if (!applicationId) return;
    setLawyerDownloading(true);
    try {
      const applicantSafe = (applicant.name || "Applicant").replace(/\s+/g, "_");
      await downloadAuthedPost(
        `/visa/application/${applicationId}/lawyer-bundle`,
        {
          lawyer_name: lawyerForm.lawyer_name,
          lawyer_firm: lawyerForm.lawyer_firm,
          notes: lawyerForm.notes,
        },
        `PB_VisaBundle_${applicantSafe}_${countryCode}_${applicationId}.zip`,
      );
      toast.success("Lawyer bundle downloaded — ready to email to counsel");
      setLawyerOpen(false);
      onSaved?.();
    } catch (e) {
      toast.error(e.message || "Bundle download failed");
    } finally {
      setLawyerDownloading(false);
    }
  };

  const resetWizard = () => {
    setStep(1);
    setApplicationId("");
    setCountryCode("");
    setApplicant({ ...EMPTY_APPLICANT });
    setBusiness({ ...EMPTY_BUSINESS });
    setReport(null);
    setLetters([]);
  };

  return (
    <Card data-testid="visa-wizard-card">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle>Visa Readiness Wizard</CardTitle>
            <CardDescription>
              Step {step} of {STEPS.length} — {STEPS[step - 1]?.label}
              {applicationId && <span className="ml-2 font-mono text-xs">[{applicationId}]</span>}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {applicationId && (
              <Button variant="outline" size="sm" onClick={resetWizard} data-testid="visa-wizard-new">
                <FilePlus2 className="h-4 w-4 mr-1" /> Start Fresh
              </Button>
            )}
          </div>
        </div>
        {/* Stepper */}
        <div className="flex items-center gap-1 mt-3 overflow-x-auto">
          {STEPS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStep(s.id)}
              className={`px-2 py-1 rounded text-xs flex items-center gap-1 whitespace-nowrap ${
                step === s.id ? "bg-primary text-white" : step > s.id ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
              }`}
              data-testid={`visa-step-${s.id}`}
            >
              <s.icon className="h-3 w-3" /> {s.id}. {s.label}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* STEP 1: COUNTRY */}
        {step === 1 && (
          <div className="space-y-4">
            <Label>Destination Country *</Label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3" data-testid="visa-country-grid">
              {countries.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => setCountryCode(c.code)}
                  className={`p-4 border rounded-lg text-left transition ${
                    countryCode === c.code ? "border-primary bg-primary/5 ring-2 ring-primary" : "border-slate-200 hover:border-slate-400"
                  }`}
                  data-testid={`visa-country-${c.code}`}
                >
                  <div className="text-2xl">{c.flag || "🌐"}</div>
                  <div className="font-semibold">{c.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">{c.notes}</div>
                </button>
              ))}
            </div>
            {countryCode && pathways.length > 0 && (
              <div>
                <Label className="mt-4">Available Pathways</Label>
                <ul className="text-sm space-y-1 mt-2">
                  {pathways.map((p) => (
                    <li key={p.id} className="border-l-2 border-primary/40 pl-2">
                      <b>{p.name}</b> · {p.type} · {p.duration_months || "?"} months
                      <div className="text-xs text-muted-foreground">{p.summary}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: APPLICANT */}
        {step === 2 && (
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Full Name *"><Input value={applicant.name} onChange={(e) => update({ name: e.target.value })} data-testid="visa-applicant-name" /></Field>
            <Field label="Age *"><Input type="number" value={applicant.age} onChange={(e) => update({ age: e.target.value })} data-testid="visa-applicant-age" /></Field>
            <Field label="Date of Birth"><Input type="date" value={applicant.date_of_birth} onChange={(e) => update({ date_of_birth: e.target.value })} /></Field>
            <Field label="Nationality"><Input value={applicant.nationality} onChange={(e) => update({ nationality: e.target.value })} /></Field>
            <Field label="Marital Status">
              <Select value={applicant.marital_status} onValueChange={(v) => update({ marital_status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Single">Single</SelectItem>
                  <SelectItem value="Married">Married</SelectItem>
                  <SelectItem value="Divorced">Divorced</SelectItem>
                  <SelectItem value="Widowed">Widowed</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Current Location"><Input value={applicant.current_location} onChange={(e) => update({ current_location: e.target.value })} /></Field>
            <Field label="Passport Number"><Input value={applicant.passport_number} onChange={(e) => update({ passport_number: e.target.value })} /></Field>
            <Field label="Passport Expiry"><Input type="date" value={applicant.passport_expiry} onChange={(e) => update({ passport_expiry: e.target.value })} /></Field>
          </div>
        )}

        {/* STEP 3: EDU & SKILLS */}
        {step === 3 && (
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Highest Education"><Input value={applicant.education_highest} onChange={(e) => update({ education_highest: e.target.value })} placeholder="e.g. B.Tech, MBA" /></Field>
            <Field label="Institution"><Input value={applicant.education_institution} onChange={(e) => update({ education_institution: e.target.value })} /></Field>
            <Field label="English Test Status">
              <Select value={applicant.english_test_status} onValueChange={(v) => update({ english_test_status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Not Started">Not Started</SelectItem>
                  <SelectItem value="Booked">Booked</SelectItem>
                  <SelectItem value="Passed">Passed</SelectItem>
                  <SelectItem value="Exempt">Exempt</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="English Test Score"><Input value={applicant.english_test_score} onChange={(e) => update({ english_test_score: e.target.value })} placeholder="e.g. IELTS 7.5" /></Field>
            <Field label="Skills (comma separated)" wide>
              <Input value={applicant.skills} onChange={(e) => update({ skills: e.target.value })} placeholder="Franchise operations, F&B management, team leadership…" />
            </Field>
          </div>
        )}

        {/* STEP 4: EXPERIENCE */}
        {step === 4 && (
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Current Role"><Input value={applicant.current_role} onChange={(e) => update({ current_role: e.target.value })} /></Field>
            <Field label="Total Years of Experience"><Input type="number" value={applicant.years_of_experience} onChange={(e) => update({ years_of_experience: e.target.value })} data-testid="visa-yoe" /></Field>
          </div>
        )}

        {/* STEP 5: FAMILY */}
        {step === 5 && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Switch checked={!!applicant.family_included} onCheckedChange={(v) => update({ family_included: v })} data-testid="visa-family-toggle" />
              <Label>Include family / spouse / children in the visa application</Label>
            </div>
            {applicant.family_included && (
              <div className="grid md:grid-cols-2 gap-4">
                <Field label="Spouse Name"><Input value={applicant.spouse_name} onChange={(e) => update({ spouse_name: e.target.value })} /></Field>
                <Field label="Spouse DOB"><Input type="date" value={applicant.spouse_dob} onChange={(e) => update({ spouse_dob: e.target.value })} /></Field>
                <Field label="Children (count & ages)" wide>
                  <Input value={applicant.children} onChange={(e) => update({ children: e.target.value })} placeholder="e.g. 2 children (ages 8 and 5)" />
                </Field>
              </div>
            )}
          </div>
        )}

        {/* STEP 6: BUSINESS / ROLE */}
        {step === 6 && (
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Role Offered"><Input value={business.role_offered} onChange={(e) => updateBiz({ role_offered: e.target.value })} placeholder="e.g. Director — Australia Operations" /></Field>
            <Field label="Proposed Salary"><Input value={business.proposed_salary} onChange={(e) => updateBiz({ proposed_salary: e.target.value })} placeholder="e.g. AUD 110,000 p.a." /></Field>
            <Field label="Proposed Start Date"><Input type="date" value={business.proposed_start_date} onChange={(e) => updateBiz({ proposed_start_date: e.target.value })} /></Field>
            <Field label="Proposed Centre / Branch"><Input value={business.proposed_centre} onChange={(e) => updateBiz({ proposed_centre: e.target.value })} placeholder="e.g. Purnabramha Melbourne CBD" /></Field>
            <Field label="Centre Address" wide><Textarea rows={2} value={business.proposed_centre_address} onChange={(e) => updateBiz({ proposed_centre_address: e.target.value })} /></Field>
            <Field label="Reporting To"><Input value={business.reporting_to} onChange={(e) => updateBiz({ reporting_to: e.target.value })} /></Field>
            <Field label="Key Responsibilities" wide><Textarea rows={3} value={business.role_responsibilities} onChange={(e) => updateBiz({ role_responsibilities: e.target.value })} /></Field>
          </div>
        )}

        {/* STEP 7: SIGNATORY & ENTITY */}
        {step === 7 && (
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Signing Entity *">
              <Select value={business.entity_id} onValueChange={(v) => updateBiz({ entity_id: v })}>
                <SelectTrigger data-testid="visa-entity-select"><SelectValue placeholder="Select entity" /></SelectTrigger>
                <SelectContent>
                  {entities.map((e) => <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Signatory *">
              <Select value={business.signatory_id} onValueChange={(v) => updateBiz({ signatory_id: v })}>
                <SelectTrigger data-testid="visa-signatory-select"><SelectValue placeholder="Select signatory" /></SelectTrigger>
                <SelectContent>
                  {signatories.map((s) => <SelectItem key={s.id} value={s.id}>{s.name} · {s.role}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
          </div>
        )}

        {/* STEP 8: DOCS READY */}
        {step === 8 && (
          <div className="space-y-3">
            <Label className="text-base">Which evidentiary documents are already available?</Label>
            <ToggleRow
              checked={business.franchise_letter_available}
              onChange={(v) => updateBiz({ franchise_letter_available: v })}
              label="Franchise / Master-franchise support letter"
              hint="Strong factor for franchise-driven visa narratives."
            />
            <ToggleRow
              checked={business.business_plan_available}
              onChange={(v) => updateBiz({ business_plan_available: v })}
              label="Business plan / expansion plan"
              hint="Required for investor / business-owner pathways."
            />
            <ToggleRow
              checked={business.financial_proof_available}
              onChange={(v) => updateBiz({ financial_proof_available: v })}
              label="Financial proof (settlement / business funds)"
              hint="Bank statements, audited financials, ITRs."
            />
          </div>
        )}

        {/* STEP 9: GOALS & NOTES */}
        {step === 9 && (
          <div className="grid md:grid-cols-1 gap-4">
            <Field label="Goal Summary"><Textarea rows={3} value={business.goal_summary} onChange={(e) => updateBiz({ goal_summary: e.target.value })} placeholder="What is the applicant ultimately trying to achieve? (e.g., PR via 482→186)" /></Field>
            <Field label="Consultant Notes / Internal Context"><Textarea rows={3} value={business.consultant_notes} onChange={(e) => updateBiz({ consultant_notes: e.target.value })} placeholder="Anything the immigration lawyer should know." /></Field>
          </div>
        )}

        {/* STEP 10: REVIEW & SAVE */}
        {step === 10 && (
          <ReviewStep
            applicationId={applicationId}
            countryCode={countryCode}
            countries={countries}
            applicant={applicant}
            business={business}
            report={report}
            letters={letters}
            templates={templates}
            letterScope={letterScope}
            setLetterScope={setLetterScope}
            generatingReport={generatingReport}
            generatingLetters={generatingLetters}
            saving={saving}
            onSave={() => saveApplication(false)}
            onGenerateReport={generateReport}
            onGenerateLetters={generateLetters}
            onDownloadReport={downloadReport}
            onDownloadChecklist={downloadChecklist}
            onDownloadZip={downloadZip}
            onDownloadLetterWord={downloadLetterWord}
            onOpenLawyerBundle={openLawyerBundle}
            onBuildCompleteBundle={buildCompleteBundle}
            building={building}
          />
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between border-t pt-4">
          <Button variant="outline" size="sm" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))} data-testid="visa-step-prev">
            <ChevronLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <div className="text-xs text-muted-foreground">
            {applicationId ? `Draft saved · ${applicationId}` : "Draft not saved yet"}
          </div>
          {step < STEPS.length ? (
            <Button size="sm" disabled={!canNext()} onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))} data-testid="visa-step-next">
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button size="sm" onClick={() => saveApplication(false)} disabled={saving} data-testid="visa-step-save">
              {saving && <Loader2 className="h-4 w-4 mr-1 animate-spin" />} Save Draft
            </Button>
          )}
        </div>
      </CardContent>

      {/* Send to Immigration Lawyer dialog */}
      <Dialog open={lawyerOpen} onOpenChange={setLawyerOpen}>
        <DialogContent className="max-w-2xl" data-testid="visa-lawyer-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" /> Send to Immigration Lawyer
            </DialogTitle>
            <DialogDescription>
              Preview the complete bundle Purnabramha will hand to immigration counsel — cover letter, readiness report, checklist, all drafted support letters and a manifest.
            </DialogDescription>
          </DialogHeader>

          <div className="grid md:grid-cols-2 gap-3">
            <Field label="Lawyer Name">
              <Input
                value={lawyerForm.lawyer_name}
                onChange={(e) => setLawyerForm((p) => ({ ...p, lawyer_name: e.target.value }))}
                placeholder="e.g. Ms. Asha Khan"
                data-testid="visa-lawyer-name"
              />
            </Field>
            <Field label="Lawyer Firm">
              <Input
                value={lawyerForm.lawyer_firm}
                onChange={(e) => setLawyerForm((p) => ({ ...p, lawyer_firm: e.target.value }))}
                placeholder="e.g. Khan Immigration LLP"
                data-testid="visa-lawyer-firm"
              />
            </Field>
            <Field label="Specific Notes / Requests" wide>
              <Textarea
                rows={2}
                value={lawyerForm.notes}
                onChange={(e) => setLawyerForm((p) => ({ ...p, notes: e.target.value }))}
                placeholder="Anything you want the lawyer to focus on (e.g. expedite AU 482 review, confirm IELTS waiver eligibility)…"
                data-testid="visa-lawyer-notes"
              />
            </Field>
          </div>

          <div className="border rounded p-3 bg-slate-50 max-h-80 overflow-auto" data-testid="visa-lawyer-preview">
            {lawyerLoading ? (
              <div className="flex items-center text-sm text-muted-foreground"><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading bundle preview…</div>
            ) : lawyerPreview ? (
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">
                  Bundle for <b>{lawyerPreview.applicant_name || "—"}</b> · {lawyerPreview.country_code || "—"} · <b>{lawyerPreview.file_count}</b> file(s)
                </div>
                {(lawyerPreview.warnings || []).map((w, i) => (
                  <div key={i} className="text-xs flex items-start gap-1 bg-amber-100 border border-amber-300 rounded p-2 text-amber-800" data-testid={`visa-lawyer-warning-${i}`}>
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" /> <span>{w}</span>
                  </div>
                ))}
                <table className="w-full text-xs">
                  <thead className="text-left bg-white border-b">
                    <tr>
                      <th className="p-1 w-12">#</th>
                      <th className="p-1">File</th>
                      <th className="p-1 w-16">Kind</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(lawyerPreview.files || []).map((f) => (
                      <tr key={f.name} className="border-b last:border-0">
                        <td className="p-1 font-mono">{f.order}</td>
                        <td className="p-1">
                          <div className="font-medium">{f.name}</div>
                          <div className="text-muted-foreground">{f.description}</div>
                        </td>
                        <td className="p-1"><Badge variant="outline" className="text-xs">{f.kind}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No preview yet.</div>
            )}
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2 items-stretch">
            <Button variant="outline" size="sm" onClick={() => setLawyerOpen(false)} data-testid="visa-lawyer-cancel">Close</Button>
            <Button
              size="sm"
              onClick={downloadLawyerBundle}
              disabled={!lawyerPreview || lawyerDownloading}
              data-testid="visa-lawyer-download"
            >
              {lawyerDownloading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Send className="h-4 w-4 mr-1" />}
              Download Bundle (.zip)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Review & Output                                            */
/* ────────────────────────────────────────────────────────── */
function ReviewStep({
  applicationId, countryCode, countries, applicant, business, report, letters,
  templates, letterScope, setLetterScope,
  generatingReport, generatingLetters, saving,
  onSave, onGenerateReport, onGenerateLetters,
  onDownloadReport, onDownloadChecklist, onDownloadZip, onDownloadLetterWord,
  onOpenLawyerBundle, onBuildCompleteBundle, building,
}) {
  const countryName = countries.find((c) => c.code === countryCode)?.name || countryCode;

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="border-primary/30">
          <CardHeader className="pb-2"><CardTitle className="text-base">Summary</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-1">
            <div><b>Country:</b> {countryName}</div>
            <div><b>Applicant:</b> {applicant.name} (age {applicant.age})</div>
            <div><b>Experience:</b> {applicant.years_of_experience || 0} years</div>
            <div><b>English:</b> {applicant.english_test_status}</div>
            <div><b>Family included:</b> {applicant.family_included ? "Yes" : "No"}</div>
            <div><b>Role:</b> {business.role_offered || "—"}</div>
            <div><b>Centre:</b> {business.proposed_centre || "—"}</div>
          </CardContent>
        </Card>

        <Card className="border-emerald-300">
          <CardHeader className="pb-2"><CardTitle className="text-base">Generate Outputs</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button onClick={onSave} disabled={saving} size="sm" variant="outline" data-testid="visa-save-btn">
                {saving && <Loader2 className="h-4 w-4 mr-1 animate-spin" />} Save Draft
              </Button>
              <Button onClick={onGenerateReport} disabled={generatingReport || !applicationId && !applicant.name} size="sm" data-testid="visa-generate-report-btn">
                {generatingReport ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />}
                Generate Readiness Report
              </Button>
            </div>

            <div className="border-t pt-3 space-y-2">
              <div className="flex items-center gap-2">
                <Label className="text-xs">Letter Scope:</Label>
                <Select value={letterScope} onValueChange={setLetterScope}>
                  <SelectTrigger className="h-8 w-44" data-testid="visa-letter-scope">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All letters (15)</SelectItem>
                    <SelectItem value="company">Company letters</SelectItem>
                    <SelectItem value="franchise">Franchise letters</SelectItem>
                    <SelectItem value="personal">Personal / experience</SelectItem>
                    <SelectItem value="resolutions">Resolutions only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={onGenerateLetters} disabled={generatingLetters || !applicationId} size="sm" variant="default" data-testid="visa-generate-letters-btn">
                {generatingLetters ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <FileText className="h-4 w-4 mr-1" />}
                Generate AI Letters (Claude Sonnet 4.5)
              </Button>
            </div>

            <div className="border-t pt-3 flex flex-wrap gap-2">
              <Button size="sm" variant="outline" disabled={!report} onClick={onDownloadReport} data-testid="visa-dl-report">
                <Download className="h-3.5 w-3.5 mr-1" /> PDF Report
              </Button>
              <Button size="sm" variant="outline" disabled={!report} onClick={onDownloadChecklist} data-testid="visa-dl-checklist">
                <Download className="h-3.5 w-3.5 mr-1" /> Excel Checklist
              </Button>
              <Button size="sm" variant="outline" disabled={!applicationId} onClick={onDownloadZip} data-testid="visa-dl-zip">
                <FileArchive className="h-3.5 w-3.5 mr-1" /> ZIP Bundle
              </Button>
              <Button
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                disabled={!applicationId}
                onClick={onOpenLawyerBundle}
                data-testid="visa-lawyer-bundle-btn"
              >
                <Briefcase className="h-3.5 w-3.5 mr-1" /> Send to Immigration Lawyer
              </Button>
              <Button
                size="sm"
                className="bg-amber-600 hover:bg-amber-700 text-white"
                disabled={!applicationId || building}
                onClick={onBuildCompleteBundle}
                data-testid="visa-complete-bundle-btn"
              >
                {building ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <FileArchive className="h-3.5 w-3.5 mr-1" />}
                Generate Complete Bundle
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report view */}
      {report && (
        <Card data-testid="visa-report-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" /> Readiness Report
              <Badge variant={report.suitability === "Strong" ? "default" : report.suitability === "Medium" ? "secondary" : "destructive"}>
                {report.suitability} · {report.score}/100
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {report.risks?.length > 0 && (
              <div>
                <div className="font-semibold flex items-center gap-1 text-red-700"><Ban className="h-4 w-4" /> Key Risks</div>
                <ul className="list-disc pl-6">{report.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
            )}

            {report.ranked_pathways?.length > 0 && (
              <div>
                <div className="font-semibold">Top Pathway Matches</div>
                <table className="w-full text-xs border mt-1">
                  <thead className="bg-slate-100"><tr>
                    <th className="p-1 text-left">Pathway</th><th className="p-1 text-left">Type</th><th className="p-1 text-left">Fit</th><th className="p-1 text-left">Duration</th>
                  </tr></thead>
                  <tbody>
                    {report.ranked_pathways.slice(0, 5).map((r, i) => (
                      <tr key={i} className="border-t">
                        <td className="p-1">{r.pathway.name}</td>
                        <td className="p-1">{r.pathway.type}</td>
                        <td className="p-1">{r.fit_score}/60</td>
                        <td className="p-1">{r.pathway.duration_months || "?"} mo</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="grid md:grid-cols-3 gap-4">
              {["company", "applicant", "family"].map((k) => (
                report.documents_required?.[k]?.length > 0 && (
                  <div key={k}>
                    <div className="font-semibold capitalize">{k} documents</div>
                    <ul className="text-xs list-disc pl-5">
                      {report.documents_required[k].map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                )
              ))}
            </div>

            {report.signatory_letter_plan?.length > 0 && (
              <div>
                <div className="font-semibold">Letter Checklist</div>
                <table className="w-full text-xs border mt-1">
                  <thead className="bg-slate-100"><tr>
                    <th className="p-1">#</th><th className="p-1 text-left">Letter</th><th className="p-1 text-left">Signed By</th><th className="p-1 text-left">Status</th>
                  </tr></thead>
                  <tbody>
                    {report.signatory_letter_plan.map((p) => (
                      <tr key={p.letter_key} className="border-t">
                        <td className="p-1 text-center">{p.sr_no}</td>
                        <td className="p-1">{p.letter_name}</td>
                        <td className="p-1">{p.signed_by}</td>
                        <td className="p-1"><Badge variant="outline" className="text-xs">{p.status}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="text-xs text-muted-foreground italic border-t pt-2">{report.disclaimer}</div>
          </CardContent>
        </Card>
      )}

      {/* Letters view */}
      {letters?.length > 0 && (
        <Card data-testid="visa-letters-card">
          <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5" /> Drafted Letters ({letters.length})</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-4">
              {letters.map((l) => (
                <details key={l.letter_key} className="border rounded p-3" data-testid={`visa-letter-${l.letter_key}`}>
                  <summary className="cursor-pointer font-medium flex items-center justify-between flex-wrap gap-2">
                    <span>{l.letter_name}</span>
                    <span className="flex items-center gap-2">
                      <Badge variant={l.status === "Drafted" ? "default" : "outline"}>{l.status}</Badge>
                      <Button size="sm" variant="ghost" onClick={(e) => { e.preventDefault(); onDownloadLetterWord(l.letter_key, l.letter_name); }} data-testid={`visa-letter-dl-${l.letter_key}`}>
                        <Download className="h-3.5 w-3.5 mr-1" /> .docx
                      </Button>
                    </span>
                  </summary>
                  <div className="text-xs text-muted-foreground mt-2"><b>Subject:</b> {l.subject}</div>
                  <pre className="whitespace-pre-wrap text-sm bg-slate-50 p-3 rounded border mt-2 max-h-96 overflow-auto">{l.body}</pre>
                </details>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Admin Panel                                                */
/* ────────────────────────────────────────────────────────── */
function AdminPanel({ countries, templates, entities, signatories, pathways, refreshPathways, onRefresh }) {
  const [adminTab, setAdminTab] = useState("countries");
  return (
    <Card data-testid="visa-admin-card">
      <CardHeader>
        <CardTitle>Visa Admin Panel</CardTitle>
        <CardDescription>Manage countries, pathways, letter templates, entities & signatories.</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs value={adminTab} onValueChange={setAdminTab}>
          <TabsList>
            <TabsTrigger value="countries" data-testid="visa-admin-tab-countries">Countries</TabsTrigger>
            <TabsTrigger value="pathways" data-testid="visa-admin-tab-pathways">Pathways</TabsTrigger>
            <TabsTrigger value="templates" data-testid="visa-admin-tab-templates">Letter Templates</TabsTrigger>
            <TabsTrigger value="entities" data-testid="visa-admin-tab-entities">Entities</TabsTrigger>
            <TabsTrigger value="signatories" data-testid="visa-admin-tab-signatories">Signatories</TabsTrigger>
            <TabsTrigger value="bundles" data-testid="visa-admin-tab-bundles">Bundle History</TabsTrigger>
          </TabsList>

          <TabsContent value="countries" className="mt-4">
            <CRUDTable
              rows={countries}
              keyField="code"
              fields={[
                { name: "code", label: "Code", required: true, w: "w-24" },
                { name: "name", label: "Name", required: true },
                { name: "flag", label: "Flag", w: "w-24" },
                { name: "currency", label: "Currency", w: "w-24" },
                { name: "notes", label: "Notes", textarea: true },
              ]}
              endpoint="/visa/admin/country"
              deleteEndpoint={(r) => `/visa/admin/country/${encodeURIComponent(r.code)}`}
              onRefresh={onRefresh}
              testid="countries"
            />
          </TabsContent>

          <TabsContent value="pathways" className="mt-4">
            <CRUDTable
              rows={pathways}
              keyField="id"
              fields={[
                { name: "id", label: "ID", required: true, w: "w-32" },
                { name: "country_code", label: "Country", required: true, w: "w-24",
                  select: countries.map((c) => ({ value: c.code, label: c.name })) },
                { name: "name", label: "Name", required: true },
                { name: "type", label: "Type", w: "w-32",
                  select: ["Permanent", "Temporary", "Provisional"].map((v) => ({ value: v, label: v })) },
                { name: "duration_months", label: "Months", w: "w-20", number: true },
                { name: "summary", label: "Summary", textarea: true },
              ]}
              endpoint="/visa/admin/pathway"
              deleteEndpoint={(r) => `/visa/admin/pathway/${encodeURIComponent(r.id)}`}
              onRefresh={() => { onRefresh(); refreshPathways(); }}
              testid="pathways"
              onLoadHint="Pathways list shows last-loaded country. Open the wizard's Country step to filter."
            />
          </TabsContent>

          <TabsContent value="templates" className="mt-4">
            <CRUDTable
              rows={templates}
              keyField="id"
              fields={[
                { name: "id", label: "Key", required: true, w: "w-44" },
                { name: "name", label: "Name", required: true },
                { name: "subject", label: "Subject" },
                { name: "purpose", label: "Purpose", textarea: true },
                { name: "body_template", label: "Body Template (optional)", textarea: true },
              ]}
              endpoint="/visa/admin/letter-template"
              deleteEndpoint={(r) => `/visa/admin/letter-template/${encodeURIComponent(r.id)}`}
              onRefresh={onRefresh}
              testid="templates"
            />
          </TabsContent>

          <TabsContent value="entities" className="mt-4">
            <CRUDTable
              rows={entities}
              keyField="id"
              fields={[
                { name: "id", label: "ID", w: "w-32" },
                { name: "name", label: "Name", required: true },
                { name: "country_code", label: "Country", w: "w-24" },
                { name: "registration_number", label: "Reg #" },
                { name: "address", label: "Address", textarea: true },
                { name: "notes", label: "Notes" },
              ]}
              endpoint="/visa/admin/entity"
              deleteEndpoint={(r) => `/visa/admin/entity/${encodeURIComponent(r.id)}`}
              onRefresh={onRefresh}
              testid="entities"
            />
          </TabsContent>

          <TabsContent value="signatories" className="mt-4">
            <CRUDTable
              rows={signatories}
              keyField="id"
              fields={[
                { name: "id", label: "ID", w: "w-32" },
                { name: "name", label: "Name", required: true },
                { name: "role", label: "Role / Designation", required: true },
                { name: "entity_id", label: "Entity",
                  select: entities.map((e) => ({ value: e.id, label: e.name })) },
                { name: "email", label: "Email" },
                { name: "phone", label: "Phone" },
              ]}
              endpoint="/visa/admin/signatory"
              deleteEndpoint={(r) => `/visa/admin/signatory/${encodeURIComponent(r.id)}`}
              onRefresh={onRefresh}
              testid="signatories"
            />
          </TabsContent>

          <TabsContent value="bundles" className="mt-4">
            <BundleHistory />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

/* Generic Admin CRUD table */
function CRUDTable({ rows, keyField, fields, endpoint, deleteEndpoint, onRefresh, testid, onLoadHint }) {
  const [draft, setDraft] = useState({});
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const startEdit = (r) => { setEditing(r[keyField]); setDraft({ ...r }); };
  const startNew = () => { setEditing("__new__"); setDraft({}); };
  const cancel = () => { setEditing(null); setDraft({}); };

  const save = async () => {
    for (const f of fields) {
      if (f.required && !draft[f.name]) {
        toast.error(`${f.label} is required`);
        return;
      }
    }
    setSaving(true);
    try {
      await api.post(endpoint, { token: getToken(), ...draft });
      toast.success("Saved");
      cancel();
      onRefresh();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const del = async (r) => {
    if (!window.confirm(`Delete ${r[keyField]}?`)) return;
    try {
      await api.delete(deleteEndpoint(r));
      toast.success("Deleted");
      onRefresh();
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="space-y-3" data-testid={`visa-crud-${testid}`}>
      <div className="flex items-center justify-between">
        <Button size="sm" onClick={startNew} data-testid={`visa-crud-${testid}-new`}>
          <Plus className="h-4 w-4 mr-1" /> Add New
        </Button>
        {onLoadHint && <div className="text-xs text-muted-foreground">{onLoadHint}</div>}
      </div>

      {editing && (
        <Card className="border-primary/30">
          <CardContent className="pt-4 grid md:grid-cols-2 gap-3">
            {fields.map((f) => (
              <Field key={f.name} label={f.label + (f.required ? " *" : "")} wide={f.textarea}>
                {f.select ? (
                  <Select value={draft[f.name] || ""} onValueChange={(v) => setDraft({ ...draft, [f.name]: v })}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>{f.select.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
                  </Select>
                ) : f.textarea ? (
                  <Textarea rows={2} value={draft[f.name] || ""} onChange={(e) => setDraft({ ...draft, [f.name]: e.target.value })} />
                ) : (
                  <Input
                    type={f.number ? "number" : "text"}
                    value={draft[f.name] || ""}
                    onChange={(e) => setDraft({ ...draft, [f.name]: f.number ? Number(e.target.value) : e.target.value })}
                  />
                )}
              </Field>
            ))}
            <div className="md:col-span-2 flex justify-end gap-2 mt-2">
              <Button variant="outline" size="sm" onClick={cancel}>Cancel</Button>
              <Button size="sm" onClick={save} disabled={saving} data-testid={`visa-crud-${testid}-save`}>
                {saving && <Loader2 className="h-4 w-4 mr-1 animate-spin" />} Save
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="overflow-x-auto border rounded">
        <table className="w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              {fields.map((f) => <th key={f.name} className={`p-2 text-left ${f.w || ""}`}>{f.label}</th>)}
              <th className="p-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={fields.length + 1} className="p-4 text-center text-muted-foreground">No records.</td></tr>
            ) : rows.map((r) => (
              <tr key={r[keyField]} className="border-t" data-testid={`visa-crud-${testid}-row-${r[keyField]}`}>
                {fields.map((f) => (
                  <td key={f.name} className="p-2 text-xs">
                    {f.textarea ? (
                      <div className="line-clamp-2">{r[f.name]}</div>
                    ) : (
                      String(r[f.name] ?? "")
                    )}
                  </td>
                ))}
                <td className="p-2 text-right space-x-1">
                  <Button size="sm" variant="outline" onClick={() => startEdit(r)} data-testid={`visa-crud-${testid}-edit-${r[keyField]}`}>Edit</Button>
                  <Button size="sm" variant="ghost" onClick={() => del(r)} data-testid={`visa-crud-${testid}-del-${r[keyField]}`}>
                    <Trash2 className="h-3.5 w-3.5 text-red-600" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Small UI helpers                                           */
/* ────────────────────────────────────────────────────────── */
function Field({ label, children, wide }) {
  return (
    <div className={wide ? "md:col-span-2 space-y-1" : "space-y-1"}>
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}

function ToggleRow({ checked, onChange, label, hint }) {
  return (
    <div className="flex items-start gap-3 border rounded p-3">
      <Switch checked={!!checked} onCheckedChange={onChange} />
      <div>
        <div className="text-sm font-medium">{label}</div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </div>
    </div>
  );
}


/* ────────────────────────────────────────────────────────── */
/* AI Recommender Section                                     */
/* ────────────────────────────────────────────────────────── */
const EMPTY_RECOMMEND_INPUT = {
  applicant_name: "",
  current_role: "",
  age: "",
  years_of_experience: "",
  nationality: "Indian",
  english_status: "Not Started",
  family_included: false,
  spouse_work_rights_required: false,
  shareholding_pct: "",
  has_existing_operations: false,
  has_expansion_plan: false,
  has_business_plan: false,
  has_financial_proof: false,
  has_franchise_letter: false,
  has_skills_assessment: false,
  goal: "",
  country_codes: [],
  use_ai_narrative: true,
};

function RecommenderSection({ countries, onProceedToWizard }) {
  const [input, setInput] = useState({ ...EMPTY_RECOMMEND_INPUT });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [showAll, setShowAll] = useState(false);

  const upd = (obj) => setInput((p) => ({ ...p, ...obj }));
  const toggleCountry = (code) => {
    setInput((p) => {
      const cs = p.country_codes.includes(code)
        ? p.country_codes.filter((c) => c !== code)
        : [...p.country_codes, code];
      return { ...p, country_codes: cs };
    });
  };

  const run = async () => {
    if (!input.applicant_name) { toast.error("Applicant name is required"); return; }
    if (!input.age) { toast.error("Applicant age is required"); return; }
    setLoading(true);
    setResults(null);
    try {
      const payload = {
        token: getToken(),
        ...input,
        age: input.age ? Number(input.age) : null,
        years_of_experience: input.years_of_experience ? Number(input.years_of_experience) : null,
        shareholding_pct: input.shareholding_pct ? Number(input.shareholding_pct) : null,
        country_codes: input.country_codes.length ? input.country_codes : null,
      };
      const res = await api.post("/visa/recommend", payload);
      setResults(res.data);
      toast.success(`Found ${res.data?.top?.length || 0} matching pathways across ${input.country_codes.length || countries.length} countries`);
    } catch (err) {
      toast.error("Recommendation failed");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const proceed = (item) => {
    const p = item.pathway;
    const seed = {
      country_code: p.country_code,
      pathway_id: p.id,
      applicant: {
        name: input.applicant_name,
        age: input.age ? Number(input.age) : null,
        years_of_experience: input.years_of_experience ? Number(input.years_of_experience) : null,
        nationality: input.nationality,
        english_test_status: input.english_status,
        family_included: input.family_included,
        current_role: input.current_role,
      },
      business: {
        goal_summary: input.goal,
        franchise_letter_available: input.has_franchise_letter,
        business_plan_available: input.has_business_plan,
        financial_proof_available: input.has_financial_proof,
        selected_pathway_id: p.id,
      },
    };
    onProceedToWizard?.(seed);
    toast.success(`Loaded ${p.name} into the Manual Wizard for refinement`);
  };

  return (
    <div className="space-y-6" data-testid="visa-recommender-section">
      <Card className="border-primary/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5" /> AI Visa Advisor</CardTitle>
          <CardDescription>
            Describe the applicant and goals — the system compares every pathway across all priority countries and ranks the best fit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-3">
            <Field label="Applicant Name *">
              <Input value={input.applicant_name} onChange={(e) => upd({ applicant_name: e.target.value })} placeholder="e.g. Sandeep Kathale" data-testid="rec-name" />
            </Field>
            <Field label="Current Role">
              <Input value={input.current_role} onChange={(e) => upd({ current_role: e.target.value })} placeholder="e.g. Managing Director" data-testid="rec-role" />
            </Field>
            <Field label="Age *">
              <Input type="number" value={input.age} onChange={(e) => upd({ age: e.target.value })} data-testid="rec-age" />
            </Field>
            <Field label="Years of Experience">
              <Input type="number" value={input.years_of_experience} onChange={(e) => upd({ years_of_experience: e.target.value })} data-testid="rec-yoe" />
            </Field>
            <Field label="Nationality">
              <Input value={input.nationality} onChange={(e) => upd({ nationality: e.target.value })} />
            </Field>
            <Field label="English Status">
              <Select value={input.english_status} onValueChange={(v) => upd({ english_status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Not Started">Not Started</SelectItem>
                  <SelectItem value="Booked">Booked</SelectItem>
                  <SelectItem value="Passed">Passed</SelectItem>
                  <SelectItem value="Exempt">Exempt</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Shareholding % in destination entity">
              <Input type="number" value={input.shareholding_pct} onChange={(e) => upd({ shareholding_pct: e.target.value })} placeholder="e.g. 35" />
            </Field>
            <Field label="Goal" wide>
              <Input value={input.goal} onChange={(e) => upd({ goal: e.target.value })} placeholder="e.g. PR + family + spouse work rights" data-testid="rec-goal" />
            </Field>
          </div>

          <div>
            <Label className="text-xs">Country shortlist (leave empty to scan all)</Label>
            <div className="flex flex-wrap gap-2 mt-1" data-testid="rec-countries">
              {countries.map((c) => {
                const on = input.country_codes.includes(c.code);
                return (
                  <button
                    key={c.code}
                    type="button"
                    onClick={() => toggleCountry(c.code)}
                    className={`px-3 py-1 text-xs rounded-full border ${on ? "bg-primary text-white border-primary" : "bg-white text-slate-700"}`}
                    data-testid={`rec-country-${c.code}`}
                  >
                    {c.flag || "🌐"} {c.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-2">
            <ToggleRow checked={input.family_included} onChange={(v) => upd({ family_included: v })} label="Family / spouse / children included" hint="Influences spouse work-rights scoring." />
            <ToggleRow checked={input.has_existing_operations} onChange={(v) => upd({ has_existing_operations: v })} label="Existing operations in destination country" hint="Strong factor for 186 / L-1A / EB-1C." />
            <ToggleRow checked={input.has_expansion_plan} onChange={(v) => upd({ has_expansion_plan: v })} label="Documented expansion plan" />
            <ToggleRow checked={input.has_business_plan} onChange={(v) => upd({ has_business_plan: v })} label="Business plan available" />
            <ToggleRow checked={input.has_financial_proof} onChange={(v) => upd({ has_financial_proof: v })} label="Financial proof / audited financials" />
            <ToggleRow checked={input.has_franchise_letter} onChange={(v) => upd({ has_franchise_letter: v })} label="Franchise support letter ready" />
            <ToggleRow checked={input.has_skills_assessment} onChange={(v) => upd({ has_skills_assessment: v })} label="Skills assessment completed (AU)" />
            <ToggleRow checked={input.use_ai_narrative} onChange={(v) => upd({ use_ai_narrative: v })} label="Add Claude Sonnet 4.5 narrative reasoning to top 5" hint="Adds ~30s but produces a polished 'Why' paragraph per pathway." />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => { setInput({ ...EMPTY_RECOMMEND_INPUT }); setResults(null); }} data-testid="rec-reset">Reset</Button>
            <Button size="sm" onClick={run} disabled={loading} data-testid="rec-run">
              {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />}
              Get Recommendations
            </Button>
          </div>
        </CardContent>
      </Card>

      {results && (
        <div className="space-y-3" data-testid="visa-recommender-results">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recommendations</h2>
            <Button size="sm" variant="ghost" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Show top 5" : `Show all ${results.all?.length || 0} pathways`}
            </Button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {(showAll ? results.all : results.top).map((item, idx) => {
              const p = item.pathway;
              const colour = item.suitability === "Strong" ? "border-emerald-400 bg-emerald-50"
                : item.suitability === "Medium" ? "border-amber-400 bg-amber-50"
                : "border-rose-300 bg-rose-50";
              return (
                <Card key={p.id} className={`${colour} border-2`} data-testid={`rec-result-${p.id}`}>
                  <CardContent className="p-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="text-xs text-muted-foreground">#{idx + 1} · {item.country?.name || p.country_code} {item.country?.flag || ""}</div>
                        <div className="font-semibold leading-tight">{p.name}</div>
                      </div>
                      <Badge variant={item.suitability === "Strong" ? "default" : "secondary"}>
                        {item.suitability} · {item.score}/100
                      </Badge>
                    </div>
                    <div className="text-xs grid grid-cols-2 gap-x-2">
                      <div><b>Timeline:</b> {p.timeline_band || `${p.duration_months || "?"} months`}</div>
                      <div><b>Type:</b> {p.type}</div>
                      <div><b>Company cost:</b> {p.company_cost_band || "—"}</div>
                      <div><b>Applicant cost:</b> {p.applicant_cost_band || "—"}</div>
                    </div>
                    {item.ai_rationale && (
                      <div className="text-xs italic bg-white/60 border-l-2 border-primary/40 pl-2 py-1">
                        <Sparkles className="h-3 w-3 inline mr-1 text-primary" />{item.ai_rationale}
                      </div>
                    )}
                    {item.reasons?.length > 0 && (
                      <div className="text-xs">
                        <div className="font-semibold text-emerald-700">Why?</div>
                        <ul className="list-disc pl-5">{item.reasons.slice(0, 5).map((r, i) => <li key={i}>{r}</li>)}</ul>
                      </div>
                    )}
                    {item.risks?.length > 0 && (
                      <div className="text-xs">
                        <div className="font-semibold text-rose-700">Risk</div>
                        <ul className="list-disc pl-5">{item.risks.slice(0, 4).map((r, i) => <li key={i}>{r}</li>)}</ul>
                      </div>
                    )}
                    <div className="pt-1">
                      <Button size="sm" className="w-full" onClick={() => proceed(item)} data-testid={`rec-proceed-${p.id}`}>
                        Proceed with this visa <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────── */
/* Bundle History (admin)                                     */
/* ────────────────────────────────────────────────────────── */
function BundleHistory() {
  const [bundles, setBundles] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await api.get("/visa/admin/bundles");
      setBundles(r.data?.bundles || []);
    } catch {
      toast.error("Failed to load bundle history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const download = (b) => {
    downloadAuthed(`/visa/admin/bundle/${b.bundle_id}`, b.filename)
      .catch((e) => toast.error(e.message));
  };

  return (
    <Card data-testid="visa-bundle-history-card">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Bundle History</CardTitle>
          <CardDescription>Last 30 generated bundles available for re-download.</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading} data-testid="visa-bundle-history-refresh">
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {bundles.length === 0 ? (
          <div className="text-sm text-muted-foreground py-6 text-center" data-testid="visa-bundle-history-empty">No bundles generated yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border" data-testid="visa-bundle-history-table">
              <thead className="bg-slate-100">
                <tr>
                  <th className="p-2 text-left">When</th>
                  <th className="p-2 text-left">Applicant</th>
                  <th className="p-2 text-left">Kind</th>
                  <th className="p-2 text-left">Filename</th>
                  <th className="p-2 text-right">Size</th>
                  <th className="p-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {bundles.map((b) => (
                  <tr key={b.bundle_id} className="border-t" data-testid={`visa-bundle-history-row-${b.bundle_id}`}>
                    <td className="p-2 text-xs">{(b.generated_at || "").replace("T", " ").slice(0, 19)}</td>
                    <td className="p-2">{b.applicant_name || "—"}</td>
                    <td className="p-2"><Badge variant="outline">{b.kind}</Badge></td>
                    <td className="p-2 text-xs font-mono">{b.filename}</td>
                    <td className="p-2 text-right text-xs">{Math.round((b.size_bytes || 0) / 1024)} KB</td>
                    <td className="p-2 text-right">
                      <Button size="sm" variant="outline" onClick={() => download(b)} data-testid={`visa-bundle-dl-${b.bundle_id}`}>
                        <Download className="h-3.5 w-3.5 mr-1" /> Download
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

