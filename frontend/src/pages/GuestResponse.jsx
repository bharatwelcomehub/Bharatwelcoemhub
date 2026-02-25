import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Loader2, 
  Send, 
  MessageCircle, 
  Bot, 
  User,
  MapPin,
  Phone,
  Clock,
  Trash2,
  Building2,
  Copy,
  CheckCircle,
  Sparkles,
  CalendarCheck
} from "lucide-react";

export default function GuestResponse() {
  const { session } = useAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [centerInfo, setCenterInfo] = useState({});
  const [selectedCenter, setSelectedCenter] = useState(session?.center || "");
  const messagesEndRef = useRef(null);
  const [activeTab, setActiveTab] = useState("ai-chat");
  
  // Booking Response Converter state
  const [rawBookingText, setRawBookingText] = useState("");
  const [formattedResponse, setFormattedResponse] = useState("");
  const [bookingLoading, setBookingLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Load center info
  useEffect(() => {
    const loadCenterInfo = async () => {
      try {
        const res = await api.get("/center_info");
        setCenterInfo(res.data.centers || {});
      } catch (e) {
        console.error("Failed to load center info:", e);
      }
    };
    loadCenterInfo();
  }, []);

  // Set default selected center from session
  useEffect(() => {
    if (session?.center && !selectedCenter) {
      setSelectedCenter(session.center);
    }
  }, [session?.center]);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Send message to AI
  const sendMessage = async () => {
    if (!question.trim()) {
      toast.error("Please enter a question");
      return;
    }
    
    if (!selectedCenter) {
      toast.error("Please select a center first");
      return;
    }
    
    const userMessage = question.trim();
    setQuestion("");
    
    // Add user message with center context
    setMessages(prev => [...prev, { 
      role: "user", 
      content: userMessage,
      center: selectedCenter 
    }]);
    
    setLoading(true);
    try {
      const res = await api.post("/guest_ai", {
        token: session.token,
        center: selectedCenter,
        question: userMessage,
        sessionId: sessionId
      });
      
      // Store session ID
      if (res.data.sessionId) {
        setSessionId(res.data.sessionId);
      }
      
      // Add AI response
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: res.data.answer,
        center: selectedCenter
      }]);
      
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to get AI response");
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Sorry, I couldn't process that request. Please try again or contact support." 
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Clear chat
  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
  };

  // Get current center info
  const currentCenterInfo = centerInfo[selectedCenter] || {};

  // Get all centers as array for dropdown
  const centersList = Object.entries(centerInfo).map(([code, info]) => ({
    code,
    ...info
  }));

  // Generate booking response
  const generateBookingResponse = async () => {
    if (!rawBookingText.trim()) {
      toast.error("Please enter booking details");
      return;
    }
    
    if (!selectedCenter) {
      toast.error("Please select a center first");
      return;
    }
    
    setBookingLoading(true);
    setCopied(false);
    try {
      const res = await api.post("/guest/booking-response", {
        token: session.token,
        center: selectedCenter,
        raw_booking_text: rawBookingText
      });
      
      if (res.data.formatted_message) {
        setFormattedResponse(res.data.formatted_message);
        toast.success("Booking response generated!");
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to generate response");
    } finally {
      setBookingLoading(false);
    }
  };

  // Copy to clipboard
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(formattedResponse);
      setCopied(true);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      toast.error("Failed to copy");
    }
  };

  // Clear booking response
  const clearBookingResponse = () => {
    setRawBookingText("");
    setFormattedResponse("");
    setCopied(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-primary" data-testid="guest-response-title">Guest Communication</h1>
        <p className="text-muted-foreground mt-1">
          AI-powered tools for guest queries and booking confirmations
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="ai-chat" className="gap-2" data-testid="tab-ai-chat">
            <Bot className="w-4 h-4" />
            Guest AI Chat
          </TabsTrigger>
          <TabsTrigger value="booking-response" className="gap-2" data-testid="tab-booking-response">
            <CalendarCheck className="w-4 h-4" />
            Booking Response
          </TabsTrigger>
        </TabsList>

        {/* AI Chat Tab */}
        <TabsContent value="ai-chat">
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Chat Panel */}
            <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="border-b flex-shrink-0">
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-primary" />
                  Purnabramha AI Assistant
                </CardTitle>
                <div className="flex items-center gap-2">
                  {/* Center Selector */}
                  <Select 
                    value={selectedCenter} 
                    onValueChange={setSelectedCenter}
                  >
                    <SelectTrigger className="w-[200px]" data-testid="center-selector">
                      <Building2 className="w-4 h-4 mr-2 text-muted-foreground" />
                      <SelectValue placeholder="Select center" />
                    </SelectTrigger>
                    <SelectContent>
                      {centersList.map((center) => (
                        <SelectItem 
                          key={center.code} 
                          value={center.code}
                          data-testid={`center-option-${center.code}`}
                        >
                          <div className="flex items-center gap-2">
                            {center.country === "Australia" ? "🇦🇺" : "🇮🇳"}
                            <span>{center.code}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={clearChat}
                    className="text-muted-foreground"
                    data-testid="clear-chat-btn"
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Clear
                  </Button>
                </div>
              </div>
              {/* Selected center info bar */}
              {selectedCenter && currentCenterInfo.name && (
                <div className="mt-2 p-2 bg-muted/50 rounded-lg flex items-center gap-4 text-sm">
                  <Badge variant="secondary">{selectedCenter}</Badge>
                  <span className="text-muted-foreground">{currentCenterInfo.name}</span>
                  <span className="text-muted-foreground font-mono">{currentCenterInfo.phone}</span>
                </div>
              )}
            </CardHeader>
            
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground">
                  <Bot className="w-16 h-16 mb-4 opacity-30" />
                  <p className="text-lg font-semibold">Namaskar! </p>
                  <p className="text-sm mt-2">
                    Select a center and type a guest question. I'll help you respond professionally.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2 justify-center">
                    {[
                      "What are the timings?",
                      "Do you have parking?",
                      "Is the food vegetarian?",
                      "What's in the thali?"
                    ].map((q, i) => (
                      <Button
                        key={i}
                        variant="outline"
                        size="sm"
                        className="rounded-full"
                        onClick={() => setQuestion(q)}
                        data-testid={`suggested-question-${i}`}
                      >
                        {q}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-primary" />
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {msg.role === "user" && msg.center && (
                        <Badge variant="secondary" className="mb-1 text-xs">
                          {msg.center}
                        </Badge>
                      )}
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    {msg.role === "user" && (
                      <div className="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4 text-secondary" />
                      </div>
                    )}
                  </div>
                ))
              )}
              {loading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                  <div className="bg-muted rounded-2xl px-4 py-3">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </CardContent>
            
            {/* Input */}
            <div className="border-t p-4 flex-shrink-0">
              <div className="flex gap-2">
                <Input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Type guest's question here..."
                  onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage()}
                  disabled={loading}
                  className="flex-1"
                  data-testid="guest-ai-input"
                />
                <Button 
                  onClick={sendMessage} 
                  disabled={loading || !question.trim() || !selectedCenter}
                  data-testid="guest-ai-send"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Center Info Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Selected Center</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedCenter && currentCenterInfo.name ? (
                <>
                  <div>
                    <Badge className="mb-2" data-testid="selected-center-badge">{selectedCenter}</Badge>
                    <h3 className="font-bold">{currentCenterInfo.name}</h3>
                  </div>
                  
                  {currentCenterInfo.address && (
                    <div className="flex gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <span className="text-muted-foreground">{currentCenterInfo.address}</span>
                    </div>
                  )}
                  
                  {currentCenterInfo.phone && (
                    <div className="flex gap-2 text-sm">
                      <Phone className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <span className="font-mono">{currentCenterInfo.phone}</span>
                    </div>
                  )}
                  
                  {currentCenterInfo.timings && (
                    <div className="flex gap-2 text-sm">
                      <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                      <span>{currentCenterInfo.timings}</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground text-sm">
                  Select a center from the dropdown above to see details.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">All Centers</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[300px] overflow-y-auto">
              {centersList.map((center) => (
                <button
                  key={center.code}
                  onClick={() => setSelectedCenter(center.code)}
                  className={`w-full text-left border-b pb-2 last:border-0 hover:bg-muted/50 p-2 rounded transition-colors ${
                    selectedCenter === center.code ? "bg-primary/10 border-primary" : ""
                  }`}
                  data-testid={`center-list-${center.code}`}
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{center.code}</Badge>
                    {center.country === "Australia" && <span className="text-xs"></span>}
                    {center.country === "India" && <span className="text-xs"></span>}
                  </div>
                  <p className="text-sm font-medium mt-1">{center.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{center.phone}</p>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <h4 className="font-bold text-sm mb-2">Tips</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Select the center the guest is asking about</li>
                <li>• Type the guest's exact question</li>
                <li>• AI responds with center-specific context</li>
                <li>• Copy response to share with guest</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
