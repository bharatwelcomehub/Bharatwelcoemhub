import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Save, X, Tags, Search } from "lucide-react";
import { api } from "@/lib/api";

export default function ExpenseHeads() {
  const { session } = useAuth();
  const [loading, setLoading] = useState(false);
  const [expenseTypes, setExpenseTypes] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    is_active: true
  });

  // Fetch expense types
  const fetchExpenseTypes = async () => {
    setLoading(true);
    try {
      const res = await api.get("/sales/expense-heads");
      if (res.data.expense_heads) {
        setExpenseTypes(res.data.expense_heads);
      }
    } catch (err) {
      // Fallback to default types if endpoint doesn't exist yet
      const defaultTypes = [
        { _id: "1", name: "GROCERY", description: "Daily grocery items", is_active: true },
        { _id: "2", name: "DAIRY PRODUCTS", description: "Milk, curd, paneer etc.", is_active: true },
        { _id: "3", name: "FRUITS & VEGETABLE", description: "Fresh fruits and vegetables", is_active: true },
        { _id: "4", name: "WATER CAN / BOTTLE", description: "Drinking water supplies", is_active: true },
        { _id: "5", name: "CYLINDER", description: "Gas cylinders", is_active: true },
        { _id: "6", name: "PAV", description: "Bread/Pav supplies", is_active: true },
        { _id: "7", name: "PACKAGING MATERIAL", description: "Takeaway containers, bags", is_active: true },
        { _id: "8", name: "CELEBRATION EXPENSES", description: "Festival and event expenses", is_active: true },
        { _id: "9", name: "MEDIA & ADVERTISEMENT", description: "Marketing and ads", is_active: true },
        { _id: "10", name: "RESTAURANT GENERAL EXPENSES", description: "Miscellaneous restaurant expenses", is_active: true },
        { _id: "11", name: "REPAIR & MAINTENANCE", description: "Equipment and property repairs", is_active: true },
        { _id: "12", name: "SALARY", description: "Staff salary payments", is_active: true },
        { _id: "13", name: "ADVANCE", description: "Salary advances to staff", is_active: true },
        { _id: "14", name: "RENT", description: "Shop/property rent", is_active: true },
        { _id: "15", name: "ELECTRICITY", description: "Electricity bills", is_active: true },
        { _id: "16", name: "STATIONARY & PACKAGING", description: "Office supplies and packaging", is_active: true },
        { _id: "17", name: "OVER TIME", description: "Staff overtime payments", is_active: true },
        { _id: "18", name: "STAFF ROOM RENT", description: "Staff accommodation rent", is_active: true },
        { _id: "19", name: "EMI / LOAN INSTALMENT", description: "Loan EMI payments", is_active: true },
        { _id: "20", name: "RENT PAID SHOP", description: "Main shop rent", is_active: true },
      ];
      setExpenseTypes(defaultTypes);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExpenseTypes();
  }, []);

  // Filter expense types
  const filteredTypes = expenseTypes.filter(type => 
    type.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    type.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Handle form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error("Expense head name is required");
      return;
    }
    
    setLoading(true);
    try {
      if (editingId) {
        // Use URL encoding for name with special characters
        await api.put(`/sales/expense-heads/${encodeURIComponent(editingId)}?token=${session?.token}`, formData);
        toast.success("Expense head updated successfully");
      } else {
        await api.post(`/sales/expense-heads?token=${session?.token}`, formData);
        toast.success("Expense head created successfully");
      }
      
      // Reset form and refresh
      setShowForm(false);
      setEditingId(null);
      setFormData({ name: "", description: "", is_active: true });
      fetchExpenseTypes();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save expense head");
    } finally {
      setLoading(false);
    }
  };

  // Handle edit
  const handleEdit = (type) => {
    setEditingId(type.name); // Use name as identifier (matches backend PUT endpoint)
    setFormData({
      name: type.name,
      description: type.description || "",
      is_active: type.is_active !== false
    });
    setShowForm(true);
  };

  // Handle delete
  const handleDelete = async (name) => {
    if (!confirm("Are you sure you want to delete this expense head?")) return;
    
    setLoading(true);
    try {
      // Backend uses name as the path parameter
      await api.delete(`/sales/expense-heads/${encodeURIComponent(name)}?token=${session?.token}`);
      toast.success("Expense head deleted");
      fetchExpenseTypes();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete expense head");
    } finally {
      setLoading(false);
    }
  };

  // Cancel form
  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setFormData({ name: "", description: "", is_active: true });
  };

  return (
    <div className="space-y-6" data-testid="expense-heads-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Expense Heads Master</h1>
          <p className="text-muted-foreground">Manage expense categories for all centers</p>
        </div>
        
        <Button onClick={() => setShowForm(true)} className="gap-2" data-testid="add-expense-head-btn">
          <Plus className="w-4 h-4" /> Add Expense Head
        </Button>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-lg">
              {editingId ? "Edit Expense Head" : "Add New Expense Head"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Expense Head Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value.toUpperCase() })}
                    placeholder="e.g., GROCERY"
                    data-testid="expense-head-name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Brief description"
                    data-testid="expense-head-description"
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4"
                />
                <Label htmlFor="is_active" className="cursor-pointer">Active</Label>
              </div>
              
              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={handleCancel}>
                  <X className="w-4 h-4 mr-2" /> Cancel
                </Button>
                <Button type="submit" disabled={loading} data-testid="save-expense-head-btn">
                  <Save className="w-4 h-4 mr-2" /> {editingId ? "Update" : "Create"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search expense heads..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
          data-testid="search-expense-heads"
        />
      </div>

      {/* Expense Heads List */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Tags className="w-5 h-5 text-primary" />
            Expense Categories ({filteredTypes.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">#</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Name</th>
                  <th className="text-left py-3 px-2 font-medium text-muted-foreground">Description</th>
                  <th className="text-center py-3 px-2 font-medium text-muted-foreground">Status</th>
                  <th className="text-right py-3 px-2 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTypes.map((type, idx) => (
                  <tr key={type._id || idx} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-3 px-2 text-muted-foreground">{idx + 1}</td>
                    <td className="py-3 px-2 font-medium">{type.name}</td>
                    <td className="py-3 px-2 text-muted-foreground">{type.description || "-"}</td>
                    <td className="py-3 px-2 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        type.is_active !== false 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {type.is_active !== false ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(type)}
                          className="h-8 w-8 p-0"
                          data-testid={`edit-expense-head-${idx}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(type.name)}
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                          data-testid={`delete-expense-head-${idx}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredTypes.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">
                      No expense heads found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
