import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  ChefHat, 
  Search, 
  Utensils,
  LeafyGreen
} from "lucide-react";

// Recipe database (hardcoded for now - can be moved to MongoDB)
const RECIPES = {
  "solkadhi": {
    display: "सोलकढी / Solkadhi",
    category: "Drink",
    ingredients: ["kokam", "coconut milk", "garlic", "green chili", "coriander"],
    description: "A refreshing Maharashtrian drink made with kokam and coconut milk",
    descriptionMr: "कोकम आणि नारळाच्या दुधापासून बनवलेले थंडगार पेय"
  },
  "misal": {
    display: "मिसळ पाव / Misal Pav",
    category: "Snack",
    ingredients: ["sprouted moth beans", "onion", "potato", "farsan", "pav"],
    description: "Spicy Maharashtrian curry made with sprouted moth beans served with pav",
    descriptionMr: "मटकी उसळीपासून बनवलेला तिखट रस्सा पाव बरोबर"
  },
  "puranpoli": {
    display: "पुरणपोळी / Puran Poli",
    category: "Sweet",
    ingredients: ["chana dal", "jaggery", "wheat flour", "cardamom", "ghee"],
    description: "Sweet flatbread stuffed with jaggery and chana dal filling",
    descriptionMr: "चण्याच्या डाळ आणि गुळाच्या पुराणाची गोड पोळी"
  },
  "bharli_vangi": {
    display: "भरली वांगी / Bharli Vangi",
    category: "Main",
    ingredients: ["brinjal", "coconut", "peanuts", "sesame", "tamarind"],
    description: "Stuffed brinjal curry with coconut-peanut filling",
    descriptionMr: "नारळ-शेंगदाण्याच्या मसाल्याने भरलेली वांगी"
  },
  "sabudana_khichdi": {
    display: "साबुदाणा खिचडी / Sabudana Khichdi",
    category: "Snack",
    ingredients: ["sabudana", "potato", "peanuts", "cumin", "green chili"],
    description: "Fasting-friendly dish made with tapioca pearls and potatoes",
    descriptionMr: "उपवासाचा साबुदाणा, बटाटा आणि शेंगदाण्याचा पदार्थ"
  },
  "varan_bhaat": {
    display: "वरण भात / Varan Bhaat",
    category: "Main",
    ingredients: ["toor dal", "rice", "ghee", "cumin"],
    description: "Simple dal-rice comfort food, staple of Maharashtrian cuisine",
    descriptionMr: "तूर डाळ-भात, महाराष्ट्रीयन जेवणाचा मुख्य पदार्थ"
  },
  "modak": {
    display: "मोदक / Modak",
    category: "Sweet",
    ingredients: ["rice flour", "coconut", "jaggery", "cardamom"],
    description: "Steamed dumplings with sweet coconut filling, offered to Lord Ganesha",
    descriptionMr: "नारळ आणि गुळाचे गोड सारण भरलेले मोदक"
  },
  "pohe": {
    display: "पोहे / Pohe",
    category: "Breakfast",
    ingredients: ["flattened rice", "onion", "potato", "mustard seeds", "curry leaves"],
    description: "Light breakfast made with flattened rice and spices",
    descriptionMr: "पोहे, कांदा, बटाटा, मोहरी आणि कढीपत्त्याचा नाश्ता"
  },
  "kothimbir_vadi": {
    display: "कोथिंबीर वडी / Kothimbir Vadi",
    category: "Snack",
    ingredients: ["coriander leaves", "gram flour", "ginger", "green chili", "sesame"],
    description: "Steamed and fried coriander cakes, crispy and flavorful",
    descriptionMr: "कोथिंबीर आणि बेसनाच्या वड्या"
  },
  "aamti": {
    display: "आमटी / Aamti",
    category: "Main",
    ingredients: ["toor dal", "kokum", "jaggery", "tamarind", "goda masala"],
    description: "Sweet and sour dal preparation unique to Maharashtra",
    descriptionMr: "गोड आणि आंबट चवीची महाराष्ट्रीयन डाळ"
  },
  "thalipeeth": {
    display: "थालीपीठ / Thalipeeth",
    category: "Breakfast",
    ingredients: ["bhajani flour", "onion", "coriander", "cumin"],
    description: "Multi-grain flatbread made with special bhajani flour",
    descriptionMr: "भाजणीच्या पिठाचे तिखट थालीपीठ"
  },
  "zunka": {
    display: "झुणका भाकर / Zunka Bhakar",
    category: "Main",
    ingredients: ["gram flour", "onion", "green chili", "garlic"],
    description: "Dry gram flour preparation served with jowar bhakri",
    descriptionMr: "बेसनाचा कोरडा झुणका ज्वारीच्या भाकरीबरोबर"
  }
};

