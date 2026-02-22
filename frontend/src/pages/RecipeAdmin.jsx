import { useState, useEffect } from "react";
import { useAuth } from "@/App";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { 
  ChefHat, 
  Plus, 
  Pencil, 
  Trash2, 
  Search,
  Save,
  X,
  Loader2,
  AlertTriangle,
  Image as ImageIcon,
  Upload,
  UtensilsCrossed,
  Coffee,
  Baby,
  Soup,
  Wheat,
  Cookie,
  Salad,
  GlassWater
} from "lucide-react";

const CATEGORIES = [
  { value: "ALL", label: "All Recipes", icon: ChefHat },
  { value: "SNACKS", label: "Snacks", icon: UtensilsCrossed },
  { value: "DRINKS", label: "Drinks", icon: Coffee },
  { value: "BALGOPAL", label: "Balgopal", icon: Baby },
  { value: "MAINS", label: "Mains", icon: Soup },
  { value: "CURRIES", label: "Curries", icon: Soup },
  { value: "RICE", label: "Rice", icon: Wheat },
  { value: "CHAPATI", label: "Chapati", icon: Wheat },
  { value: "SWEETS", label: "Sweets", icon: Cookie },
  { value: "CHUTNEYS", label: "Chutneys", icon: GlassWater },
  { value: "SALADS", label: "Salads", icon: Salad },
];

