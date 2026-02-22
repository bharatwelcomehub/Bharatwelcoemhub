import { useState, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileText,
  Loader2,
  Copy,
  Check,
  Briefcase,
  UserMinus,
  Award,
  Plane,
  Building2,
  User,
  Search,
  MapPin
} from "lucide-react";

const LETTER_TYPES = [
  { value: "offer", label: "Offer Letter", icon: Briefcase, description: "New employee joining offer" },
  { value: "exit", label: "Exit Letter", icon: UserMinus, description: "Resignation acceptance" },
  { value: "experience", label: "Experience Letter", icon: Award, description: "Work experience certificate" },
  { value: "visa", label: "Visa Letter", icon: Plane, description: "Immigration support letter" }
];

export default function HRLetters() {
  const [allEmployees, setAllEmployees] = useState([]);
  const [centers, setCenters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  
  // Form state
  const [selectedCenter, setSelectedCenter] = useState("");
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [letterType, setLetterType] = useState("");
  const [generatedLetter, setGeneratedLetter] = useState(null);
  
  // Additional fields
  const [joiningDate, setJoiningDate] = useState("");
  const [salary, setSalary] = useState("");
  const [lastWorkingDate, setLastWorkingDate] = useState("");
  const [exitReason, setExitReason] = useState("");
  
  // Visa fields
  const [destinationCountry, setDestinationCountry] = useState("");
  const [visaNumber, setVisaNumber] = useState("");
  const [travelPurpose, setTravelPurpose] = useState("");
  const [travelDuration, setTravelDuration] = useState("");
  const [travelStartDate, setTravelStartDate] = useState("");
  const [travelEndDate, setTravelEndDate] = useState("");
  const [invitingCompany, setInvitingCompany] = useState("");
  const [projectDetails, setProjectDetails] = useState("");

  // Load employees on mount
  useEffect(() => {
    const loadEmployees = async () => {
      try {
        const sessionStr = localStorage.getItem("pb_session_v2");
        if (!sessionStr) {
          toast.error("Please login first");
          setLoading(false);
          return;
        }
        const session = JSON.parse(sessionStr);
        const token = session?.token;
        
        if (!token) {
          toast.error("Invalid session");
          setLoading(false);
          return;
        }
        
        // Load employees and centers in parallel
        const [empRes, centerRes] = await Promise.all([
          api.get(`/hr_letter/employees?token=${token}`),
          api.post("/mgt/centers", { token })
        ]);
        
        setAllEmployees(empRes.data.employees || []);
        
        // Transform centers for dropdown
        const centersFromDb = (centerRes.data.centers || []).map(c => ({
          value: c.code,
          label: `${c.code} - ${c.name?.replace('Purnabramha ', '')}`
        }));
        // Add "ALL" option
        centersFromDb.push({ value: "ALL", label: "All Centers" });
        setCenters(centersFromDb);
      } catch (e) {
        console.error("Failed to load data:", e);
        if (e.response?.status === 403) {
          toast.error("Only PB-MGT can access HR Letters");
        } else {
          toast.error("Failed to load data");
        }
      } finally {
        setLoading(false);
      }
    };
    loadEmployees();
  }, []);

  // Filter employees by center and search
  const filteredEmployees = useMemo(() => {
    let filtered = allEmployees;
    
    // Filter by center
    if (selectedCenter && selectedCenter !== "ALL") {
      filtered = filtered.filter(e => e.center === selectedCenter);
    }
    
    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(e => 
        e.name?.toLowerCase().includes(query) ||
        e.designation?.toLowerCase().includes(query)
      );
    }
    
    return filtered;
  }, [allEmployees, selectedCenter, searchQuery]);

  // Get selected employee details
  const selectedEmpDetails = allEmployees.find(e => e.name === selectedEmployee);

  // Prepopulate fields when employee is selected
  useEffect(() => {
    if (selectedEmpDetails) {
      setJoiningDate(selectedEmpDetails.dateOfJoining || "");
      setSalary(selectedEmpDetails.currentSalary?.toString() || "");
    }
  }, [selectedEmployee, selectedEmpDetails]);

  // Get token helper
  const getToken = () => {
    const sessionStr = localStorage.getItem("pb_session_v2");
    const session = sessionStr ? JSON.parse(sessionStr) : null;
    return session?.token;
  };

  // Generate letter
  const handleGenerate = async () => {
    if (!selectedEmployee || !letterType) {
      toast.error("Please select employee and letter type");
      return;
    }

    setGenerating(true);
    setGeneratedLetter(null);

    try {
      const token = getToken();
      if (!token) {
        toast.error("Session expired");
        setGenerating(false);
        return;
      }
      
      const payload = {
        token,
        employeeName: selectedEmployee,
        letterType,
        joiningDate,
        salary,
        lastWorkingDate,
        exitReason,
        destinationCountry,
        visaNumber,
        travelPurpose,
        travelDuration,
        travelStartDate,
        travelEndDate,
        invitingCompany,
        projectDetails
      };

      const res = await api.post("/hr_letter/generate", payload);
      
      // Parse the response into structured format
      setGeneratedLetter({
        type: letterType,
        employeeName: selectedEmployee,
        content: res.data.content,
        date: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        empDetails: selectedEmpDetails
      });
      
      toast.success(`${LETTER_TYPES.find(t => t.value === letterType)?.label} generated!`);
    } catch (e) {
      console.error("Failed to generate letter:", e);
      toast.error(e.response?.data?.detail || "Failed to generate letter");
    } finally {
      setGenerating(false);
    }
  };

  // Download letter
  const downloadLetter = async (format) => {
    if (!generatedLetter) {
      toast.error("No letter to download");
      return;
    }
    
    try {
      const token = getToken();
      if (!token) {
        toast.error("Session expired");
        return;
      }
      
      const response = await api.post("/hr_letter/download", {
        token,
        content: generatedLetter.content,
        letterType: generatedLetter.type,
        employeeName: generatedLetter.employeeName,
        format
      }, { responseType: 'blob' });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().split('T')[0].replace(/-/g, '');
      a.download = `${generatedLetter.type}_letter_${generatedLetter.employeeName.replace(/\s+/g, "_")}_${today}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success(`Downloaded as ${format.toUpperCase()}`);
    } catch (e) {
      console.error("Download error:", e);
      toast.error("Failed to download");
    }
  };

  // Copy to clipboard
  const copyToClipboard = async () => {
    if (!generatedLetter) return;
    try {
      await navigator.clipboard.writeText(generatedLetter.content);
      setCopied(true);
      toast.success("Copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      toast.error("Failed to copy");
    }
  };

  // Reset form
  const resetForm = () => {
    setSelectedCenter("");
    setSelectedEmployee("");
    setSearchQuery("");
    setLetterType("");
    setGeneratedLetter(null);
    setJoiningDate("");
    setSalary("");
    setLastWorkingDate("");
    setExitReason("");
    setDestinationCountry("");
    setVisaNumber("");
    setTravelPurpose("");
    setTravelDuration("");
    setTravelStartDate("");
    setTravelEndDate("");
    setInvitingCompany("");
    setProjectDetails("");
  };

  // Render letter preview with proper formatting
  const renderLetterPreview = () => {
    if (!generatedLetter) return null;
    
    const { type, employeeName, date, empDetails, content } = generatedLetter;
    const letterTitle = LETTER_TYPES.find(t => t.value === type)?.label?.toUpperCase() || "HR LETTER";
    
    // Parse content into paragraphs
    const paragraphs = content.split('\n').filter(p => p.trim());
    
    return (
      <div className="bg-white border-2 border-gray-200 rounded-lg shadow-lg p-8 min-h-[700px]">
        {/* Letterhead */}
        <div className="text-center border-b-2 border-primary pb-4 mb-6">
          <img 
            src="https://customer-assets.emergentagent.com/job_642d5081-fe67-412f-9b66-6148b69260ec/artifacts/ndlupwdb_pb_logo.png" 
            alt="Purnabramha" 
            className="h-16 mx-auto mb-2"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'block';
            }}
          />
          <h1 className="text-2xl font-bold text-primary hidden">Purnabramha®</h1>
          <h2 className="text-lg font-bold text-gray-800">MANASWINI FOODS PVT. LTD.</h2>
          <p className="text-xs text-gray-500">
            17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102
          </p>
        </div>
        
        {/* Letter Title */}
        <div className="text-center mb-6">
          <h3 className="text-xl font-bold text-gray-800 underline decoration-2 underline-offset-4">
            {letterTitle}
          </h3>
        </div>
        
        {/* Date and Reference */}
        <div className="flex justify-between mb-6 text-sm">
          <div>
            <span className="font-semibold">Date:</span> {date}
          </div>
          <div>
            <span className="font-semibold">Ref:</span> MFPL/HR/{type.toUpperCase()}/{new Date().getFullYear()}
          </div>
        </div>
        
        {/* To Section */}
        <div className="mb-6">
          <p className="font-semibold">To,</p>
          <p className="font-bold">{employeeName}</p>
          {empDetails && (
            <>
              <p>{empDetails.designation || 'Employee'}</p>
              <p>{empDetails.center}</p>
            </>
          )}
        </div>
        
        {/* Subject */}
        <div className="mb-4">
          <p>
            <span className="font-semibold">Subject:</span>{' '}
            {type === 'offer' && 'Offer of Employment'}
            {type === 'exit' && 'Acceptance of Resignation'}
            {type === 'experience' && 'Experience / Service Certificate'}
            {type === 'visa' && 'Employment Verification for Visa Purpose'}
          </p>
        </div>
        
        {/* Body Content */}
        <div className="space-y-3 text-sm leading-relaxed text-justify">
          {paragraphs.map((para, idx) => {
            // Skip if it's just formatting markers
            if (para.startsWith('**MANASWINI') || para.startsWith('*Purnabramha')) return null;
            if (para.startsWith('**Date:') || para.startsWith('Registered Address')) return null;
            if (para.startsWith('CIN:') || para.startsWith('##')) return null;
            
            // Clean up markdown
            let cleanPara = para
              .replace(/\*\*/g, '')
              .replace(/\*/g, '')
              .replace(/##/g, '')
              .trim();
            
            if (!cleanPara) return null;
            
            // Check if it's a bullet point
            if (cleanPara.startsWith('-') || cleanPara.startsWith('•')) {
              return (
                <p key={idx} className="pl-6">
                  • {cleanPara.substring(1).trim()}
                </p>
              );
            }
            
            return <p key={idx}>{cleanPara}</p>;
          })}
        </div>
        
        {/* Signature Section */}
        <div className="mt-10 pt-6">
          <p className="mb-2">Yours sincerely,</p>
          <p className="font-semibold">For MANASWINI FOODS PVT. LTD.</p>
          <div className="mt-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_642d5081-fe67-412f-9b66-6148b69260ec/artifacts/rnk77act_sign.png" 
              alt="Signature" 
              className="h-16"
              onError={(e) => e.target.style.display = 'none'}
            />
          </div>
          <p className="font-bold mt-2">Mr. Sandeep Gadhwal</p>
          <p>Director</p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-primary" data-testid="hr-letters-title">
          HR Letters Generator
        </h1>
        <p className="text-muted-foreground mt-2">
          Generate professional HR documents with company letterhead
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Form Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Generate Letter
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Step 1: Select Center */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                1. Select Center
              </Label>
              <Select value={selectedCenter} onValueChange={(v) => { setSelectedCenter(v); setSelectedEmployee(""); }}>
                <SelectTrigger data-testid="center-select">
                  <SelectValue placeholder="Choose center first" />
                </SelectTrigger>
                <SelectContent>
                  {CENTERS.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Step 2: Search & Select Employee */}
            {selectedCenter && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  2. Search & Select Employee
                </Label>
                
                {/* Search Input */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by name or designation..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                    data-testid="employee-search"
                  />
                </div>
                
                {/* Employee Dropdown */}
                <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
                  <SelectTrigger data-testid="employee-select">
                    <SelectValue placeholder={`Select from ${filteredEmployees.length} employees`} />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredEmployees.map((emp) => (
                      <SelectItem key={emp.name} value={emp.name}>
                        {emp.name} - {emp.designation || "Employee"} ({emp.center})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                {/* Selected Employee Details */}
                {selectedEmpDetails && (
                  <div className="bg-primary/5 border border-primary/20 p-3 rounded-lg">
                    <p className="font-semibold text-primary">{selectedEmpDetails.name}</p>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground mt-1">
                      <p><strong>Center:</strong> {selectedEmpDetails.center}</p>
                      <p><strong>Designation:</strong> {selectedEmpDetails.designation || "N/A"}</p>
                      <p><strong>DOJ:</strong> {selectedEmpDetails.dateOfJoining || "N/A"}</p>
                      <p><strong>Salary:</strong> ₹{selectedEmpDetails.currentSalary?.toLocaleString() || "N/A"}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Letter Type */}
            {selectedEmployee && (
              <div className="space-y-2">
                <Label>3. Select Letter Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {LETTER_TYPES.map((type) => (
                    <Button
                      key={type.value}
                      variant={letterType === type.value ? "default" : "outline"}
                      className="h-auto py-3 flex flex-col items-center gap-1"
                      onClick={() => setLetterType(type.value)}
                      data-testid={`letter-type-${type.value}`}
                    >
                      <type.icon className="w-5 h-5" />
                      <span className="text-xs">{type.label}</span>
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Letter-specific fields */}
            {letterType === "offer" && (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm">Offer Letter Details</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Joining Date</Label>
                    <Input type="date" value={joiningDate} onChange={(e) => setJoiningDate(e.target.value)} />
                  </div>
                  <div>
                    <Label className="text-xs">Monthly Salary (₹)</Label>
                    <Input type="number" value={salary} onChange={(e) => setSalary(e.target.value)} placeholder="25000" />
                  </div>
                </div>
              </div>
            )}

            {letterType === "exit" && (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm">Exit Letter Details</h4>
                <div>
                  <Label className="text-xs">Last Working Date</Label>
                  <Input type="date" value={lastWorkingDate} onChange={(e) => setLastWorkingDate(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">Reason (Optional)</Label>
                  <Input value={exitReason} onChange={(e) => setExitReason(e.target.value)} placeholder="Personal reasons" />
                </div>
              </div>
            )}

            {letterType === "experience" && (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm">Experience Letter Details</h4>
                <div>
                  <Label className="text-xs">Last Working Date</Label>
                  <Input type="date" value={lastWorkingDate} onChange={(e) => setLastWorkingDate(e.target.value)} />
                </div>
              </div>
            )}

            {letterType === "visa" && (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm">Visa Letter Details</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Destination Country *</Label>
                    <Input value={destinationCountry} onChange={(e) => setDestinationCountry(e.target.value)} placeholder="Australia" />
                  </div>
                  <div>
                    <Label className="text-xs">Visa Type</Label>
                    <Input value={visaNumber} onChange={(e) => setVisaNumber(e.target.value)} placeholder="Business Visa" />
                  </div>
                  <div>
                    <Label className="text-xs">Travel Start Date</Label>
                    <Input type="date" value={travelStartDate} onChange={(e) => setTravelStartDate(e.target.value)} />
                  </div>
                  <div>
                    <Label className="text-xs">Travel End Date</Label>
                    <Input type="date" value={travelEndDate} onChange={(e) => setTravelEndDate(e.target.value)} />
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Purpose of Travel</Label>
                  <Select value={travelPurpose} onValueChange={setTravelPurpose}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select purpose" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="business">Business Meeting</SelectItem>
                      <SelectItem value="training">Training / Workshop</SelectItem>
                      <SelectItem value="project">Project Work</SelectItem>
                      <SelectItem value="conference">Conference</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Inviting Company (if any)</Label>
                  <Input value={invitingCompany} onChange={(e) => setInvitingCompany(e.target.value)} placeholder="Company name" />
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleGenerate}
                disabled={!selectedEmployee || !letterType || generating}
                className="flex-1"
                data-testid="generate-letter-btn"
              >
                {generating ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</>
                ) : (
                  <><FileText className="w-4 h-4 mr-2" />Generate Letter</>
                )}
              </Button>
              <Button variant="outline" onClick={resetForm}>Reset</Button>
            </div>
          </CardContent>
        </Card>

        {/* Letter Preview Section */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-secondary" />
                Letter Preview
              </CardTitle>
              {generatedLetter && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={copyToClipboard} title="Copy">
                    {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadLetter('pdf')} className="text-red-600">
                    <FileText className="w-4 h-4 mr-1" />PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => downloadLetter('docx')} className="text-blue-600">
                    <FileText className="w-4 h-4 mr-1" />Word
                  </Button>
                </div>
              )}
            </div>
            {generatedLetter && (
              <Badge variant="secondary" className="w-fit">
                {LETTER_TYPES.find(t => t.value === generatedLetter.type)?.label}
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[700px]">
              {generating ? (
                <div className="flex flex-col items-center justify-center h-64">
                  <Loader2 className="w-12 h-12 animate-spin mb-4 text-primary" />
                  <p className="text-muted-foreground">Generating letter with AI...</p>
                </div>
              ) : generatedLetter ? (
                renderLetterPreview()
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <FileText className="w-16 h-16 mb-4 opacity-30" />
                  <p>Letter preview will appear here</p>
                  <p className="text-sm mt-2">Select center → employee → letter type</p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