const CATEGORIES = ["All", "Main", "Snack", "Breakfast", "Sweet", "Drink"];

export default function BhojanGuru() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedRecipe, setSelectedRecipe] = useState(null);

  const recipes = Object.entries(RECIPES);

  const filteredRecipes = recipes.filter(([key, recipe]) => {
    const matchesSearch = 
      recipe.display.toLowerCase().includes(search.toLowerCase()) ||
      recipe.ingredients.some(i => i.toLowerCase().includes(search.toLowerCase()));
    const matchesCategory = selectedCategory === "All" || recipe.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-primary font-marathi">
          भोजन गुरु
        </h1>
        <p className="text-xl text-muted-foreground mt-1">Bhojan Guru</p>
        <p className="text-sm text-muted-foreground mt-2">
          Explore authentic Maharashtrian recipes
        </p>
      </div>

      {/* Search and filter */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              placeholder="Search recipes or ingredients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 h-12 text-lg"
              data-testid="recipe-search"
            />
          </div>
          
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(cat => (
              <Button
                key={cat}
                variant={selectedCategory === cat ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(cat)}
                className="rounded-full"
              >
                {cat}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Recipe list */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Utensils className="w-5 h-5 text-secondary" />
              Recipes ({filteredRecipes.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 max-h-[500px] overflow-y-auto">
            {filteredRecipes.length > 0 ? (
              filteredRecipes.map(([key, recipe]) => (
                <button
                  key={key}
                  onClick={() => setSelectedRecipe({ key, ...recipe })}
                  className={`w-full text-left p-4 rounded-lg border transition-all hover:shadow-md ${
                    selectedRecipe?.key === key 
                      ? "bg-primary/10 border-primary" 
                      : "bg-card hover:bg-muted/50 border-border"
                  }`}
                  data-testid={`recipe-${key}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{recipe.display}</span>
                    <Badge variant="outline">{recipe.category}</Badge>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <ChefHat className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No recipes found</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recipe details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ChefHat className="w-5 h-5 text-primary" />
              Recipe Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedRecipe ? (
              <div className="space-y-6 animate-fadeIn">
                <div>
                  <h2 className="text-2xl font-bold text-primary font-marathi">
                    {selectedRecipe.display}
                  </h2>
                  <Badge className="mt-2">{selectedRecipe.category}</Badge>
                </div>

                <div className="space-y-2">
                  <h3 className="font-bold flex items-center gap-2">
                    <LeafyGreen className="w-4 h-4 text-green-600" />
                    Ingredients
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedRecipe.ingredients.map((ing, i) => (
                      <Badge key={i} variant="secondary" className="capitalize">
                        {ing}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="font-bold">Description</h3>
                  <p className="text-muted-foreground">{selectedRecipe.description}</p>
                </div>

                <div className="space-y-2 bg-muted/50 rounded-lg p-4">
                  <h3 className="font-bold font-marathi">मराठी वर्णन</h3>
                  <p className="text-muted-foreground font-marathi">
                    {selectedRecipe.descriptionMr}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <ChefHat className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p>Select a recipe to view details</p>
                <p className="text-sm mt-2 font-marathi">
                  पाककृती निवडा
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
