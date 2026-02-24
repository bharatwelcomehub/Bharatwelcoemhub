import { useState } from "react";
import { useAuth } from "@/App";
import { api, CENTERS } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Send, CheckCircle, Building2 } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const [center, setCenter] = useState("");
  const [mobile, setMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const handleSendOTP = async () => {
    if (!center || !mobile) {
      toast.error("Please select center and enter mobile number");
      return;
    }
    
    setLoading(true);
    try {
      await api.post("/send_otp", { center, mobile });
      toast.success("OTP sent to your registered email!");
      setStep(2);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (!otp) {
      toast.error("Please enter OTP");
      return;
    }
    
    setLoading(true);
    try {
      const res = await api.post("/verify_otp", { center, mobile, otp });
      toast.success("Login successful!");
      login({
        token: res.data.token,
        center: res.data.center,
        managerName: res.data.managerName,
        mobile: res.data.mobile,
        roles: res.data.roles || {},
      });
    } catch (e) {
      toast.error(e.response?.data?.detail || "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen login-bg relative">
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      
      {/* Content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md animate-fadeIn">
          {/* Logo/Brand */}
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
              Purnabramha
            </h1>
            <p className="text-white/70 mt-2 text-lg">IntraPB Portal</p>
          </div>

          <Card className="glass shadow-2xl border-0">
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl text-primary">Manager Login</CardTitle>
              <CardDescription>
                {step === 1 
                  ? "Enter your center and mobile number to receive OTP" 
                  : "Enter the OTP sent to your registered email"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {step === 1 ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="center" className="text-primary font-semibold">
                      Center
                    </Label>
                    <Select value={center} onValueChange={setCenter}>
                      <SelectTrigger data-testid="center-select" className="h-12">
                        <Building2 className="w-4 h-4 mr-2 text-muted-foreground" />
                        <SelectValue placeholder="Select your center" />
                      </SelectTrigger>
                      <SelectContent>
                        {CENTERS.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.code} - {c.name.split(" - ")[0]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="mobile" className="text-primary font-semibold">
                      Mobile Number
                    </Label>
                    <Input
                      id="mobile"
                      data-testid="mobile-input"
                      type="tel"
                      placeholder="e.g. 9741399190"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                      className="h-12"
                    />
                  </div>

                  <Button
                    data-testid="send-otp-btn"
                    onClick={handleSendOTP}
                    disabled={loading}
                    className="w-full h-12 text-base font-bold"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    ) : (
                      <Send className="w-5 h-5 mr-2" />
                    )}
                    Send OTP
                  </Button>
                </>
              ) : (
                <>
                  <div className="bg-muted rounded-lg p-4 text-center">
                    <p className="text-sm text-muted-foreground">OTP sent to</p>
                    <p className="font-bold text-primary">{center} • {mobile}</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="otp" className="text-primary font-semibold">
                      Enter OTP
                    </Label>
                    <Input
                      id="otp"
                      data-testid="otp-input"
                      type="text"
                      placeholder="6-digit OTP"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                      className="h-12 text-center text-xl tracking-widest font-mono"
                      maxLength={6}
                    />
                    <p className="text-xs text-muted-foreground text-center">
                      OTP is sent to registered manager email. Contact admin if you don't receive it.
                    </p>
                  </div>

                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={() => { setStep(1); setOtp(""); }}
                      className="flex-1 h-12"
                    >
                      Back
                    </Button>
                    <Button
                      data-testid="verify-otp-btn"
                      onClick={handleVerifyOTP}
                      disabled={loading}
                      className="flex-1 h-12 font-bold"
                    >
                      {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      ) : (
                        <CheckCircle className="w-5 h-5 mr-2" />
                      )}
                      Verify & Login
                    </Button>
                  </div>
                </>
              )}

              <div className="pt-4 border-t border-border">
                <p className="text-xs text-center text-muted-foreground">
                  OTP is sent to registered manager email.
                  <br />
                  Contact admin if you don't receive it.
                </p>
              </div>
            </CardContent>
          </Card>

          <p className="text-center text-white/50 text-sm mt-6">
            © {new Date().getFullYear()} Manswini Foods Pvt. Ltd.
          </p>
        </div>
      </div>
    </div>
  );
}
