import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, BookOpen, Shield, Users, Calculator, Store } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL || "";

const manuals = [
  {
    role: "Super Admin",
    file: "manual-super-admin.html",
    color: "from-[#7B1E2A] to-[#4a0e18]",
    textColor: "text-[#7B1E2A]",
    bgColor: "bg-[#7B1E2A]/5",
    borderColor: "border-[#7B1E2A]/20",
    icon: Shield,
    description: "Complete system administration guide. Covers all modules: Centers, Managers, Roles, Master Data, Freeze Control, Franchise Management, and more.",
    audience: "Jayanti, Sandeep, IT Admin"
  },
  {
    role: "Center Manager",
    file: "manual-center-manager.html",
    color: "from-[#2D8B55] to-[#1a5535]",
    textColor: "text-[#2D8B55]",
    bgColor: "bg-[#2D8B55]/5",
    borderColor: "border-[#2D8B55]/20",
    icon: Users,
    description: "Day-to-day operations guide. Covers Attendance, Sales Entry, Expense Entry, Employee Management, Salary & Payslips.",
    audience: "All center managers"
  },
  {
    role: "Accountant",
    file: "manual-accountant.html",
    color: "from-[#C06520] to-[#7a3a10]",
    textColor: "text-[#C06520]",
    bgColor: "bg-[#C06520]/5",
    borderColor: "border-[#C06520]/20",
    icon: Calculator,
    description: "Financial operations & reporting guide. Covers Center Accounts, Revenue Share, Commission Upload, MIS Dashboard, Loan Entries, PDF Reports.",
    audience: "Accounts team"
  },
  {
    role: "Franchise Owner",
    file: "manual-franchise-owner.html",
    color: "from-[#6B3FA0] to-[#3a1f60]",
    textColor: "text-[#6B3FA0]",
    bgColor: "bg-[#6B3FA0]/5",
    borderColor: "border-[#6B3FA0]/20",
    icon: Store,
    description: "Franchise performance monitoring guide. Covers Owner Dashboard, Sales Overview, Revenue Share Breakdown, Documents, Exit Process.",
    audience: "All franchise owners"
  }
];

export default function UserManuals() {
  const handleDownload = (file) => {
    const link = document.createElement("a");
    link.href = `/${file}`;
    link.download = file;
    link.click();
  };

  const handleView = (file) => {
    window.open(`/${file}`, "_blank");
  };

  return (
    <div className="space-y-6" data-testid="user-manuals-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">User Manuals</h1>
        <p className="text-sm text-gray-500 mt-1">Download role-based user manuals to share with your team</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {manuals.map((m) => {
          const Icon = m.icon;
          return (
            <Card key={m.role} className={`overflow-hidden border ${m.borderColor}`} data-testid={`manual-card-${m.role.toLowerCase().replace(/\s/g, '-')}`}>
              <div className={`bg-gradient-to-r ${m.color} px-5 py-4 flex items-center gap-3`}>
                <div className="w-10 h-10 rounded-lg bg-white/15 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-white font-bold text-base">{m.role}</h3>
                  <p className="text-white/70 text-xs">User Manual</p>
                </div>
              </div>
              <CardContent className="p-5 space-y-4">
                <p className="text-sm text-gray-600 leading-relaxed">{m.description}</p>
                <div className={`${m.bgColor} rounded-lg px-3 py-2`}>
                  <p className="text-xs font-medium text-gray-500">Target Audience</p>
                  <p className={`text-sm font-semibold ${m.textColor}`}>{m.audience}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleView(m.file)}
                    data-testid={`view-${m.role.toLowerCase().replace(/\s/g, '-')}`}
                  >
                    <BookOpen className="w-4 h-4 mr-1.5" />
                    View
                  </Button>
                  <Button
                    size="sm"
                    className={`flex-1 bg-gradient-to-r ${m.color} hover:opacity-90 text-white`}
                    onClick={() => handleDownload(m.file)}
                    data-testid={`download-${m.role.toLowerCase().replace(/\s/g, '-')}`}
                  >
                    <Download className="w-4 h-4 mr-1.5" />
                    Download
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Complete Manual */}
      <Card className="border-amber-200 bg-amber-50/30">
        <CardContent className="p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-amber-700" />
            </div>
            <div>
              <p className="font-bold text-gray-900 text-sm">Complete User Manual (All Roles)</p>
              <p className="text-xs text-gray-500">The full combined manual covering all roles and modules</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => handleView("user-manual.html")} data-testid="view-complete-manual">
              <BookOpen className="w-4 h-4 mr-1.5" /> View
            </Button>
            <Button size="sm" className="bg-amber-600 hover:bg-amber-700 text-white" onClick={() => handleDownload("user-manual.html")} data-testid="download-complete-manual">
              <Download className="w-4 h-4 mr-1.5" /> Download
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