export default function RecipeAdmin() {
  const { session } = useAuth();
  const [recipes, setRecipes] = useState({});
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("ALL");
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    key: "",
    name: "",
    display: "",
    ingredients: "",
    method: "",
    category: "MAINS",
    image: ""
  });

  // Load recipes
  useEffect(() => {
    loadRecipes();
  }, []);

  const loadRecipes = async () => {
    setLoading(true);
    try {
      const res = await api.get("/recipes");
      setRecipes(res.data.recipes || {});
      setCategories(res.data.categories || CATEGORIES.map(c => c.value).filter(c => c !== "ALL"));
    } catch (e) {
      toast.error("Failed to load recipes");
    } finally {
      setLoading(false);
    }
  };

  // Filter recipes by category and search
  const filteredRecipes = Object.entries(recipes).filter(([key, recipe]) => {
    const matchesSearch = 
      recipe.display?.toLowerCase().includes(search.toLowerCase()) ||
      recipe.name?.toLowerCase().includes(search.toLowerCase()) ||
      key.toLowerCase().includes(search.toLowerCase());
    
    const matchesCategory = 
      activeCategory === "ALL" || 
      recipe.category?.toUpperCase() === activeCategory;
    
    return matchesSearch && matchesCategory;
  });

  // Get count by category
  const getCategoryCount = (cat) => {
    if (cat === "ALL") return Object.keys(recipes).length;
    return Object.values(recipes).filter(r => r.category?.toUpperCase() === cat).length;
  };

  // Select recipe for viewing/editing
  const selectRecipe = (key, recipe) => {
    setSelectedRecipe({ key, ...recipe });
    setFormData({
      key: key,
      name: recipe.name || "",
      display: recipe.display || "",
      ingredients: (recipe.ingredients || []).join("\n"),
      method: (recipe.method || []).join("\n"),
      category: recipe.category?.toUpperCase() || "MAINS",
      image: recipe.image || ""
    });
    setIsEditing(false);
    setIsCreating(false);
  };

  // Start creating new recipe
  const startCreate = () => {
    setSelectedRecipe(null);
    setFormData({
      key: "",
      name: "",
      display: "",
      ingredients: "",
      method: "",
      category: activeCategory === "ALL" ? "MAINS" : activeCategory,
      image: ""
    });
    setIsCreating(true);
    setIsEditing(false);
  };

  // Start editing
  const startEdit = () => {
    setIsEditing(true);
    setIsCreating(false);
  };

  // Cancel editing
  const cancelEdit = () => {
    if (selectedRecipe) {
      setFormData({
        key: selectedRecipe.key,
        name: selectedRecipe.name || "",
        display: selectedRecipe.display || "",
        ingredients: (selectedRecipe.ingredients || []).join("\n"),
        method: (selectedRecipe.method || []).join("\n"),
        category: selectedRecipe.category?.toUpperCase() || "MAINS",
        image: selectedRecipe.image || ""
      });
    }
    setIsEditing(false);
    setIsCreating(false);
  };

  // Save recipe (create or update)
  const saveRecipe = async () => {
    if (!formData.key.trim() || !formData.display.trim()) {
      toast.error("Recipe key and name are required");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        key: formData.key.toLowerCase().replace(/\s+/g, "_"),
        name: formData.name.trim() || formData.display.trim(),
        display: formData.display.trim(),
        ingredients: formData.ingredients.split("\n").filter(i => i.trim()),
        method: formData.method.split("\n").filter(m => m.trim()),
        category: formData.category.toUpperCase(),
        image: formData.image || ""
      };

      if (isCreating) {
        await api.post(`/recipes?token=${session.token}`, payload);
        toast.success(`Recipe "${payload.display}" created!`);
      } else {
        await api.put(`/recipes/${selectedRecipe.key}?token=${session.token}`, payload);
        toast.success(`Recipe "${payload.display}" updated!`);
      }

      await loadRecipes();
      setIsEditing(false);
      setIsCreating(false);
      
      if (isCreating) {
        setSelectedRecipe(null);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save recipe");
    } finally {
      setSaving(false);
    }
  };

  // Delete recipe
  const confirmDelete = async () => {
    if (!deleteDialog) return;
    
    setSaving(true);
    try {
      await api.delete(`/recipes/${deleteDialog}?token=${session.token}`);
      toast.success("Recipe deleted");
      await loadRecipes();
      setDeleteDialog(null);
      setSelectedRecipe(null);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete recipe");
    } finally {
      setSaving(false);
    }
  };

  // Check if user is MGT
  if (session?.center !== "PB-MGT") {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
            <h2 className="text-xl font-bold mb-2">Access Restricted</h2>
            <p className="text-muted-foreground">
              Only PB-MGT managers can access the Recipe Admin panel.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2">Loading recipes...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-primary" data-testid="recipe-admin-title">
            Recipe Admin
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage Purnabramha recipes • {Object.keys(recipes).length} total recipes
          </p>
        </div>
        <Button onClick={startCreate} data-testid="add-recipe-btn">
          <Plus className="w-4 h-4 mr-2" />
          Add New Recipe
        </Button>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search recipes by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
          data-testid="recipe-search"
        />
      </div>

      {/* Category Tabs */}
      <Tabs value={activeCategory} onValueChange={setActiveCategory} className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-1 bg-muted/50 p-1">
          {CATEGORIES.map(cat => {
            const Icon = cat.icon;
            const count = getCategoryCount(cat.value);
            return (
              <TabsTrigger 
                key={cat.value} 
                value={cat.value}
                className="flex items-center gap-1 px-3 py-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                data-testid={`category-tab-${cat.value}`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{cat.label}</span>
                <Badge variant="secondary" className="ml-1 text-xs px-1.5">
                  {count}
                </Badge>
              </TabsTrigger>
            );
          })}
        </TabsList>

        <div className="grid lg:grid-cols-3 gap-6 mt-4">
          {/* Recipe List */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <ChefHat className="w-5 h-5 text-primary" />
                {activeCategory === "ALL" ? "All Recipes" : `${activeCategory} Recipes`}
                <Badge variant="outline" className="ml-auto">{filteredRecipes.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] pr-4">
                <div className="space-y-2">
                  {filteredRecipes.map(([key, recipe]) => (
                    <button
                      key={key}
                      onClick={() => selectRecipe(key, recipe)}
                      className={`w-full text-left p-3 rounded-lg border transition-all hover:shadow-md ${
                        selectedRecipe?.key === key
                          ? "bg-primary/10 border-primary"
                          : "bg-card hover:bg-muted/50 border-border"
                      }`}
                      data-testid={`recipe-item-${key}`}
                    >
                      <div className="flex items-start gap-3">
                        {recipe.image ? (
                          <img 
                            src={recipe.image} 
                            alt={recipe.name}
                            className="w-12 h-12 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center">
                            <ChefHat className="w-6 h-6 text-muted-foreground" />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-medium truncate">{recipe.display || recipe.name}</span>
                          </div>
                          <Badge variant="outline" className="text-xs mt-1">
                            {recipe.category || "MAINS"}
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            {(recipe.ingredients || []).length} ingredients • {(recipe.method || []).length} steps
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                  {filteredRecipes.length === 0 && (
                    <p className="text-center text-muted-foreground py-8">
                      No recipes found in this category
                    </p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Recipe Editor */}
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">
                  {isCreating ? "Create New Recipe" : selectedRecipe ? selectedRecipe.display || selectedRecipe.name : "Select a Recipe"}
                </CardTitle>
                {selectedRecipe && !isCreating && !isEditing && (
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={startEdit} data-testid="edit-recipe-btn">
                      <Pencil className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button 
                      variant="destructive" 
                      size="sm" 
                      onClick={() => setDeleteDialog(selectedRecipe.key)}
                      data-testid="delete-recipe-btn"
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {(selectedRecipe || isCreating) ? (
                <ScrollArea className="h-[500px] pr-4">
                  <div className="space-y-4">
                    {/* Image Preview/URL */}
                    <div className="space-y-2">
                      <Label className="flex items-center gap-2">
                        <ImageIcon className="w-4 h-4" />
                        Recipe Image
                      </Label>
                      {formData.image && (
                        <div className="relative w-full h-48 rounded-lg overflow-hidden bg-muted">
                          <img 
                            src={formData.image} 
                            alt="Recipe" 
                            className="w-full h-full object-cover"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        </div>
                      )}
                      <Input
                        value={formData.image}
                        onChange={(e) => setFormData(prev => ({ ...prev, image: e.target.value }))}
                        placeholder="https://example.com/image.jpg"
                        disabled={!isEditing && !isCreating}
                        data-testid="recipe-image-input"
                      />
                      <p className="text-xs text-muted-foreground">
                        Enter image URL or leave empty for default icon
                      </p>
                    </div>

                    {/* Recipe Key (only for new recipes) */}
                    {isCreating && (
                      <div className="space-y-2">
                        <Label>Recipe Key (unique identifier)</Label>
                        <Input
                          value={formData.key}
                          onChange={(e) => setFormData(prev => ({ ...prev, key: e.target.value }))}
                          placeholder="e.g., solkadhi, vada_pav"
                          disabled={!isCreating}
                          data-testid="recipe-key-input"
                        />
                        <p className="text-xs text-muted-foreground">
                          Use lowercase, underscores for spaces (e.g., puran_poli)
                        </p>
                      </div>
                    )}

                    {/* Name */}
                    <div className="space-y-2">
                      <Label>Recipe Name</Label>
                      <Input
                        value={formData.name}
                        onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Solkadhi"
                        disabled={!isEditing && !isCreating}
                        data-testid="recipe-name-input"
                      />
                    </div>

                    {/* Display Name */}
                    <div className="space-y-2">
                      <Label>Display Name (with Marathi/Hindi)</Label>
                      <Input
                        value={formData.display}
                        onChange={(e) => setFormData(prev => ({ ...prev, display: e.target.value }))}
                        placeholder="e.g., Solkadhi / सोलकढी"
                        disabled={!isEditing && !isCreating}
                        data-testid="recipe-display-input"
                      />
                    </div>

                    {/* Category */}
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select
                        value={formData.category}
                        onValueChange={(val) => setFormData(prev => ({ ...prev, category: val }))}
                        disabled={!isEditing && !isCreating}
                      >
                        <SelectTrigger data-testid="recipe-category-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CATEGORIES.filter(c => c.value !== "ALL").map(cat => (
                            <SelectItem key={cat.value} value={cat.value}>
                              {cat.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Ingredients */}
                    <div className="space-y-2">
                      <Label>Ingredients (one per line)</Label>
                      <Textarea
                        value={formData.ingredients}
                        onChange={(e) => setFormData(prev => ({ ...prev, ingredients: e.target.value }))}
                        placeholder="Kokum – 80 g&#10;Coconut milk – 1 litre&#10;Green chilli – 2&#10;..."
                        disabled={!isEditing && !isCreating}
                        rows={8}
                        className="font-mono text-sm"
                        data-testid="recipe-ingredients-input"
                      />
                    </div>

                    {/* Method */}
                    <div className="space-y-2">
                      <Label>Method Steps (one per line)</Label>
                      <Textarea
                        value={formData.method}
                        onChange={(e) => setFormData(prev => ({ ...prev, method: e.target.value }))}
                        placeholder="Soak kokum in warm water for 10 minutes.&#10;Blend coconut milk with spices.&#10;..."
                        disabled={!isEditing && !isCreating}
                        rows={10}
                        className="font-mono text-sm"
                        data-testid="recipe-method-input"
                      />
                    </div>

                    {/* Action buttons */}
                    {(isEditing || isCreating) && (
                      <div className="flex gap-3 pt-4 sticky bottom-0 bg-background py-4">
                        <Button onClick={saveRecipe} disabled={saving} data-testid="save-recipe-btn">
                          {saving ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4 mr-2" />
                          )}
                          {isCreating ? "Create Recipe" : "Save Changes"}
                        </Button>
                        <Button variant="outline" onClick={cancelEdit}>
                          <X className="w-4 h-4 mr-2" />
                          Cancel
                        </Button>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              ) : (
                <div className="h-[400px] flex flex-col items-center justify-center text-muted-foreground">
                  <ChefHat className="w-16 h-16 mb-4 opacity-30" />
                  <p>Select a recipe to view or edit</p>
                  <p className="text-sm mt-2">Or click "Add New Recipe" to create one</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Recipe?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this recipe? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
