import { useState, useEffect } from "react";
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
  Download,
  Copy,
  Check,
  Briefcase,
  UserMinus,
  Award,
  Plane,
  Building2,
  Calendar,
  User
} from "lucide-react";

const LETTER_TYPES = [
  { 
    value: "offer", 
    label: "Offer Letter", 
    icon: Briefcase,
    description: "New employee joining offer"
  },
  { 
    value: "exit", 
    label: "Exit Letter", 
    icon: UserMinus,
    description: "Resignation acceptance letter"
  },
  { 
    value: "experience", 
    label: "Experience Letter", 
    icon: Award,
    description: "Work experience certificate"
  },
  { 
    value: "visa", 
    label: "Visa/Immigration Letter", 
    icon: Plane,
    description: "Invitation letter for visa purposes"
  }
];

export default function HRLetters() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  
  // Form state
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [letterType, setLetterType] = useState("");
  const [generatedLetter, setGeneratedLetter] = useState("");
  
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
        const token = localStorage.getItem("token");
        const res = await api.get(`/hr_letter/employees?token=${token}`);
        setEmployees(res.data.employees || []);
      } catch (e) {
        console.error("Failed to load employees:", e);
        if (e.response?.status === 403) {
          toast.error("Only PB-MGT can access HR Letters");
        } else {
          toast.error("Failed to load employees");
        }
      } finally {
        setLoading(false);
      }
    };
    loadEmployees();
  }, []);

  // Get selected employee details
  const selectedEmpDetails = employees.find(e => e.name === selectedEmployee);

  // Generate letter
  const handleGenerate = async () => {
    if (!selectedEmployee || !letterType) {
      toast.error("Please select employee and letter type");
      return;
    }

    setGenerating(true);
    setGeneratedLetter("");

    try {
      const token = localStorage.getItem("token");
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
      setGeneratedLetter(res.data.content);
      toast.success(`${LETTER_TYPES.find(t => t.value === letterType)?.label} generated successfully!`);
    } catch (e) {
      console.error("Failed to generate letter:", e);
      toast.error(e.response?.data?.detail || "Failed to generate letter");
    } finally {
      setGenerating(false);
    }
  };

  // Copy to clipboard
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generatedLetter);
      setCopied(true);
      toast.success("Letter copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      toast.error("Failed to copy");
    }
  };

  // Download as text file
  const downloadLetter = () => {
    const blob = new Blob([generatedLetter], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${letterType}_letter_${selectedEmployee.replace(/\s+/g, "_")}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Letter downloaded!");
  };

  // Reset form
  const resetForm = () => {
    setSelectedEmployee("");
    setLetterType("");
    setGeneratedLetter("");
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2">Loading HR Letters...</span>
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
          Generate professional HR documents using AI
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
            <CardDescription>
              Select employee and letter type, then fill in the required details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Employee Selection */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <User className="w-4 h-4" />
                Select Employee
              </Label>
              <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
                <SelectTrigger data-testid="employee-select">
                  <SelectValue placeholder="Choose an employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((emp) => (
                    <SelectItem key={emp.name} value={emp.name}>
                      {emp.name} - {emp.designation || "N/A"} ({emp.center})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedEmpDetails && (
                <div className="text-sm text-muted-foreground bg-muted p-2 rounded">
                  <p><strong>Designation:</strong> {selectedEmpDetails.designation || "N/A"}</p>
                  <p><strong>Center:</strong> {selectedEmpDetails.center}</p>
                  <p><strong>DOJ:</strong> {selectedEmpDetails.dateOfJoining || "N/A"}</p>
                </div>
              )}
            </div>

            {/* Letter Type Selection */}
            <div className="space-y-2">
              <Label>Letter Type</Label>
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

            {/* Conditional Fields based on Letter Type */}
            {letterType === "offer" && (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  Offer Letter Details
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Joining Date</Label>
                    <Input
                      type="date"
                      value={joiningDate}
                      onChange={(e) => setJoiningDate(e.target.value)}
                      data-testid="joining-date"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Monthly Salary (Rs.)</Label>
                    <Input
                      type="number"
                      placeholder="e.g., 25000"
                      value={salary}
                      onChange={(e) => setSalary(e.target.value)}
                      data-testid="salary-input"
                    />
                  </div>
                </div>
              </div>
            )}

            {letterType === "exit" && (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold flex items-center gap-2">
                  <UserMinus className="w-4 h-4" />
                  Exit Letter Details
                </h4>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Last Working Date</Label>
                    <Input
                      type="date"
                      value={lastWorkingDate}
                      onChange={(e) => setLastWorkingDate(e.target.value)}
                      data-testid="last-working-date"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Reason for Exit (Optional)</Label>
                    <Input
                      placeholder="e.g., Personal reasons, Career growth"
                      value={exitReason}
                      onChange={(e) => setExitReason(e.target.value)}
                      data-testid="exit-reason"
                    />
                  </div>
                </div>
              </div>
            )}

            {letterType === "experience" && (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold flex items-center gap-2">
                  <Award className="w-4 h-4" />
                  Experience Letter Details
                </h4>
                <div className="space-y-2">
                  <Label>Last Working Date</Label>
                  <Input
                    type="date"
                    value={lastWorkingDate}
                    onChange={(e) => setLastWorkingDate(e.target.value)}
                    data-testid="exp-last-date"
                  />
                </div>
              </div>
            )}

            {letterType === "visa" && (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <h4 className="font-semibold flex items-center gap-2">
                  <Plane className="w-4 h-4" />
                  Visa/Immigration Letter Details
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Destination Country *</Label>
                    <Input
                      placeholder="e.g., United States, Australia"
                      value={destinationCountry}
                      onChange={(e) => setDestinationCountry(e.target.value)}
                      data-testid="destination-country"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Visa Number (if available)</Label>
                    <Input
                      placeholder="e.g., B1/B2, Work Visa"
                      value={visaNumber}
                      onChange={(e) => setVisaNumber(e.target.value)}
                      data-testid="visa-number"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Purpose of Travel *</Label>
                  <Select value={travelPurpose} onValueChange={setTravelPurpose}>
                    <SelectTrigger data-testid="travel-purpose">
                      <SelectValue placeholder="Select purpose" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="business_visit">Business Visit / Meetings</SelectItem>
                      <SelectItem value="training">Training / Workshop</SelectItem>
                      <SelectItem value="project_work">Project Work / Assignment</SelectItem>
                      <SelectItem value="conference">Conference / Exhibition</SelectItem>
                      <SelectItem value="client_meeting">Client Meeting</SelectItem>
                      <SelectItem value="branch_setup">Branch Setup / Expansion</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Travel Start Date</Label>
                    <Input
                      type="date"
                      value={travelStartDate}
                      onChange={(e) => setTravelStartDate(e.target.value)}
                      data-testid="travel-start"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Travel End Date</Label>
                    <Input
                      type="date"
                      value={travelEndDate}
                      onChange={(e) => setTravelEndDate(e.target.value)}
                      data-testid="travel-end"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Duration of Stay</Label>
                  <Input
                    placeholder="e.g., 15 days, 2 weeks, 3 months"
                    value={travelDuration}
                    onChange={(e) => setTravelDuration(e.target.value)}
                    data-testid="travel-duration"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Inviting Company/Organization (if any)</Label>
                  <Input
                    placeholder="e.g., ABC Corporation, XYZ Partners"
                    value={invitingCompany}
                    onChange={(e) => setInvitingCompany(e.target.value)}
                    data-testid="inviting-company"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Project/Business Details</Label>
                  <Textarea
                    placeholder="Brief description of the project or business purpose..."
                    value={projectDetails}
                    onChange={(e) => setProjectDetails(e.target.value)}
                    rows={3}
                    data-testid="project-details"
                  />
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-4">
              <Button
                onClick={handleGenerate}
                disabled={!selectedEmployee || !letterType || generating}
                className="flex-1"
                data-testid="generate-letter-btn"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating with AI...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Generate Letter
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={resetForm} data-testid="reset-btn">
                Reset
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Generated Letter Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-secondary" />
                Generated Letter
              </span>
              {generatedLetter && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={copyToClipboard}
                    data-testid="copy-letter-btn"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={downloadLetter}
                    data-testid="download-letter-btn"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </CardTitle>
            {letterType && (
              <Badge variant="secondary">
                {LETTER_TYPES.find(t => t.value === letterType)?.label}
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              {generating ? (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <Loader2 className="w-12 h-12 animate-spin mb-4" />
                  <p>AI is generating your letter...</p>
                  <p className="text-sm mt-2">This may take a few seconds</p>
                </div>
              ) : generatedLetter ? (
                <div className="whitespace-pre-wrap font-mono text-sm bg-muted/30 p-4 rounded-lg border">
                  {generatedLetter}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                  <FileText className="w-16 h-16 mb-4 opacity-30" />
                  <p>Your generated letter will appear here</p>
                  <p className="text-sm mt-2">Select employee and letter type to begin</p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
