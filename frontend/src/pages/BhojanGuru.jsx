import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
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
  Sparkles,
  Heart,
  Sun,
  Cloud,
  Zap,
  Users,
  Calendar,
  MapPin,
  ThermometerSun,
  MessageCircle
} from "lucide-react";

// Categories for filtering
const RECIPE_CATEGORIES = [
  { key: "all", label: "All", icon: Utensils },
  { key: "drinks", label: "Drinks", icon: Soup },
  { key: "snacks", label: "Snacks", icon: UtensilsCrossed },
  { key: "mains", label: "Mains", icon: ChefHat },
  { key: "sweets", label: "Sweets", icon: Sparkles },
  { key: "fasting", label: "Fasting", icon: LeafyGreen },
  { key: "chutneys", label: "Chutneys", icon: Utensils },
];

// Map recipe keys to categories
function categorizeRecipe(key, category) {
  if (category) return category;
  const keyLower = key.toLowerCase();
  if (keyLower.includes("piyush") || keyLower.includes("kokum") || keyLower.includes("sol") || 
      keyLower.includes("tea") || keyLower.includes("pani") || keyLower.includes("awala") ||
      keyLower.includes("panhe") || keyLower.includes("lemon") || keyLower.includes("buttermilk")) return "drinks";
  if (keyLower.includes("vada") || keyLower.includes("bhaji") || keyLower.includes("vadi") || 
      keyLower.includes("pakoda") || keyLower.includes("kachori") || keyLower.includes("pohe")) return "snacks";
  if (keyLower.includes("modak") || keyLower.includes("poli") || keyLower.includes("shrikhand") ||
      keyLower.includes("basundi") || keyLower.includes("halwa") || keyLower.includes("sheera") ||
      keyLower.includes("ladoo") || keyLower.includes("kheer") || keyLower.includes("gulab")) return "sweets";
  if (keyLower.includes("sabudana") || keyLower.includes("upvas") || keyLower.includes("vrat")) return "fasting";
  if (keyLower.includes("chutney")) return "chutneys";
  return "mains";
}

