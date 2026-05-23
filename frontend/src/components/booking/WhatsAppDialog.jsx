/**
 * Shared WhatsApp preview/copy dialog for Tiffin / Catering / Event bookings.
 * Identical UX to the existing Booking Intelligence WhatsApp flow.
 */
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { MessageSquare, Copy, Send, Loader2, ExternalLink } from "lucide-react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

export default function WhatsAppDialog({ open, onOpenChange, kind, row, token, onMarkedSent }) {
  const [message, setMessage] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !row) return;
    setLoading(true);
    fetch(`${API}/api/bookings/ext/${kind}/whatsapp-preview/${row.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) { setMessage(d.message); setPhone(d.phone || ""); }
        else toast.error("Failed to generate WhatsApp message");
      })
      .finally(() => setLoading(false));
  }, [open, kind, row, token]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      toast.success("Message copied to clipboard");
    } catch {
      toast.error("Copy failed — select & copy manually");
    }
  };

  const openWa = () => {
    if (!phone) { toast.error("No phone number on this booking"); return; }
    const clean = phone.replace(/\D/g, "");
    const url = `https://wa.me/${clean}?text=${encodeURIComponent(message)}`;
    window.open(url, "_blank", "noopener");
  };

  const markSent = async () => {
    try {
      const res = await fetch(`${API}/api/bookings/ext/${kind}/whatsapp-mark-sent/${row.id}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        toast.success("Marked as sent");
        onMarkedSent?.();
        onOpenChange(false);
      }
    } catch {
      toast.error("Failed to mark sent");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-green-500" />
            WhatsApp — {row?.customer_name || row?.id}
          </DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : (
          <>
            <div className="text-xs text-muted-foreground">
              To: <span className="font-medium text-foreground">{phone || "—"}</span>
            </div>
            <textarea
              className="w-full min-h-[280px] p-3 text-sm font-mono bg-green-50 dark:bg-green-900/20 border border-green-500/30 rounded whitespace-pre-wrap"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              data-testid="whatsapp-message-textarea"
            />
            <p className="text-xs text-muted-foreground italic">
              Edit if needed, copy or open WhatsApp directly. Marking as sent stamps an audit timestamp.
            </p>
          </>
        )}
        <DialogFooter className="flex-wrap gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
          <Button variant="outline" onClick={copy} data-testid="whatsapp-copy-btn">
            <Copy className="w-4 h-4 mr-2" /> Copy
          </Button>
          <Button variant="outline" onClick={openWa} data-testid="whatsapp-open-btn">
            <ExternalLink className="w-4 h-4 mr-2" /> Open WhatsApp
          </Button>
          <Button onClick={markSent} className="bg-green-600 hover:bg-green-700" data-testid="whatsapp-mark-sent-btn">
            <Send className="w-4 h-4 mr-2" /> Mark Sent
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
