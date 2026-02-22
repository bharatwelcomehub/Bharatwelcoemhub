import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  ChefHat, 
  Search, 
  Utensils,
  LeafyGreen,
  Copy,
  Check,
  Loader2,
  BookOpen,
  Soup,
  UtensilsCrossed,
  Sparkles
} from "lucide-react";

// Categories for filtering
const RECIPE_CATEGORIES = [
  { key: "all", label: "All", icon: Utensils },
  { key: "drinks", label: "Drinks", icon: Soup },
  { key: "snacks", label: "Snacks", icon: UtensilsCrossed },
  { key: "mains", label: "Mains", icon: ChefHat },
  { key: "sweets", label: "Sweets", icon: Sparkles },
  { key: "thalis", label: "Thalis", icon: BookOpen },
];

// Map recipe keys to categories
function categorizeRecipe(key) {
  const keyLower = key.toLowerCase();
  if (keyLower.includes("piyush") || keyLower.includes("kokum") || keyLower.includes("sol") || 
      keyLower.includes("tea") || keyLower.includes("pani") || keyLower.includes("awala") ||
      keyLower.includes("panhe") || keyLower.includes("lemon")) return "drinks";
  if (keyLower.includes("vada") || keyLower.includes("bhaji") || keyLower.includes("vadi") || 
      keyLower.includes("pakoda") || keyLower.includes("kachori")) return "snacks";
  if (keyLower.includes("modak") || keyLower.includes("poli") || keyLower.includes("shrikhand") ||
      keyLower.includes("basundi") || keyLower.includes("halwa") || keyLower.includes("sheera") ||
      keyLower.includes("ladoo") || keyLower.includes("kheer")) return "sweets";
  if (keyLower.includes("thali")) return "thalis";
  return "mains";
}

