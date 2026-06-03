import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { useAuth } from '@/App';
import { Loader2, Upload, Film, Download, Share2, History, X } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const MAX_BYTES = 60 * 1024 * 1024;       // 60 MB

export default function VideoCreator() {
  const { session } = useAuth();
  const fileInput = useRef(null);

  const [centers, setCenters] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);    // { video_id, size_kb, duration_s }
  const [videoFile, setVideoFile] = useState(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState(null);

  const [form, setForm] = useState({
    center: session?.center || '',
    headline: '',
    sub: '',
    byline: session?.managerName || '',
    use_logo: true,
    position: 'bottom',
  });

  // ── Load centers + history ────────────────────────────────────────────
  const loadCenters = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await fetch(`${API}/api/marketing/ads/masters`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (res.ok) { const d = await res.json(); setCenters(d.centers || []); }
    } catch (e) { /* ignore */ }
  }, [session?.token]);

  const loadHistory = useCallback(async () => {
    if (!session?.token) return;
    try {
      const res = await fetch(`${API}/api/marketing/videos/list`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token, limit: 12 }),
      });
      if (res.ok) { const d = await res.json(); setHistory(d.items || []); }
    } catch (e) { /* ignore */ }
  }, [session?.token]);

  useEffect(() => { loadCenters(); loadHistory(); }, [loadCenters, loadHistory]);

  // ── File picker ───────────────────────────────────────────────────────
  const onVideoSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_BYTES) {
      toast.error(`File too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Max ${MAX_BYTES / 1024 / 1024} MB.`);
      return;
    }
    setVideoFile(f);
    if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
    setVideoPreviewUrl(URL.createObjectURL(f));
    setResult(null);
  };

  const clearVideo = () => {
    if (videoPreviewUrl) URL.revokeObjectURL(videoPreviewUrl);
    setVideoFile(null);
    setVideoPreviewUrl(null);
    setResult(null);
    if (fileInput.current) fileInput.current.value = '';
  };

  // ── Submit (upload + brand) ───────────────────────────────────────────
  const generate = () => {
    if (!videoFile) { toast.error('Pick a video first'); return; }
    if (!form.center) { toast.error('Center required'); return; }
    setBusy(true);
    setProgress(0);
    setResult(null);
    const fd = new FormData();
    fd.append('token', session.token);
    fd.append('center', form.center);
    fd.append('headline', form.headline || '');
    fd.append('sub', form.sub || '');
    fd.append('byline', form.byline || '');
    fd.append('use_logo', form.use_logo ? 'true' : 'false');
    fd.append('position', form.position || 'bottom');
    fd.append('video', videoFile);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API}/api/marketing/videos/overlay`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      setBusy(false);
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const d = JSON.parse(xhr.responseText);
          setResult(d);
          toast.success(`Video ready — ${d.size_kb} KB · ${d.duration_s}s`);
          loadHistory();
        } catch {
          toast.error('Bad response from server');
        }
      } else {
        let msg = 'Processing failed';
        try { msg = JSON.parse(xhr.responseText).detail || msg; } catch { /* keep default */ }
        toast.error(msg);
      }
    };
    xhr.onerror = () => { setBusy(false); toast.error('Network error during upload'); };
    toast.info('Uploading & branding — this can take 30–90s depending on clip length');
    xhr.send(fd);
  };

  // ── Download / share ──────────────────────────────────────────────────
  const downloadVideo = async (video_id) => {
    try {
      const res = await fetch(`${API}/api/marketing/videos/asset/${video_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: session.token }),
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `Purnabramha_${video_id}.mp4`;
      a.click(); URL.revokeObjectURL(url);
      toast.success('Downloaded');
    } catch (e) { toast.error(e.message); }
  };

  const shareWhatsapp = () => {
    const text = encodeURIComponent(`${form.headline}\n${form.sub}\n\n— Purnabramha`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
    toast.info('WhatsApp opened — attach the downloaded video.');
  };

  const previewUrl = result
    ? `${API}/api/marketing/videos/asset/${result.video_id}?token=${session?.token}`
    : null;

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4" data-testid="video-creator">
      <div className="grid lg:grid-cols-5 gap-4">
        {/* Form */}
        <Card className="lg:col-span-2" data-testid="video-form-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Film className="w-5 h-5 text-rose-700" /> Brand a Video
            </CardTitle>
            <CardDescription>
              Upload a short clip (≤60s, ≤60 MB). We burn the Purnabramha logo +
              your caption (Marathi or English) using crisp typography.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs">Video clip *</Label>
              <div className="mt-1">
                {videoFile ? (
                  <div className="rounded-lg border-2 border-amber-300 p-2 flex items-center justify-between gap-2 bg-amber-50">
                    <div className="text-xs truncate">
                      <p className="font-medium truncate">{videoFile.name}</p>
                      <p className="text-muted-foreground">{(videoFile.size / 1024 / 1024).toFixed(1)} MB</p>
                    </div>
                    <Button size="sm" variant="ghost" onClick={clearVideo} data-testid="video-clear">
                      <X className="w-4 h-4 text-rose-700" />
                    </Button>
                  </div>
                ) : (
                  <label className="cursor-pointer flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg bg-amber-50/40 hover:bg-amber-50">
                    <input ref={fileInput} type="file" accept="video/*" className="hidden"
                      onChange={onVideoSelect} data-testid="video-input" />
                    <Upload className="w-5 h-5 mb-1 text-amber-700" />
                    <span className="text-xs text-amber-900">Upload video (≤60 MB)</span>
                  </label>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Center *</Label>
                <Select value={form.center} onValueChange={v => setForm(f => ({ ...f, center: v }))}>
                  <SelectTrigger className="h-9" data-testid="video-center"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    {centers.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Caption position</Label>
                <Select value={form.position} onValueChange={v => setForm(f => ({ ...f, position: v }))}>
                  <SelectTrigger className="h-9" data-testid="video-position"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bottom">Bottom (recommended)</SelectItem>
                    <SelectItem value="top">Top</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs">Headline (Marathi or English)</Label>
              <Input value={form.headline}
                onChange={e => setForm(f => ({ ...f, headline: e.target.value }))}
                placeholder="e.g. विसावा, चव घ्या, आनंद साजरा करा"
                data-testid="video-headline" />
            </div>
            <div>
              <Label className="text-xs">Sub-line (smaller)</Label>
              <Input value={form.sub}
                onChange={e => setForm(f => ({ ...f, sub: e.target.value }))}
                placeholder="e.g. Authentic Maharashtrian since 2008"
                data-testid="video-sub" />
            </div>
            <div>
              <Label className="text-xs">Byline (host / manager)</Label>
              <Input value={form.byline}
                onChange={e => setForm(f => ({ ...f, byline: e.target.value }))}
                placeholder="e.g. Jayanti Kathale"
                data-testid="video-byline" />
            </div>
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input type="checkbox" checked={form.use_logo}
                onChange={e => setForm(f => ({ ...f, use_logo: e.target.checked }))}
                className="w-3.5 h-3.5"
                data-testid="video-use-logo" />
              <span>Burn Purnabramha logo (top-right)</span>
            </label>

            <Button onClick={generate} disabled={busy || !videoFile}
              className="w-full bg-[#8B0000] hover:bg-[#5C0000] text-white"
              size="lg" data-testid="video-generate-btn">
              {busy
                ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {progress > 0 && progress < 100 ? `Uploading ${progress}%…` : 'Branding video…'}</>
                : <><Film className="w-4 h-4 mr-2" />Brand Video</>}
            </Button>
            {busy && progress > 0 && progress < 100 && (
              <div className="h-2 w-full bg-amber-100 rounded-full overflow-hidden">
                <div className="h-full bg-[#8B0000] transition-all" style={{ width: `${progress}%` }} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Preview */}
        <Card className="lg:col-span-3" data-testid="video-preview-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Preview</CardTitle>
            <CardDescription>Original on top, branded version below after processing.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {videoPreviewUrl && !result && (
              <div>
                <p className="text-[10px] uppercase font-semibold text-muted-foreground mb-1">Original</p>
                <video src={videoPreviewUrl} controls className="w-full rounded-lg border" />
              </div>
            )}
            {result && previewUrl && (
              <div>
                <p className="text-[10px] uppercase font-semibold text-emerald-700 mb-1">
                  Branded · {result.size_kb} KB · {result.duration_s}s
                </p>
                <video src={previewUrl} controls className="w-full rounded-lg border-2 border-amber-300 shadow-lg"
                  data-testid="video-branded-preview" />
                <div className="flex gap-2 mt-3 flex-wrap">
                  <Button size="sm" className="bg-[#8B0000] hover:bg-[#5C0000] text-white"
                    onClick={() => downloadVideo(result.video_id)} data-testid="video-download">
                    <Download className="w-3.5 h-3.5 mr-1" />Download MP4
                  </Button>
                  <Button size="sm" variant="outline" onClick={shareWhatsapp} data-testid="video-share-wa">
                    <Share2 className="w-3.5 h-3.5 mr-1" />WhatsApp
                  </Button>
                </div>
              </div>
            )}
            {!videoPreviewUrl && !result && (
              <div className="aspect-video rounded-lg bg-gradient-to-br from-amber-50 to-rose-50 border-2 border-dashed border-amber-300 flex items-center justify-center p-6 text-center">
                <div>
                  <Film className="w-12 h-12 text-rose-300 mx-auto mb-2" />
                  <p className="text-sm text-amber-900">Pick a video on the left to begin.</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* History */}
      <Card data-testid="video-history-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><History className="w-4 h-4" />Recent Branded Videos</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">No branded videos yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {history.map(h => (
                <div key={h.video_id} className="rounded-lg border p-2 bg-white text-xs space-y-1" data-testid={`video-history-${h.video_id}`}>
                  <video src={`${API}/api/marketing/videos/asset/${h.video_id}?token=${session?.token}`}
                    controls preload="metadata" className="w-full rounded" />
                  <p className="font-medium truncate">{h.headline || '(no headline)'}</p>
                  <p className="text-muted-foreground">{h.center} · {h.duration_s || '—'}s · {h.size_kb} KB</p>
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" className="h-7 text-[10px] flex-1"
                      onClick={() => downloadVideo(h.video_id)}>
                      <Download className="w-3 h-3 mr-1" />Download
                    </Button>
                    <Badge variant="outline" className="h-7 text-[10px]">{h.download_count || 0} dl</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