// Days of week for region tab
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function BhojanGuru() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recipeData, setRecipeData] = useState({ recipes: {}, thalis: {}, bhojanGuru: {} });
  const [bhojanGuruData, setBhojanGuruData] = useState({ bhojanGuru: {}, regionWise: {}, bodyNeedMatrix: {} });
  const [descriptionData, setDescriptionData] = useState({});
  const [copiedField, setCopiedField] = useState(null);
  const [activeTab, setActiveTab] = useState("region");
  const [currentDay, setCurrentDay] = useState(DAYS[new Date().getDay()]);
  
  // Debug: Log when selectedRecipe changes
  useEffect(() => {
    console.log("BhojanGuru: selectedRecipe changed to:", selectedRecipe?.key || "null");
  }, [selectedRecipe]);
  
  // Body Need form state
  const [bodyForm, setBodyForm] = useState({
    energy: "normal",
    digestion: "normal",
    mood: "calm",
    spice: "mild",
    purpose: "family",
    weather: "any"
  });
  const [bodyRecommendations, setBodyRecommendations] = useState([]);
  const [loadingBody, setLoadingBody] = useState(false);

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [recipesRes, descriptionsRes, bhojanRes] = await Promise.all([
          api.get("/recipes"),
          api.get("/descriptions"),
          api.get("/bhojan_guru")
        ]);
        setRecipeData(recipesRes.data);
        setDescriptionData(descriptionsRes.data.descriptions || {});
        setBhojanGuruData(bhojanRes.data);
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
    category: categorizeRecipe(key, data.category)
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

  // Generate Body Need recommendations
  const generateBodyRecommendations = async () => {
    setLoadingBody(true);
    try {
      const res = await api.post("/bhojan_guru/body_need", null, { params: bodyForm });
      setBodyRecommendations(res.data.recommendations || []);
    } catch (e) {
      console.error("Failed to get body recommendations:", e);
      toast.error("Failed to generate recommendations");
    } finally {
      setLoadingBody(false);
    }
  };

  // Format region order for copy/WhatsApp
  const formatRegionOrder = (recommendation) => {
    if (!recommendation || !recommendation.recommendedOrder) return "";
    const order = recommendation.recommendedOrder;
    return `Purnabramha AI Region Order:
- DAL: ${order.dal || ""}
- BHAJI: ${order.bhaji || ""}
- RICE: ${order.rice || ""}
- ROTI: ${order.roti || ""}
- DRINK: ${order.drink || ""}
- SWEET: ${order.sweet || ""}

Today's Highlights: ${recommendation.highlights || ""}`;
  };

  // Current region recommendation
  const currentRegion = bhojanGuruData.regionWise?.[currentDay] || null;

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
        <p className="text-xl text-muted-foreground mt-1">Bhojan Guru - Smart Food Guide</p>
        <p className="text-sm text-muted-foreground mt-2">
          One table. One QR. Your thali is guided by Maharashtra's region, rhythm, and "right way to eat".
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="region" data-testid="tab-region">
            <MapPin className="w-4 h-4 mr-2" />
            Region Thali
          </TabsTrigger>
          <TabsTrigger value="body" data-testid="tab-body">
            <Heart className="w-4 h-4 mr-2" />
            Body Need
          </TabsTrigger>
          <TabsTrigger value="recipes" data-testid="tab-recipes">
            <ChefHat className="w-4 h-4 mr-2" />
            Recipes
          </TabsTrigger>
          <TabsTrigger value="menu" data-testid="tab-menu">
            <BookOpen className="w-4 h-4 mr-2" />
            Menu Desc
          </TabsTrigger>
        </TabsList>

        {/* REGION THALI TAB */}
        <TabsContent value="region" className="mt-4">
          <div className="space-y-6">
            {/* Day selector */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-primary" />
                  Today's Region Thali
                </CardTitle>
                <CardDescription>
                  Region mode is for culture + story. Each day features a different Maharashtra region.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-4">
                  {DAYS.map(day => (
                    <Button
                      key={day}
                      variant={currentDay === day ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentDay(day)}
                      className="rounded-full"
                      data-testid={`day-${day.toLowerCase()}`}
                    >
                      {day.slice(0, 3)}
                    </Button>
                  ))}
                </div>

                {currentRegion ? (
                  <div className="space-y-4">
                    <div className="bg-primary/5 rounded-lg p-4">
                      <h3 className="text-xl font-bold flex items-center gap-2">
                        <MapPin className="w-5 h-5 text-primary" />
                        {currentDay}: {currentRegion.region} — {currentRegion.thaliName}
                      </h3>
                      <p className="text-muted-foreground mt-2">{currentRegion.highlights}</p>
                    </div>

                    <div className="space-y-2">
                      <h4 className="font-semibold flex items-center gap-2">
                        <Utensils className="w-4 h-4 text-secondary" />
                        Recommended Order (from today's menu)
                      </h4>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {Object.entries(currentRegion.recommendedOrder || {}).map(([category, item]) => (
                          <div key={category} className="bg-card border rounded-lg p-3">
                            <span className="text-xs text-muted-foreground uppercase">{category}</span>
                            <p className="font-medium">{item}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex gap-2 pt-4">
                      <Button
                        variant="outline"
                        onClick={() => copyToClipboard(formatRegionOrder(currentRegion), "region")}
                        data-testid="copy-region-order"
                      >
                        {copiedField === "region" ? (
                          <Check className="w-4 h-4 mr-2 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4 mr-2" />
                        )}
                        Copy Order
                      </Button>
                      <Button
                        variant="default"
                        onClick={() => {
                          const text = encodeURIComponent(formatRegionOrder(currentRegion));
                          window.open(`https://wa.me/?text=${text}`, "_blank");
                        }}
                        data-testid="whatsapp-region"
                      >
                        <MessageCircle className="w-4 h-4 mr-2" />
                        Send on WhatsApp
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground">No recommendation available for this day.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* BODY NEED TAB */}
        <TabsContent value="body" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Heart className="w-5 h-5 text-red-500" />
                My Body Need Thali
              </CardTitle>
              <CardDescription>
                Answer 6 quick questions — AI selects the best balance from our menu.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Energy */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  1) Energy right now?
                </Label>
                <RadioGroup
                  value={bodyForm.energy}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, energy: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["low", "normal", "active"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`energy-${opt}`} />
                      <Label htmlFor={`energy-${opt}`} className="capitalize">{opt === "low" ? "Low / tired" : opt === "active" ? "Very active" : opt}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* Digestion */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <LeafyGreen className="w-4 h-4 text-green-500" />
                  2) Digestion today?
                </Label>
                <RadioGroup
                  value={bodyForm.digestion}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, digestion: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["sensitive", "normal", "strong"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`digestion-${opt}`} />
                      <Label htmlFor={`digestion-${opt}`} className="capitalize">{opt}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* Mood */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Heart className="w-4 h-4 text-pink-500" />
                  3) Mood?
                </Label>
                <RadioGroup
                  value={bodyForm.mood}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, mood: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["calm", "stressed", "irritated"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`mood-${opt}`} />
                      <Label htmlFor={`mood-${opt}`} className="capitalize">{opt}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* Spice comfort */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-orange-500" />
                  4) Spice comfort?
                </Label>
                <RadioGroup
                  value={bodyForm.spice}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, spice: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["no_spice", "mild", "medium", "high"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`spice-${opt}`} />
                      <Label htmlFor={`spice-${opt}`} className="capitalize">{opt.replace("_", " ")}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* Purpose */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-blue-500" />
                  5) You are here for…
                </Label>
                <RadioGroup
                  value={bodyForm.purpose}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, purpose: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["work", "family", "quick"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`purpose-${opt}`} />
                      <Label htmlFor={`purpose-${opt}`} className="capitalize">{opt === "work" ? "Work / focus" : opt === "family" ? "Family / comfort" : "Quick meal"}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              {/* Weather */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <ThermometerSun className="w-4 h-4 text-cyan-500" />
                  6) Weather vibe?
                </Label>
                <RadioGroup
                  value={bodyForm.weather}
                  onValueChange={(v) => setBodyForm({ ...bodyForm, weather: v })}
                  className="flex flex-wrap gap-4"
                >
                  {["hot", "cold", "rainy", "any"].map(opt => (
                    <div key={opt} className="flex items-center space-x-2">
                      <RadioGroupItem value={opt} id={`weather-${opt}`} />
                      <Label htmlFor={`weather-${opt}`} className="capitalize">{opt}</Label>
                    </div>
                  ))}
                </RadioGroup>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={generateBodyRecommendations} disabled={loadingBody} data-testid="generate-body-order">
                  {loadingBody && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Generate My Order
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setBodyForm({
                      energy: "normal",
                      digestion: "normal",
                      mood: "calm",
                      spice: "mild",
                      purpose: "family",
                      weather: "any"
                    });
                    setBodyRecommendations([]);
                  }}
                >
                  Reset
                </Button>
              </div>

              {/* Recommendations */}
              {bodyRecommendations.length > 0 && (
                <div className="space-y-4 pt-4 border-t">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" />
                    Your Recommended Order
                  </h4>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {bodyRecommendations.map((item, i) => (
                      <Card key={item.key} className={i === 0 ? "border-primary border-2" : ""}>
                        <CardContent className="pt-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <h5 className="font-semibold">{item.display}</h5>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {item.tags?.map(tag => (
                                  <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                                ))}
                              </div>
                            </div>
                            {i === 0 && <Badge className="bg-primary">Top Pick</Badge>}
                          </div>
                          {item.best_with?.length > 0 && (
                            <p className="text-xs text-muted-foreground mt-2">
                              Best with: {item.best_with.join(", ")}
                            </p>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* RECIPES TAB */}
        <TabsContent value="recipes" className="mt-4">
          {/* Search */}
          <Card className="mb-4">
            <CardContent className="pt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  placeholder="Search recipes, ingredients..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                  data-testid="recipe-search"
                />
              </div>
            </CardContent>
          </Card>

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
                  Recipes ({filteredRecipes.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px] pr-4">
                  <div className="space-y-2">
                    {filteredRecipes.length > 0 ? (
                      filteredRecipes.map((recipe) => (
                        <div
                          key={recipe.key}
                          onClick={() => {
                            console.log("Recipe clicked:", recipe.key);
                            setSelectedRecipe(recipe);
                          }}
                          className={`w-full text-left p-4 rounded-lg border transition-all hover:shadow-md cursor-pointer ${
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
                        </div>
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

        {/* MENU DESCRIPTIONS TAB */}
        <TabsContent value="menu" className="mt-4">
          {/* Search */}
          <Card className="mb-4">
            <CardContent className="pt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                  placeholder="Search menu items..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                  data-testid="menu-search"
                />
              </div>
            </CardContent>
          </Card>

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