export default function BhojanGuru() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recipeData, setRecipeData] = useState({ recipes: {}, thalis: {}, bhojanGuru: {} });
  const [descriptionData, setDescriptionData] = useState({});
  const [copiedField, setCopiedField] = useState(null);
  const [activeTab, setActiveTab] = useState("recipes");

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [recipesRes, descriptionsRes] = await Promise.all([
          api.get("/recipes"),
          api.get("/descriptions")
        ]);
        setRecipeData(recipesRes.data);
        setDescriptionData(descriptionsRes.data.descriptions || {});
      } catch (e) {
        console.error("Failed to load recipe data:", e);
        toast.error("Failed to load recipe data");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Convert recipes object to array for display
  const recipesList = Object.entries(recipeData.recipes || {}).map(([key, data]) => ({
    key,
    ...data,
    category: categorizeRecipe(key)
  }));

  // Filter recipes
  const filteredRecipes = recipesList.filter(recipe => {
    const matchesSearch = 
      recipe.display?.toLowerCase().includes(search.toLowerCase()) ||
      recipe.key?.toLowerCase().includes(search.toLowerCase()) ||
      (recipe.ingredients || []).some(i => i.toLowerCase().includes(search.toLowerCase()));
    const matchesCategory = selectedCategory === "all" || recipe.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Thalis list
  const thalisList = Object.entries(recipeData.thalis || {}).map(([key, data]) => ({
    key,
    ...data
  }));

  // Descriptions list
  const descriptionsList = Object.entries(descriptionData || {}).map(([key, data]) => ({
    key,
    ...data
  })).filter(item => 
    item.display?.toLowerCase().includes(search.toLowerCase()) ||
    item.desc_short?.toLowerCase().includes(search.toLowerCase())
  );

  // Copy to clipboard
  const copyToClipboard = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      toast.success("Copied to clipboard!");
      setTimeout(() => setCopiedField(null), 2000);
    } catch (e) {
      toast.error("Failed to copy");
    }
  };

  // Format recipe for copying
  const formatRecipeForCopy = (recipe) => {
    let text = `${recipe.display}\n\n`;
    if (recipe.ingredients?.length) {
      text += "INGREDIENTS:\n";
      recipe.ingredients.forEach(ing => {
        text += `• ${ing}\n`;
      });
    }
    if (recipe.method?.length) {
      text += "\nMETHOD:\n";
      recipe.method.forEach((step, i) => {
        text += `${i + 1}. ${step}\n`;
      });
    }
    return text;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2">Loading Bhojan Guru...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-primary font-marathi" data-testid="bhojan-guru-title">
          भोजन गुरु
        </h1>
        <p className="text-xl text-muted-foreground mt-1">Bhojan Guru - Recipe Database</p>
        <p className="text-sm text-muted-foreground mt-2">
          {recipesList.length} Recipes • {thalisList.length} Thalis • {descriptionsList.length} Menu Items
        </p>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              placeholder="Search recipes, ingredients, or menu items..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 h-12 text-lg"
              data-testid="recipe-search"
            />
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="recipes" data-testid="tab-recipes">
            <ChefHat className="w-4 h-4 mr-2" />
            Recipes ({filteredRecipes.length})
          </TabsTrigger>
          <TabsTrigger value="thalis" data-testid="tab-thalis">
            <UtensilsCrossed className="w-4 h-4 mr-2" />
            Thalis ({thalisList.length})
          </TabsTrigger>
          <TabsTrigger value="descriptions" data-testid="tab-descriptions">
            <BookOpen className="w-4 h-4 mr-2" />
            Menu Descriptions
          </TabsTrigger>
        </TabsList>

        {/* RECIPES TAB */}
        <TabsContent value="recipes" className="mt-4">
          {/* Category filter */}
          <div className="flex flex-wrap gap-2 mb-4">
            {RECIPE_CATEGORIES.map(cat => (
              <Button
                key={cat.key}
                variant={selectedCategory === cat.key ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(cat.key)}
                className="rounded-full"
                data-testid={`filter-${cat.key}`}
              >
                <cat.icon className="w-4 h-4 mr-1" />
                {cat.label}
              </Button>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {/* Recipe list */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Utensils className="w-5 h-5 text-secondary" />
                  Recipes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px] pr-4">
                  <div className="space-y-2">
                    {filteredRecipes.length > 0 ? (
                      filteredRecipes.map((recipe) => (
                        <button
                          key={recipe.key}
                          onClick={() => setSelectedRecipe(recipe)}
                          className={`w-full text-left p-4 rounded-lg border transition-all hover:shadow-md ${
                            selectedRecipe?.key === recipe.key 
                              ? "bg-primary/10 border-primary" 
                              : "bg-card hover:bg-muted/50 border-border"
                          }`}
                          data-testid={`recipe-${recipe.key}`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold">{recipe.display}</span>
                            <Badge variant="outline" className="capitalize">{recipe.category}</Badge>
                          </div>
                          {recipe.ingredients && (
                            <p className="text-xs text-muted-foreground mt-1 truncate">
                              {recipe.ingredients.slice(0, 3).join(", ")}...
                            </p>
                          )}
                        </button>
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <ChefHat className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No recipes found</p>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Recipe details */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-lg">
                    <ChefHat className="w-5 h-5 text-primary" />
                    Recipe Details
                  </span>
                  {selectedRecipe && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(formatRecipeForCopy(selectedRecipe), "recipe")}
                      data-testid="copy-recipe"
                    >
                      {copiedField === "recipe" ? (
                        <Check className="w-4 h-4 mr-1 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4 mr-1" />
                      )}
                      Copy
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px] pr-4">
                  {selectedRecipe ? (
                    <div className="space-y-6 animate-fadeIn">
                      <div>
                        <h2 className="text-2xl font-bold text-primary">
                          {selectedRecipe.display}
                        </h2>
                        <Badge className="mt-2 capitalize">{selectedRecipe.category}</Badge>
                      </div>

                      {selectedRecipe.ingredients?.length > 0 && (
                        <div className="space-y-2">
                          <h3 className="font-bold flex items-center gap-2">
                            <LeafyGreen className="w-4 h-4 text-green-600" />
                            Ingredients
                          </h3>
                          <div className="bg-muted/50 rounded-lg p-4 space-y-1">
                            {selectedRecipe.ingredients.map((ing, i) => (
                              <p key={i} className="text-sm flex items-start gap-2">
                                <span className="text-primary">•</span>
                                {ing}
                              </p>
                            ))}
                          </div>
                        </div>
                      )}

                      {selectedRecipe.method?.length > 0 && (
                        <div className="space-y-2">
                          <h3 className="font-bold flex items-center gap-2">
                            <ChefHat className="w-4 h-4 text-orange-600" />
                            Method
                          </h3>
                          <div className="space-y-2">
                            {selectedRecipe.method.map((step, i) => (
                              <div key={i} className="flex gap-3 p-3 bg-muted/30 rounded-lg">
                                <span className="bg-primary text-primary-foreground w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold">
                                  {i + 1}
                                </span>
                                <p className="text-sm">{step}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <ChefHat className="w-16 h-16 mx-auto mb-4 opacity-30" />
                      <p>Select a recipe to view details</p>
                      <p className="text-sm mt-2 font-marathi">पाककृती निवडा</p>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* THALIS TAB */}
        <TabsContent value="thalis" className="mt-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {thalisList.map((thali) => (
              <Card key={thali.key} className="hover:shadow-lg transition-shadow" data-testid={`thali-${thali.key}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{thali.display}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <h4 className="text-sm font-semibold text-muted-foreground mb-2">Items Included:</h4>
                    <div className="flex flex-wrap gap-1">
                      {(thali.items || []).map((item, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {item.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  {thali.notes?.length > 0 && (
                    <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                      {thali.notes.map((note, i) => (
                        <p key={i}>• {note}</p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* DESCRIPTIONS TAB */}
        <TabsContent value="descriptions" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4">
            {descriptionsList.slice(0, 50).map((item) => (
              <Card key={item.key} className="hover:shadow-md transition-shadow" data-testid={`desc-${item.key}`}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <h3 className="font-semibold">{item.display}</h3>
                      {item.price_aud && (
                        <Badge variant="outline" className="mt-1">
                          ${item.price_aud} AUD
                        </Badge>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(
                        `${item.display}\n${item.desc_short || ""}\n\nMarathi: ${item.desc_short_mr || ""}`,
                        item.key
                      )}
                    >
                      {copiedField === item.key ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">{item.desc_short}</p>
                  {item.desc_short_mr && (
                    <p className="text-sm text-muted-foreground mt-2 font-marathi border-t pt-2">
                      {item.desc_short_mr}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          {descriptionsList.length > 50 && (
            <p className="text-center text-muted-foreground mt-4">
              Showing 50 of {descriptionsList.length} items. Use search to find more.
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
