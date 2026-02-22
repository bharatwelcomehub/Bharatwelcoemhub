import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Loader2, 
  Send, 
  MessageCircle, 
  Bot, 
  User,
  MapPin,
  Phone,
  Clock,
  Trash2
} from "lucide-react";

export default function GuestResponse() {
  const { session } = useAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [centerInfo, setCenterInfo] = useState({});
  const messagesEndRef = useRef(null);

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
    
    const userMessage = question.trim();
    setQuestion("");
    
    // Add user message
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    
    setLoading(true);
    try {
      const res = await api.post("/guest_ai", {
        token: session.token,
        center: session.center,
        question: userMessage,
        sessionId: sessionId
      });
      
      // Store session ID
      if (res.data.sessionId) {
        setSessionId(res.data.sessionId);
      }
      
      // Add AI response
      setMessages(prev => [...prev, { role: "assistant", content: res.data.answer }]);
      
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
  const currentCenter = centerInfo[session?.center] || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-primary">Guest Response AI</h1>
        <p className="text-muted-foreground mt-1">
          AI-powered assistant to help answer guest queries
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Chat Panel */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="border-b flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-primary" />
                  Purnabramha AI Assistant
                </CardTitle>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={clearChat}
                  className="text-muted-foreground"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Clear
                </Button>
              </div>
            </CardHeader>
            
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-muted-foreground">
                  <Bot className="w-16 h-16 mb-4 opacity-30" />
                  <p className="text-lg font-semibold">Namaskar! 🙏</p>
                  <p className="text-sm mt-2">
                    Type a guest question and I'll help you respond professionally.
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
                  disabled={loading || !question.trim()}
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
              <CardTitle className="text-lg">Your Center</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Badge className="mb-2">{session?.center}</Badge>
                <h3 className="font-bold">{currentCenter.name || session?.center}</h3>
              </div>
              
              {currentCenter.address && (
                <div className="flex gap-2 text-sm">
                  <MapPin className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                  <span className="text-muted-foreground">{currentCenter.address}</span>
                </div>
              )}
              
              {currentCenter.phone && (
                <div className="flex gap-2 text-sm">
                  <Phone className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="font-mono">{currentCenter.phone}</span>
                </div>
              )}
              
              {currentCenter.timings && (
                <div className="flex gap-2 text-sm">
                  <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span>{currentCenter.timings}</span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">All Centers</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[300px] overflow-y-auto">
              {Object.entries(centerInfo).map(([code, info]) => (
                <div key={code} className="border-b pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{code}</Badge>
                    {info.country === "Australia" && <span className="text-xs">🇦🇺</span>}
                    {info.country === "India" && <span className="text-xs">🇮🇳</span>}
                  </div>
                  <p className="text-sm font-medium mt-1">{info.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{info.phone}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="bg-muted/50">
            <CardContent className="pt-4">
              <h4 className="font-bold text-sm mb-2">💡 Tips</h4>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Type the guest's exact question</li>
                <li>• AI responds with Purnabramha context</li>
                <li>• Copy response to share with guest</li>
                <li>• Use suggested questions for common queries</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
