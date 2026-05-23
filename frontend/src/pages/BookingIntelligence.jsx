import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import {
  CalendarDays,
  Plus,
  Search,
  Edit,
  Trash2,
  Phone,
  Users,
  Clock,
  Gift,
  MessageSquare,
  Send,
  Eye,
  RefreshCw,
  Loader2,
  PartyPopper,
  Cake,
  Heart,
  User,
  Building2,
  TrendingUp,
  CheckCircle2,
  XCircle,
  AlertCircle,
  History,
  Bell,
  ChefHat,
  Download,
  Armchair
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

// Status colors for badges
const statusColors = {
  Enquiry: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  Confirmed: "bg-green-500/20 text-green-400 border-green-500/30",
  Visited: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Cancelled: "bg-red-500/20 text-red-400 border-red-500/30",
  "No Show": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Repeat Visit": "bg-purple-500/20 text-purple-400 border-purple-500/30",
  "Converted to Catering": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  "Lost Lead": "bg-gray-500/20 text-gray-400 border-gray-500/30"
};

const celebrationIcons = {
  Birthday: Cake,
  Anniversary: Heart,
  "Just Get-together": Users,
  "Kids Party": PartyPopper,
  "Office Team": Building2,
  Family: Users,
  "Baby Shower / Godbharai": Gift,
  Kitty: Users,
  "Womens Meet": Users,
  Engagement: Heart,
  Wedding: Heart,
  "Corporate Event": Building2,
  Other: Gift,
  None: Clock
};

export default function BookingIntelligence() {
  const { session } = useAuth();
  const token = session?.token;
  const isSuperAdmin = session?.is_super_admin === true;
  const isAdmin = session?.is_admin === true;
  const userCenter = session?.center || "";

  // Constants from backend
  const [constants, setConstants] = useState({
    time_slots: [],
    guest_types: [],
    celebration_types: [],
    menu_status: [],
    booking_sources: [],
    booking_status: [],
    catering_status: [],
    center_contacts: {}
  });

  // State
  const [activeTab, setActiveTab] = useState("bookings");
  const [loading, setLoading] = useState(false);
  const [bookings, setBookings] = useState([]);
  const [stats, setStats] = useState(null);
  const [reminders, setReminders] = useState({ birthdays: [], anniversaries: [], kids_birthdays: [] });
  const [followups, setFollowups] = useState([]);
  
  // Filters
  const [filters, setFilters] = useState({
    center: isSuperAdmin || isAdmin ? "all" : userCenter,
    status: "all",
    celebration_type: "all",
    date_from: new Date().toISOString().split("T")[0],
    date_to: new Date().toISOString().split("T")[0],
    search: "",
    period: "today"
  });

  // Dialogs
  const [showBookingDialog, setShowBookingDialog] = useState(false);
  const [showGuestLookup, setShowGuestLookup] = useState(false);
  const [showWhatsAppPreview, setShowWhatsAppPreview] = useState(false);
  const [editingBooking, setEditingBooking] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [whatsAppMessage, setWhatsAppMessage] = useState("");
  const [whatsAppType, setWhatsAppType] = useState("confirmation");

  // Guest lookup
  const [lookupPhone, setLookupPhone] = useState("");
  const [guestInfo, setGuestInfo] = useState(null);
  const [lookingUp, setLookingUp] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    guest_name: "",
    phone: "",
    alternate_phone: "",
    email: "",
    time_slot: "",
    num_guests: 2,
    guest_type: "New Entry",
    celebration_type: "None",
    dob: "",
    anniversary_date: "",
    kids_birthday: "",
    family_notes: "",
    preferences: "",
    menu_decided: "No",
    menu_details: "",
    is_catering: false,
    catering_details: "",
    catering_event_date: "",
    catering_guests: "",
    catering_location: "",
    catering_budget: "",
    catering_menu: "",
    occasion_notes: "",
    special_request: "",
    booking_source: "Phone Call",
    status: "Enquiry",
    remarks: "",
    follow_up_required: false,
    follow_up_date: "",
    follow_up_remark: "",
    table_allotted: ""
  });

  // Centers list
  const [centers, setCenters] = useState([]);

  // Load constants on mount
  useEffect(() => {
    fetchConstants();
    fetchCenters();
  }, []);

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === "bookings") {
      fetchBookings();
    } else if (activeTab === "dashboard") {
      fetchStats();
    } else if (activeTab === "reminders") {
      fetchReminders();
      fetchFollowups();
    }
  }, [activeTab, filters, token]);

  const fetchConstants = async () => {
    try {
      const res = await fetch(`${API}/api/bookings/constants`);
      if (res.ok) {
        const data = await res.json();
        setConstants(data);
      }
    } catch (err) {
      console.error("Error fetching constants:", err);
    }
  };

  const fetchCenters = async () => {
    try {
      const res = await fetch(`${API}/api/sales/centers-list`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (res.ok) {
        const data = await res.json();
        setCenters(data.centers || []);
      }
    } catch (err) {
      console.error("Error fetching centers:", err);
    }
  };

  const fetchBookings = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/bookings/list`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          ...filters
        })
      });
      if (res.ok) {
        const data = await res.json();
        setBookings(data.bookings || []);
      }
    } catch (err) {
      toast.error("Failed to fetch bookings");
    } finally {
      setLoading(false);
    }
  }, [token, filters]);

  const fetchStats = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/bookings/dashboard/stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          period: filters.period,
          center: filters.center
        })
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      toast.error("Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  }, [token, filters.period, filters.center]);

  const fetchReminders = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/bookings/reminders/upcoming`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token })
      });
      if (res.ok) {
        const data = await res.json();
        setReminders(data);
      }
    } catch (err) {
      console.error("Error fetching reminders:", err);
    }
  }, [token]);

  const fetchFollowups = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/bookings/followups/today`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token })
      });
      if (res.ok) {
        const data = await res.json();
        setFollowups(data.followups || []);
      }
    } catch (err) {
      console.error("Error fetching followups:", err);
    }
  }, [token]);

  const handleGuestLookup = async () => {
    if (!lookupPhone || lookupPhone.length < 10) {
      toast.error("Please enter a valid phone number");
      return;
    }
    setLookingUp(true);
    try {
      const res = await fetch(`${API}/api/bookings/guest-lookup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, phone: lookupPhone })
      });
      if (res.ok) {
        const data = await res.json();
        setGuestInfo(data);
        if (data.found) {
          toast.success(`Found guest: ${data.guest.name}`);
          // Auto-fill form with guest data
          setFormData(prev => ({
            ...prev,
            phone: lookupPhone,
            guest_name: data.guest.name || "",
            email: data.guest.email || "",
            alternate_phone: data.guest.alternate_phone || "",
            dob: data.guest.date_of_birth || "",
            anniversary_date: data.guest.anniversary_date || "",
            kids_birthday: data.guest.kids_birthday || "",
            family_notes: data.guest.family_notes || "",
            preferences: data.guest.preferences || "",
            guest_type: "Repeat"
          }));
        } else {
          toast.info("New guest - no previous bookings found");
          setFormData(prev => ({
            ...prev,
            phone: lookupPhone,
            guest_type: "New Entry"
          }));
        }
        setShowGuestLookup(false);
      }
    } catch (err) {
      toast.error("Error looking up guest");
    } finally {
      setLookingUp(false);
    }
  };

  const handleDownloadTodayPdf = async () => {
    try {
      const today = new Date().toISOString().split("T")[0];
      const ctr = (isSuperAdmin || isAdmin)
        ? (filters.center && filters.center !== "all" ? filters.center : null)
        : userCenter;
      const res = await fetch(`${API}/api/bookings/ext/today-table-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, center: ctr, date: today })
      });
      if (!res.ok) {
        toast.error("Failed to generate PDF");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `table_bookings_${today}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded");
    } catch (err) {
      toast.error("Error downloading PDF");
    }
  };

  const handleCreateBooking = async () => {
    if (!formData.guest_name || !formData.phone || !formData.time_slot) {
      toast.error("Please fill required fields: Guest Name, Phone, Time Slot");
      return;
    }

    setLoading(true);
    try {
      const endpoint = editingBooking 
        ? `${API}/api/bookings/update/${editingBooking.booking_id}`
        : `${API}/api/bookings/create`;
      
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token,
          center: (isSuperAdmin || isAdmin) ? (formData.center || userCenter) : userCenter,
          ...formData
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(editingBooking ? "Booking updated!" : `Booking created: ${data.booking_id}`);
        setShowBookingDialog(false);
        resetForm();
        fetchBookings();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to save booking");
      }
    } catch (err) {
      toast.error("Error saving booking");
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewWhatsApp = async (booking, type = "confirmation") => {
    setSelectedBooking(booking);
    setWhatsAppType(type);
    try {
      const res = await fetch(`${API}/api/bookings/preview-whatsapp/${booking.booking_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, type })
      });
      if (res.ok) {
        const data = await res.json();
        setWhatsAppMessage(data.message);
        setShowWhatsAppPreview(true);
      }
    } catch (err) {
      toast.error("Error generating message");
    }
  };

  const handleSendWhatsApp = async () => {
    if (!selectedBooking) return;
    try {
      const res = await fetch(`${API}/api/bookings/send-whatsapp/${selectedBooking.booking_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, type: whatsAppType })
      });
      if (res.ok) {
        toast.success("WhatsApp message logged! (Manual sending required)");
        setShowWhatsAppPreview(false);
        fetchBookings();
      }
    } catch (err) {
      toast.error("Error sending message");
    }
  };

  const handleEditBooking = (booking) => {
    setEditingBooking(booking);
    setFormData({
      date: booking.date || "",
      guest_name: booking.guest_name || "",
      phone: booking.phone || "",
      alternate_phone: booking.alternate_phone || "",
      email: "",
      time_slot: booking.time_slot || "",
      num_guests: booking.num_guests || 2,
      guest_type: booking.guest_type || "New Entry",
      celebration_type: booking.celebration_type || "None",
      dob: "",
      anniversary_date: "",
      kids_birthday: "",
      family_notes: "",
      preferences: "",
      menu_decided: booking.menu_decided || "No",
      menu_details: booking.menu_details || "",
      is_catering: booking.is_catering || false,
      catering_details: booking.catering_details || "",
      occasion_notes: booking.occasion_notes || "",
      special_request: booking.special_request || "",
      booking_source: booking.booking_source || "Phone Call",
      status: booking.status || "Enquiry",
      remarks: booking.remarks || "",
      follow_up_required: booking.follow_up_required || false,
      follow_up_date: booking.follow_up_date || "",
      follow_up_remark: booking.follow_up_remark || "",
      center: booking.center || "",
      table_allotted: booking.table_allotted || ""
    });
    setShowBookingDialog(true);
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split("T")[0],
      guest_name: "",
      phone: "",
      alternate_phone: "",
      email: "",
      time_slot: "",
      num_guests: 2,
      guest_type: "New Entry",
      celebration_type: "None",
      dob: "",
      anniversary_date: "",
      kids_birthday: "",
      family_notes: "",
      preferences: "",
      menu_decided: "No",
      menu_details: "",
      is_catering: false,
      catering_details: "",
      catering_event_date: "",
      catering_guests: "",
      catering_location: "",
      catering_budget: "",
      catering_menu: "",
      occasion_notes: "",
      special_request: "",
      booking_source: "Phone Call",
      status: "Enquiry",
      remarks: "",
      follow_up_required: false,
      follow_up_date: "",
      follow_up_remark: "",
      table_allotted: ""
    });
    setEditingBooking(null);
    setGuestInfo(null);
  };

  return (
    <div className="space-y-6" data-testid="booking-intelligence-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <CalendarDays className="w-7 h-7" />
            Booking Intelligence
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage bookings, track guests, and monitor conversions
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleDownloadTodayPdf}
            data-testid="download-today-pdf-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Download Today PDF
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setLookupPhone("");
              setGuestInfo(null);
              setShowGuestLookup(true);
            }}
            data-testid="guest-lookup-btn"
          >
            <Search className="w-4 h-4 mr-2" />
            Guest Lookup
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setShowBookingDialog(true);
            }}
            data-testid="new-booking-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Booking
          </Button>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="bookings" data-testid="tab-bookings">
            <CalendarDays className="w-4 h-4 mr-2" />
            Bookings
          </TabsTrigger>
          <TabsTrigger value="dashboard" data-testid="tab-dashboard">
            <TrendingUp className="w-4 h-4 mr-2" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="reminders" data-testid="tab-reminders">
            <Bell className="w-4 h-4 mr-2" />
            Reminders
          </TabsTrigger>
        </TabsList>

        {/* Bookings Tab */}
        <TabsContent value="bookings" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="p-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div>
                  <Label className="text-xs">From</Label>
                  <Input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))}
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">To</Label>
                  <Input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))}
                    className="h-9"
                  />
                </div>
                <div>
                  <Label className="text-xs">Status</Label>
                  <Select value={filters.status} onValueChange={(v) => setFilters(f => ({ ...f, status: v }))}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      {constants.booking_status.map(s => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Celebration</Label>
                  <Select value={filters.celebration_type} onValueChange={(v) => setFilters(f => ({ ...f, celebration_type: v }))}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      {constants.celebration_types.map(c => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Search</Label>
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-2 top-2.5 text-muted-foreground" />
                    <Input
                      placeholder="Name/Phone..."
                      value={filters.search}
                      onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
                      className="h-9 pl-8"
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end mt-3">
                <Button variant="outline" size="sm" onClick={fetchBookings}>
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Refresh
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Bookings Table */}
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : bookings.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <CalendarDays className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No bookings found for selected filters</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date/Time</TableHead>
                        <TableHead>Guest</TableHead>
                        <TableHead>Contact</TableHead>
                        <TableHead>Guests</TableHead>
                        <TableHead>Occasion</TableHead>
                        <TableHead>Table</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {bookings.map((booking) => {
                        const CelebIcon = celebrationIcons[booking.celebration_type] || Gift;
                        return (
                          <TableRow key={booking.booking_id} data-testid={`booking-row-${booking.booking_id}`}>
                            <TableCell>
                              <div className="font-medium">{booking.date}</div>
                              <div className="text-xs text-muted-foreground">{booking.time_slot}</div>
                              <div className="text-xs text-blue-400">{booking.center}</div>
                            </TableCell>
                            <TableCell>
                              <div className="font-medium">{booking.guest_name}</div>
                              <Badge variant="outline" className="text-xs">
                                {booking.guest_type}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1 text-sm">
                                <Phone className="w-3 h-3" />
                                {booking.phone}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Users className="w-4 h-4" />
                                {booking.num_guests}
                              </div>
                            </TableCell>
                            <TableCell>
                              {booking.celebration_type !== "None" && (
                                <Badge variant="outline" className="flex items-center gap-1 w-fit">
                                  <CelebIcon className="w-3 h-3" />
                                  {booking.celebration_type}
                                </Badge>
                              )}
                              {booking.is_catering && (
                                <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30 mt-1">
                                  <ChefHat className="w-3 h-3 mr-1" />
                                  Catering
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell>
                              {booking.table_allotted ? (
                                <Badge variant="outline" className="flex items-center gap-1 w-fit">
                                  <Armchair className="w-3 h-3" />
                                  {booking.table_allotted}
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <Badge className={statusColors[booking.status] || "bg-gray-500/20"}>
                                {booking.status}
                              </Badge>
                              {booking.whatsapp_sent && (
                                <MessageSquare className="w-3 h-3 text-green-400 inline ml-1" />
                              )}
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handleEditBooking(booking)}
                                  title="Edit"
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handlePreviewWhatsApp(booking, "confirmation")}
                                  title="WhatsApp"
                                  className="text-green-400"
                                >
                                  <MessageSquare className="w-4 h-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="space-y-4">
          {/* Period Selector */}
          <div className="flex gap-2">
            {["today", "week", "month"].map(period => (
              <Button
                key={period}
                variant={filters.period === period ? "default" : "outline"}
                size="sm"
                onClick={() => setFilters(f => ({ ...f, period }))}
              >
                {period.charAt(0).toUpperCase() + period.slice(1)}
              </Button>
            ))}
          </div>

          {stats && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Total Bookings</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{stats.summary.total_bookings}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {stats.summary.enquiries} enquiries
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Confirmed</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-green-400">{stats.summary.confirmed}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {stats.conversion.enquiry_to_confirmed}% conversion
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Visited</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-emerald-400">{stats.summary.visited}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {stats.conversion.booking_to_visit}% show rate
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">Expected Guests</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-blue-400">{stats.total_guests_expected}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {stats.conversion.repeat_rate}% repeat
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Guest Type & Sources */}
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Guest Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center gap-2">
                        <User className="w-4 h-4 text-blue-400" />
                        New Guests
                      </span>
                      <span className="font-bold">{stats.summary.new_guests}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center gap-2">
                        <RefreshCw className="w-4 h-4 text-green-400" />
                        Repeat Guests
                      </span>
                      <span className="font-bold">{stats.summary.repeat_guests}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm flex items-center gap-2">
                        <ChefHat className="w-4 h-4 text-cyan-400" />
                        Catering Leads
                      </span>
                      <span className="font-bold">{stats.summary.catering_leads}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Booking Sources</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {Object.entries(stats.sources || {}).slice(0, 5).map(([source, count]) => (
                      <div key={source} className="flex justify-between items-center">
                        <span className="text-sm">{source}</span>
                        <Badge variant="outline">{count}</Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>

              {/* Celebrations */}
              {Object.keys(stats.celebrations || {}).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Celebrations This Period</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(stats.celebrations).map(([type, count]) => {
                        const Icon = celebrationIcons[type] || Gift;
                        return (
                          <Badge key={type} variant="outline" className="flex items-center gap-1 py-1 px-2">
                            <Icon className="w-3 h-3" />
                            {type}: {count}
                          </Badge>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* Reminders Tab */}
        <TabsContent value="reminders" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Today's Follow-ups */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-orange-400" />
                  Follow-ups Today ({followups.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {followups.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No follow-ups scheduled</p>
                ) : (
                  <div className="space-y-2">
                    {followups.map(f => (
                      <div key={f.booking_id} className="p-2 bg-muted/50 rounded flex justify-between items-center">
                        <div>
                          <div className="font-medium text-sm">{f.guest_name}</div>
                          <div className="text-xs text-muted-foreground">{f.follow_up_remark}</div>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => handleEditBooking(f)}>
                          View
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Upcoming Birthdays */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Cake className="w-4 h-4 text-pink-400" />
                  Upcoming Birthdays
                </CardTitle>
              </CardHeader>
              <CardContent>
                {reminders.birthdays.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No birthdays in next 7 days</p>
                ) : (
                  <div className="space-y-2">
                    {reminders.birthdays.slice(0, 5).map((g, idx) => (
                      <div key={idx} className="p-2 bg-muted/50 rounded flex justify-between items-center">
                        <div>
                          <div className="font-medium text-sm">{g.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {g.days_until === 0 ? "Today!" : `In ${g.days_until} days`}
                          </div>
                        </div>
                        <Button size="sm" variant="outline" className="text-pink-400">
                          <Gift className="w-3 h-3 mr-1" />
                          Greet
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Upcoming Anniversaries */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Heart className="w-4 h-4 text-red-400" />
                  Upcoming Anniversaries
                </CardTitle>
              </CardHeader>
              <CardContent>
                {reminders.anniversaries.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No anniversaries in next 7 days</p>
                ) : (
                  <div className="space-y-2">
                    {reminders.anniversaries.slice(0, 5).map((g, idx) => (
                      <div key={idx} className="p-2 bg-muted/50 rounded flex justify-between items-center">
                        <div>
                          <div className="font-medium text-sm">{g.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {g.days_until === 0 ? "Today!" : `In ${g.days_until} days`}
                          </div>
                        </div>
                        <Button size="sm" variant="outline" className="text-red-400">
                          <Heart className="w-3 h-3 mr-1" />
                          Greet
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* New/Edit Booking Dialog */}
      <Dialog open={showBookingDialog} onOpenChange={setShowBookingDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingBooking ? "Edit Booking" : "New Booking"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Quick Guest Lookup */}
            <div className="flex gap-2">
              <Input
                placeholder="Enter phone to lookup guest..."
                value={formData.phone}
                onChange={(e) => setFormData(f => ({ ...f, phone: e.target.value }))}
              />
              <Button
                variant="outline"
                onClick={() => {
                  setLookupPhone(formData.phone);
                  handleGuestLookup();
                }}
                disabled={!formData.phone}
              >
                <Search className="w-4 h-4" />
              </Button>
            </div>

            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData(f => ({ ...f, date: e.target.value }))}
                />
              </div>
              <div>
                <Label>Time Slot *</Label>
                <Select value={formData.time_slot} onValueChange={(v) => setFormData(f => ({ ...f, time_slot: v }))}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select time..." />
                  </SelectTrigger>
                  <SelectContent>
                    {constants.time_slots.map(t => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Guest Name *</Label>
                <Input
                  value={formData.guest_name}
                  onChange={(e) => setFormData(f => ({ ...f, guest_name: e.target.value }))}
                  placeholder="Full name"
                />
              </div>
              <div>
                <Label>Number of Guests</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.num_guests}
                  onChange={(e) => setFormData(f => ({ ...f, num_guests: parseInt(e.target.value) || 1 }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Celebration Type</Label>
                <Select value={formData.celebration_type} onValueChange={(v) => setFormData(f => ({ ...f, celebration_type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {constants.celebration_types.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Source</Label>
                <Select value={formData.booking_source} onValueChange={(v) => setFormData(f => ({ ...f, booking_source: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {constants.booking_sources.map(s => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Status</Label>
                <Select value={formData.status} onValueChange={(v) => setFormData(f => ({ ...f, status: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {constants.booking_status.map(s => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Menu Decided?</Label>
                <Select value={formData.menu_decided} onValueChange={(v) => setFormData(f => ({ ...f, menu_decided: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {constants.menu_status.map(m => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>Table Allotted</Label>
              <Input
                value={formData.table_allotted}
                onChange={(e) => setFormData(f => ({ ...f, table_allotted: e.target.value }))}
                placeholder="e.g. T1, Window-2, Private Cabin"
                data-testid="table-allotted-input"
              />
            </div>

            {/* Guest Info Section */}
            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium mb-3">Guest Information (for CRM)</h4>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">Date of Birth</Label>
                  <Input
                    type="date"
                    value={formData.dob}
                    onChange={(e) => setFormData(f => ({ ...f, dob: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Anniversary</Label>
                  <Input
                    type="date"
                    value={formData.anniversary_date}
                    onChange={(e) => setFormData(f => ({ ...f, anniversary_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Kid's Birthday</Label>
                  <Input
                    type="date"
                    value={formData.kids_birthday}
                    onChange={(e) => setFormData(f => ({ ...f, kids_birthday: e.target.value }))}
                  />
                </div>
              </div>
            </div>

            {/* Catering Toggle */}
            <div className="flex items-center gap-2 border-t pt-4">
              <Switch
                checked={formData.is_catering}
                onCheckedChange={(v) => setFormData(f => ({ ...f, is_catering: v }))}
              />
              <Label>This is a catering enquiry</Label>
            </div>

            {formData.is_catering && (
              <div className="grid grid-cols-2 gap-3 p-3 bg-muted/50 rounded">
                <div>
                  <Label className="text-xs">Event Date</Label>
                  <Input
                    type="date"
                    value={formData.catering_event_date}
                    onChange={(e) => setFormData(f => ({ ...f, catering_event_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Approx Guests</Label>
                  <Input
                    type="number"
                    value={formData.catering_guests}
                    onChange={(e) => setFormData(f => ({ ...f, catering_guests: e.target.value }))}
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Location</Label>
                  <Input
                    value={formData.catering_location}
                    onChange={(e) => setFormData(f => ({ ...f, catering_location: e.target.value }))}
                    placeholder="Event venue"
                  />
                </div>
              </div>
            )}

            {/* Notes */}
            <div>
              <Label>Special Requests / Notes</Label>
              <Textarea
                value={formData.special_request}
                onChange={(e) => setFormData(f => ({ ...f, special_request: e.target.value }))}
                placeholder="Any special requests or notes..."
                rows={2}
              />
            </div>

            {/* Follow-up */}
            <div className="flex items-center gap-2">
              <Checkbox
                checked={formData.follow_up_required}
                onCheckedChange={(v) => setFormData(f => ({ ...f, follow_up_required: v }))}
              />
              <Label>Follow-up Required</Label>
            </div>

            {formData.follow_up_required && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Follow-up Date</Label>
                  <Input
                    type="date"
                    value={formData.follow_up_date}
                    onChange={(e) => setFormData(f => ({ ...f, follow_up_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">Follow-up Note</Label>
                  <Input
                    value={formData.follow_up_remark}
                    onChange={(e) => setFormData(f => ({ ...f, follow_up_remark: e.target.value }))}
                    placeholder="What to follow up on..."
                  />
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowBookingDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateBooking} disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {editingBooking ? "Update" : "Create Booking"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Guest Lookup Dialog */}
      <Dialog open={showGuestLookup} onOpenChange={setShowGuestLookup}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Guest Lookup</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Enter phone number..."
                value={lookupPhone}
                onChange={(e) => setLookupPhone(e.target.value)}
              />
              <Button onClick={handleGuestLookup} disabled={lookingUp}>
                {lookingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              </Button>
            </div>
            
            {guestInfo && (
              <div className="p-4 bg-muted/50 rounded space-y-3">
                {guestInfo.found ? (
                  <>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-green-400" />
                      <span className="font-medium">{guestInfo.guest.name}</span>
                      <Badge variant="outline">Repeat Guest</Badge>
                    </div>
                    <div className="text-sm space-y-1">
                      <p>Total Bookings: {guestInfo.stats.total_bookings}</p>
                      <p>Total Visits: {guestInfo.stats.total_visits}</p>
                      <p>Last Center: {guestInfo.guest.last_center}</p>
                    </div>
                    {guestInfo.history.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium mb-2">Recent Bookings:</p>
                        {guestInfo.history.slice(0, 3).map(b => (
                          <div key={b.booking_id} className="text-xs p-2 bg-background rounded mb-1">
                            {b.date} - {b.center} - {b.status}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    <User className="w-5 h-5 text-blue-400" />
                    <span>New Guest - No previous bookings</span>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGuestLookup(false)}>
              Close
            </Button>
            {guestInfo && (
              <Button onClick={() => {
                setShowGuestLookup(false);
                setShowBookingDialog(true);
              }}>
                Create Booking
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* WhatsApp Preview Dialog */}
      <Dialog open={showWhatsAppPreview} onOpenChange={setShowWhatsAppPreview}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-green-400" />
              WhatsApp Message Preview
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex gap-2">
              {["confirmation", "reminder", "thankyou"].map(type => (
                <Button
                  key={type}
                  variant={whatsAppType === type ? "default" : "outline"}
                  size="sm"
                  onClick={() => selectedBooking && handlePreviewWhatsApp(selectedBooking, type)}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Button>
              ))}
            </div>
            <div className="p-4 bg-green-900/20 rounded-lg border border-green-500/30 whitespace-pre-wrap text-sm">
              {whatsAppMessage}
            </div>
            <p className="text-xs text-muted-foreground">
              Note: WhatsApp Business API integration pending. Message will be logged for manual sending.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWhatsAppPreview(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendWhatsApp} className="bg-green-600 hover:bg-green-700">
              <Send className="w-4 h-4 mr-2" />
              Log & Copy Message
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
