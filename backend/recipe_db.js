/* ===================== SET 1 — DRINKS + TEA ===================== */
window.RECIPE_DB = window.RECIPE_DB || {};

Object.assign(window.RECIPE_DB, {
  solkadhi: {
    display: "Solkadhi",
    ingredients: [
      "Water – 1 litre",
      "Kokum syrup – 50 g",
      "Kokum aagal – 50 g",
      "Ginger paste – 40 g",
      "Garlic paste – 40 g",
      "Green chilli paste – 40 g",
      "Coconut milk – 200 g",
      "Salt – to taste",
      "Fresh coriander – for garnish"
    ],
    method: [
      "Take a clean vessel for solkadhi preparation.",
      "Add water, coconut milk, kokum syrup, kokum aagal, ginger paste, garlic paste and green chilli paste.",
      "Stir well until fully mixed.",
      "Filter the mixture (optional but recommended for smooth solkadhi).",
      "Taste and adjust salt as required.",
      "Garnish with chopped coriander and serve chilled.",
      "Note: Use coriander garnish on all days except Saturday. On Saturday, use coriander paste instead.",
      "Note: Always prepare drinks as the first task of the day."
    ]
  },

  masala_kokum: {
    display: "Masala Kokum",
    ingredients: [
      "Water – 1 litre",
      "Kokum syrup – 100 g",
      "Kokum aagal – 50 g",
      "Ginger paste – 40 g",
      "Garlic paste – 40 g",
      "Green chilli paste – 40 g",
      "Salt – to taste",
      "Fresh coriander – for garnish (optional)"
    ],
    method: [
      "Take a clean vessel for masala kokum.",
      "Add water, kokum syrup, kokum aagal, ginger paste, garlic paste and green chilli paste.",
      "Stir well to combine.",
      "Filter if required.",
      "Taste and adjust salt as required.",
      "Garnish with chopped coriander (optional) and serve chilled."
    ]
  },

  kokum: {
    display: "Kokum",
    ingredients: [
      "Water – 1 litre",
      "Kokum syrup – 200 g",
      "Jeera powder – 10 g",
      "Salt – to taste"
    ],
    method: [
      "Take a clean vessel.",
      "Add water, kokum syrup, jeera powder and salt.",
      "Stir well until mixed.",
      "Taste and adjust seasoning as required.",
      "Serve chilled.",
      "Note: No garnish required."
    ]
  },

  piyush: {
    display: "Piyush",
    ingredients: [
      "Shrikhand – 200 g",
      "Curd – 80 g",
      "Milk – 80 g",
      "Black pepper powder – 1 pinch",
      "Cinnamon powder – 1 pinch",
      "Almonds (badam) – chopped, for garnish"
    ],
    method: [
      "In a bowl, whisk shrikhand, curd and milk to make a smooth, lump-free mixture.",
      "Add black pepper powder and cinnamon powder. Mix well.",
      "Pour into serving glasses.",
      "Garnish with chopped almonds.",
      "Serve chilled.",
      "Note: Maintain correct shrikhand consistency."
    ]
  },

  rose_piyush: {
    display: "Rose Piyush",
    ingredients: [
      "Shrikhand – 100 g",
      "Milk – 100 ml",
      "Rose water – 20 ml",
      "Cinnamon powder – 1 pinch",
      "Black pepper powder – 1 pinch",
      "Almonds – sliced, for garnish",
      "Rose petals – for garnish"
    ],
    method: [
      "Whisk shrikhand, milk and rose water into a smooth mixture.",
      "Add cinnamon and black pepper powder. Mix well.",
      "Pour into serving glasses.",
      "Garnish with sliced almonds and rose petals.",
      "Serve chilled.",
      "Note: Crush rose petals gently in palms before adding for garnish."
    ]
  },

  mango_piyush: {
    display: "Mango Piyush",
    ingredients: [
      "Shrikhand – 200 g",
      "Mango pulp – 50 g",
      "Milk – 100 ml",
      "Almonds – sliced, for garnish"
    ],
    method: [
      "Whisk shrikhand, mango pulp and milk into a smooth, lump-free mixture.",
      "Pour into serving glasses.",
      "Garnish with sliced almonds.",
      "Serve chilled.",
      "Note: Do not add curd or black pepper in mango piyush."
    ]
  },

  awala: {
    display: "Awala (Amla Drink)",
    ingredients: [
      "Water – 1 litre",
      "Awala/Amla syrup – 200 ml",
      "Salt – 5 g"
    ],
    method: [
      "Take water in a clean container.",
      "Add amla syrup and salt.",
      "Mix well.",
      "Taste and serve chilled."
    ]
  },

  aam_panhe: {
    display: "Aam Panha",
    ingredients: [
      "Raw mango – 1 (large) or as required",
      "Sugar – as per taste",
      "Salt – as per taste",
      "Water – as required"
    ],
    method: [
      "Pressure cook raw mango for 2 whistles.",
      "Cool completely, then scoop out the pulp and make a smooth puree.",
      "Add sugar and salt, mix well.",
      "Add water to adjust consistency.",
      "Serve chilled."
    ]
  },

  limbu_pani: {
    display: "Limbu Pani",
    ingredients: [
      "Lemon – 6 pcs (approx. 40 g each)",
      "Chilled water – 1 litre",
      "Sugar – 200 g",
      "Salt – 2 pinches",
      "Lemon slices – optional",
      "Ice cubes – as required"
    ],
    method: [
      "Slice lemons and squeeze juice into water. Discard seeds.",
      "Add sugar and salt.",
      "Add ice cubes and stir until sugar dissolves.",
      "Pour into glasses and add lemon slices if using.",
      "Serve chilled."
    ]
  },

  masala_lemon: {
    display: "Masala Lemonade",
    ingredients: [
      "Lemon – 6 pcs (approx. 40 g each)",
      "Chilled water – 1 litre",
      "Sugar – 200 g",
      "Salt – 2 pinches",
      "Jaljeera powder – 2 tbsp",
      "Ice cubes – as required"
    ],
    method: [
      "Squeeze lemon juice into chilled water. Discard seeds.",
      "Add sugar and salt. Stir until dissolved.",
      "Add jaljeera powder and mix until dissolved.",
      "Add ice cubes and serve chilled."
    ]
  },

  tea_masala_tea: {
    display: "Tea / Masala Tea (Base)",
    ingredients: [
      "Milk – 1 cup (125 ml)",
      "Water – 1/4 cup (60 ml) (optional)",
      "Tea powder – 1 tsp (adjust as required)"
    ],
    method: [
      "Boil water in a saucepan (skip water if making strong milky tea).",
      "Add tea powder and boil 3–4 minutes on medium flame.",
      "Add milk and boil 6–7 minutes until colour deepens and bubbles rise.",
      "Switch off flame and strain into cups.",
      "Note: Add ginger/cardamom/cinnamon/tea masala only when required.",
      "Note: Adjust tea powder for strength."
    ]
  },

  tea_masala: {
    display: "Tea Masala",
    ingredients: [
      "Green cardamom – 100 g",
      "Nutmeg – 10 g",
      "Cinnamon – 10 g",
      "Cloves (lavang) – 10 g",
      "Sugar – 20 g"
    ],
    method: [
      "Wash and wipe cinnamon, then dry fully.",
      "Dry roast cinnamon and cardamom separately until aromatic.",
      "Break nutmeg into pieces and ensure clean/dry.",
      "Remove clove heads if using large cloves; avoid baby cloves as per SOP.",
      "Grind all roasted spices with sugar into a fine powder.",
      "Store airtight in a dry container."
    ]
  }
});
/* ===================== SET 2 — SNACKS ===================== */
window.RECIPE_DB = window.RECIPE_DB || {};

Object.assign(window.RECIPE_DB, {

  kanda_bhaji: {
    display: "Kanda Bhaji",
    ingredients: [
      "Onion – 1 kg (thinly sliced)",
      "Besan – 300 g",
      "Rice flour – 50 g",
      "Green chilli paste – 20 g",
      "Ajwain – 5 g",
      "Salt – to taste",
      "Turmeric – 5 g",
      "Red chilli powder – 10 g",
      "Oil – for deep frying"
    ],
    method: [
      "Slice onions thinly and separate layers.",
      "Add besan, rice flour, salt, turmeric, red chilli powder, ajwain and green chilli paste.",
      "Mix lightly without adding water (onion moisture is enough).",
      "Heat oil to medium-hot.",
      "Drop small portions and fry until golden and crisp.",
      "Remove and drain excess oil.",
      "Serve hot with chutney."
    ]
  },

  batata_vada: {
    display: "Batata Vada",
    ingredients: [
      "Boiled potatoes – 1 kg",
      "Green chilli paste – 20 g",
      "Ginger paste – 20 g",
      "Mustard seeds – 10 g",
      "Curry leaves – few",
      "Turmeric – 5 g",
      "Salt – to taste",
      "Besan – 300 g",
      "Oil – for frying"
    ],
    method: [
      "Mash boiled potatoes.",
      "Heat oil, add mustard seeds and curry leaves.",
      "Add ginger, green chilli paste and turmeric.",
      "Add mashed potato and salt, mix well.",
      "Make lemon-sized balls.",
      "Prepare besan batter with water and salt.",
      "Dip balls and deep fry till golden.",
      "Serve hot."
    ]
  },

  sabudana_vada: {
    display: "Sabudana Vada",
    ingredients: [
      "Soaked sabudana – 500 g",
      "Boiled potatoes – 500 g",
      "Roasted peanut powder – 150 g",
      "Green chilli paste – 20 g",
      "Cumin seeds – 10 g",
      "Salt – to taste",
      "Oil – for frying"
    ],
    method: [
      "Mix sabudana, mashed potatoes and peanut powder.",
      "Add cumin, green chilli paste and salt.",
      "Shape into flat patties.",
      "Heat oil on medium flame.",
      "Fry till golden and crisp.",
      "Serve hot with curd or chutney."
    ]
  },

  kothimbir_vadi: {
    display: "Kothimbir Vadi",
    ingredients: [
      "Fresh coriander – 2 bunches (chopped)",
      "Besan – 300 g",
      "Green chilli paste – 20 g",
      "Ginger paste – 15 g",
      "Cumin seeds – 10 g",
      "Salt – to taste",
      "Oil – for shallow/deep frying"
    ],
    method: [
      "Mix coriander, besan, chilli paste, ginger, cumin and salt.",
      "Add minimal water to form thick batter.",
      "Steam mixture for 20 minutes.",
      "Cool and cut into pieces.",
      "Shallow or deep fry until golden.",
      "Serve hot."
    ]
  },

  alu_vadi: {
    display: "Alu Vadi",
    ingredients: [
      "Colocasia leaves – 20 pcs",
      "Besan – 400 g",
      "Tamarind pulp – 80 g",
      "Jaggery – 100 g",
      "Red chilli powder – 20 g",
      "Salt – to taste",
      "Oil – for frying"
    ],
    method: [
      "Clean and dry colocasia leaves.",
      "Prepare thick besan paste with spices, tamarind and jaggery.",
      "Apply paste on leaves and roll tightly.",
      "Steam rolls for 30 minutes.",
      "Cool and slice.",
      "Shallow fry or temper before serving."
    ]
  },

  pudachi_vadi: {
    display: "Pudachi Vadi",
    ingredients: [
      "Besan – 300 g",
      "Coconut – 100 g (grated)",
      "Green chilli paste – 20 g",
      "Coriander – chopped",
      "Salt – to taste",
      "Oil – for frying"
    ],
    method: [
      "Prepare besan dough with spices.",
      "Prepare coconut stuffing separately.",
      "Roll besan dough, add stuffing and roll.",
      "Steam rolls until cooked.",
      "Cool, slice and deep fry till crisp.",
      "Serve hot."
    ]
  },

  maaswadi: {
    display: "Maaswadi",
    ingredients: [
      "Besan – 300 g",
      "Dry coconut – 100 g",
      "Peanut powder – 150 g",
      "Tamarind-jaggery paste – 120 g",
      "Red chilli powder – 20 g",
      "Salt – to taste",
      "Oil – for frying"
    ],
    method: [
      "Prepare thick besan dough and steam into sheet.",
      "Prepare stuffing with coconut, peanuts and spices.",
      "Spread stuffing, roll tightly.",
      "Slice into rounds.",
      "Deep fry till golden.",
      "Serve hot."
    ]
  },

  bread_pakoda: {
    display: "Bread Pakoda",
    ingredients: [
      "Bread slices – 10 pcs",
      "Boiled potato filling – 400 g",
      "Besan – 250 g",
      "Salt – to taste",
      "Red chilli powder – 10 g",
      "Oil – for frying"
    ],
    method: [
      "Prepare potato stuffing.",
      "Sandwich stuffing between bread slices.",
      "Prepare besan batter.",
      "Dip bread and deep fry till golden.",
      "Serve hot with chutney."
    ]
  },

  snacks_platter: {
    display: "Snacks Platter",
    ingredients: [
      "Kanda Bhaji",
      "Batata Vada",
      "Sabudana Vada",
      "Kothimbir Vadi",
      "Alu Vadi"
    ],
    method: [
      "Prepare all individual snacks as per SOP.",
      "Arrange neatly on platter.",
      "Serve hot with green and tamarind chutney."
    ]
  }

});
/* ===================== SET 3 — ALL (BREAKFAST + MAINS + RICE + SWEETS + BALGOPAL) ===================== */
window.RECIPE_DB = window.RECIPE_DB || {};

Object.assign(window.RECIPE_DB, {

/* ---------- BREAKFAST ---------- */

kanda_pohe: {
  display: "Kanda Pohe",
  ingredients: [
    "Poha – 1 kg",
    "Onion – 300 g (chopped)",
    "Peanuts – 150 g",
    "Mustard seeds – 10 g",
    "Turmeric – 5 g",
    "Green chillies – 20 g",
    "Salt – to taste",
    "Oil – 80 ml",
    "Lemon & coriander"
  ],
  method: [
    "Wash poha gently and drain.",
    "Heat oil, add mustard seeds and peanuts.",
    "Add onions, chillies and turmeric.",
    "Add poha and salt, mix lightly.",
    "Cover and steam 5 minutes.",
    "Finish with lemon and coriander."
  ]
},

tarri_pohe: {
  display: "Tarri Pohe",
  ingredients: [
    "Prepared kanda pohe",
    "Tarri (misal gravy) – as required",
    "Onion, farsan – garnish"
  ],
  method: [
    "Serve hot pohe in plate.",
    "Top generously with tarri.",
    "Garnish with onion and farsan.",
    "Serve immediately."
  ]
},

ghavan: {
  display: "Ghavan",
  ingredients: [
    "Rice flour – 500 g",
    "Salt – to taste",
    "Water – as required"
  ],
  method: [
    "Prepare thin batter using rice flour and water.",
    "Heat tawa lightly.",
    "Pour batter thinly.",
    "Cook without flipping.",
    "Serve soft and hot."
  ]
},

dhirde: {
  display: "Dhirde",
  ingredients: [
    "Wheat flour – 300 g",
    "Besan – 100 g",
    "Garlic – crushed",
    "Salt – to taste",
    "Water – as required"
  ],
  method: [
    "Mix all ingredients into thick batter.",
    "Spread on hot tawa.",
    "Cook both sides with oil.",
    "Serve hot with curd."
  ]
},

/* ---------- MAIN BHJI / USAL / KADHI ---------- */

matki_usal: {
  display: "Matki Usal",
  ingredients: [
    "Sprouted matki – 1 kg",
    "Onion – 300 g",
    "Tomato – 300 g",
    "Goda masala – 30 g",
    "Oil – 100 ml",
    "Salt – to taste"
  ],
  method: [
    "Heat oil, sauté onion till golden.",
    "Add tomato and masala.",
    "Add matki and water.",
    "Cook till soft and semi-gravy."
  ]
},

kadhi: {
  display: "Kadhi",
  ingredients: [
    "Curd – 1 litre",
    "Besan – 100 g",
    "Ginger – 20 g",
    "Curry leaves",
    "Mustard seeds",
    "Salt – to taste"
  ],
  method: [
    "Whisk curd and besan.",
    "Cook on low flame till thick.",
    "Prepare tempering.",
    "Add to kadhi and simmer."
  ]
},

misal_pav: {
  display: "Misal",
  ingredients: [
    "Sprouts – 1 kg",
    "Misal masala – 50 g",
    "Onion – chopped",
    "Tarri – as required",
    "Oil – 150 ml"
  ],
  method: [
    "Cook sprouts with masala.",
    "Prepare tarri separately.",
    "Assemble with onion and farsan.",
    "Serve hot."
  ]
},

/* ---------- RICE & ROTI ---------- */

steam_rice: {
  display: "Steam Rice",
  ingredients: [
    "Rice – 1 kg",
    "Water – as required"
  ],
  method: [
    "Wash rice thoroughly.",
    "Cook till fluffy.",
    "Serve hot."
  ]
},

masale_bhat: {
  display: "Masale Bhat",
  ingredients: [
    "Rice – 1 kg",
    "Goda masala – 40 g",
    "Vegetables – mixed",
    "Oil – 100 ml",
    "Salt – to taste"
  ],
  method: [
    "Sauté masala and vegetables.",
    "Add rice and water.",
    "Cook till aromatic."
  ]
},

jowar_bhakri: {
  display: "Jowar Bhakri",
  ingredients: [
    "Jowar flour – 1 kg",
    "Hot water – as required",
    "Salt – optional"
  ],
  method: [
    "Knead flour with hot water.",
    "Pat bhakri by hand.",
    "Roast on flame.",
    "Serve with ghee."
  ]
},

/* ---------- SWEETS ---------- */

puranpoli: {
  display: "Puran Poli",
  ingredients: [
    "Chana dal – 500 g",
    "Jaggery – 500 g",
    "Wheat flour – 500 g",
    "Nutmeg & cardamom"
  ],
  method: [
    "Cook dal till soft.",
    "Mix jaggery and spices.",
    "Prepare dough.",
    "Stuff and roll poli.",
    "Cook on tawa."
  ]
},

basundi: {
  display: "Basundi",
  ingredients: [
    "Milk – 2 litres",
    "Sugar – 200 g",
    "Cardamom – 5 g",
    "Nuts – garnish"
  ],
  method: [
    "Boil milk till thick.",
    "Add sugar and cardamom.",
    "Reduce slowly.",
    "Serve chilled or warm."
  ]
},

ukadicha_modak: {
  display: "Ukadiche Modak",
  ingredients: [
    "Rice flour – 500 g",
    "Coconut – 400 g",
    "Jaggery – 300 g",
    "Ghee – few drops"
  ],
  method: [
    "Prepare coconut-jaggery filling.",
    "Make rice dough.",
    "Shape modaks.",
    "Steam till cooked."
  ]
},

/* ---------- BALGOPAL ---------- */

balgopal_thali: {
  display: "Balgopal Thali",
  ingredients: [
    "Rice",
    "Varan",
    "Batata bhaji",
    "Puranpoli / Shrikhand"
  ],
  method: [
    "Prepare all items mild.",
    "Serve balanced portions.",
    "Ensure low spice."
  ]
},

balgopal_vada_pav: {
  display: "Balgopal Vada Pav",
  ingredients: [
    "Mini pav",
    "Mild batata vada"
  ],
  method: [
    "Prepare vada without excess spice.",
    "Serve in mini pav.",
    "No chutney heat."
  ]
}

});
/* ===================== SET 4 — FESTIVAL + THALI-WISE RECIPES ===================== */
window.RECIPE_DB = window.RECIPE_DB || {};
window.THALI_DB  = window.THALI_DB  || {};

Object.assign(window.RECIPE_DB, {

/* ---------- FESTIVAL SPECIALS ---------- */

shrikhand: {
  display: "Shrikhand",
  ingredients: [
    "Hung curd – 1 kg",
    "Sugar – 250 g",
    "Cardamom powder – 5 g",
    "Saffron – optional",
    "Nuts – garnish"
  ],
  method: [
    "Prepare thick hung curd (no water).",
    "Whisk with sugar until smooth.",
    "Add cardamom (and saffron if using).",
    "Chill 2–3 hours.",
    "Garnish with nuts and serve."
  ]
},

aamrakhand: {
  display: "Amrakhand",
  ingredients: [
    "Hung curd – 1 kg",
    "Mango pulp – 300 g",
    "Sugar – 150 g (adjust to mango sweetness)",
    "Cardamom powder – 5 g"
  ],
  method: [
    "Whisk hung curd and sugar until smooth.",
    "Fold in mango pulp and cardamom.",
    "Chill well.",
    "Serve cold."
  ]
},

sabudana_khichdi: {
  display: "Sabudana Khichdi (Upvas)",
  ingredients: [
    "Sabudana – 1 kg (soaked)",
    "Peanuts – 250 g (crushed)",
    "Potato – 500 g (cubes)",
    "Green chillies – 20 g",
    "Cumin – 10 g",
    "Ghee – 120 g",
    "Salt (sendha) – to taste",
    "Lemon & coriander"
  ],
  method: [
    "Soak sabudana till soft, drain well.",
    "Heat ghee, add cumin and chillies.",
    "Add potatoes, cook till done.",
    "Add peanuts, then sabudana and salt.",
    "Toss gently on low flame 5–7 minutes.",
    "Finish with lemon and coriander."
  ]
},

sabudana_vada: {
  display: "Sabudana Vada (Upvas)",
  ingredients: [
    "Soaked sabudana – 1 kg",
    "Boiled potato – 700 g",
    "Crushed peanuts – 300 g",
    "Green chilli – 20 g",
    "Cumin – 10 g",
    "Salt (sendha) – to taste",
    "Oil – for frying"
  ],
  method: [
    "Mix all ingredients into firm mixture.",
    "Shape vadas.",
    "Deep fry on medium heat until crisp.",
    "Serve with upvas chutney."
  ]
},

rajgira_thalipeeth: {
  display: "Rajgira Thalipeeth (Upvas)",
  ingredients: [
    "Rajgira flour – 500 g",
    "Boiled potato – 400 g",
    "Green chilli – 15 g",
    "Cumin – 10 g",
    "Salt (sendha) – to taste",
    "Ghee/oil – for roasting"
  ],
  method: [
    "Mix flour with potato and spices.",
    "Make soft dough (use little water).",
    "Pat on banana leaf/plastic.",
    "Roast both sides with ghee.",
    "Serve hot."
  ]
},

tilgul_ladoo: {
  display: "Tilgul Ladoo (Makar Sankranti)",
  ingredients: [
    "Sesame (til) – 500 g (roasted)",
    "Jaggery – 500 g",
    "Ghee – 50 g",
    "Cardamom – 5 g"
  ],
  method: [
    "Roast sesame lightly and cool.",
    "Melt jaggery with ghee to soft-ball stage.",
    "Mix sesame and cardamom quickly.",
    "Shape ladoos while warm."
  ]
},

gajar_halwa: {
  display: "Gajar Halwa",
  ingredients: [
    "Carrot – 2 kg (grated)",
    "Milk – 2 litres",
    "Sugar – 400 g",
    "Ghee – 150 g",
    "Cardamom – 5 g",
    "Nuts – garnish"
  ],
  method: [
    "Cook carrots in ghee 8–10 minutes.",
    "Add milk, simmer till reduced.",
    "Add sugar, cook till thick.",
    "Finish with cardamom and nuts."
  ]
},

sheera: {
  display: "Sheera (Sooji Halwa)",
  ingredients: [
    "Sooji – 500 g",
    "Ghee – 200 g",
    "Sugar – 350 g",
    "Water/milk – 1.2 litres",
    "Cardamom – 5 g",
    "Nuts – garnish"
  ],
  method: [
    "Roast sooji in ghee till aromatic.",
    "Boil water/milk with sugar.",
    "Add liquid to sooji carefully, stir.",
    "Cook till glossy and soft.",
    "Add cardamom and garnish."
  ]
},

piyush: {
  display: "Piyush (Shikran Style)",
  ingredients: [
    "Thick curd – 1 litre",
    "Milk – 500 ml",
    "Sugar – 200 g",
    "Cardamom – 5 g",
    "Nutmeg – pinch (optional)"
  ],
  method: [
    "Whisk curd smooth.",
    "Add milk, sugar, spices.",
    "Chill and serve."
  ]
},

solkadhi: {
  display: "Solkadhi",
  ingredients: [
    "Kokum – 80 g",
    "Coconut milk – 1 litre",
    "Garlic – 20 g (crushed)",
    "Green chilli – optional",
    "Salt – to taste",
    "Coriander"
  ],
  method: [
    "Soak kokum in warm water, extract juice.",
    "Mix with coconut milk.",
    "Add garlic, salt, coriander.",
    "Chill and serve."
  ]
},

/* ---------- THALI COMPONENTS (common) ---------- */

varan: {
  display: "Varan (Simple Dal)",
  ingredients: [
    "Toor dal – 1 kg",
    "Turmeric – 10 g",
    "Salt – to taste",
    "Ghee – 50 g",
    "Jeera – 10 g"
  ],
  method: [
    "Pressure cook toor dal with turmeric.",
    "Whisk smooth, add salt and water.",
    "Temper ghee + jeera.",
    "Simmer 5 minutes."
  ]
},

batata_bhaji: {
  display: "Batata Bhaji (Mild)",
  ingredients: [
    "Potato – 2 kg",
    "Mustard – 10 g",
    "Turmeric – 10 g",
    "Green chilli – 10 g (optional mild)",
    "Oil – 100 ml",
    "Salt – to taste"
  ],
  method: [
    "Boil and cube potatoes.",
    "Temper mustard + turmeric.",
    "Add potatoes and salt.",
    "Toss gently, finish with coriander."
  ]
},

thecha: {
  display: "Thecha",
  ingredients: [
    "Green chilli – 200 g",
    "Garlic – 60 g",
    "Peanuts – 150 g (optional)",
    "Salt – to taste",
    "Oil – 50 ml"
  ],
  method: [
    "Roast chillies and garlic lightly.",
    "Crush coarsely (not paste).",
    "Add salt and roasted peanuts (optional).",
    "Finish with hot oil."
  ]
},

kothimbir_vadi: {
  display: "Kothimbir Vadi",
  ingredients: [
    "Coriander – 800 g (chopped)",
    "Besan – 500 g",
    "Spices – (turmeric, chilli, salt)",
    "Oil – for frying",
    "Sesame – optional"
  ],
  method: [
    "Mix coriander with besan and spices.",
    "Steam mixture in tray 12–15 minutes.",
    "Cut pieces and shallow/deep fry.",
    "Serve hot with chutney."
  ]
},

alu_vadi: {
  display: "Alu Vadi (Patra)",
  ingredients: [
    "Colocasia leaves – 25–30 pcs",
    "Besan – 700 g",
    "Tamarind-jaggery – balance",
    "Spices – (turmeric, chilli, salt)",
    "Oil + mustard + sesame – tempering"
  ],
  method: [
    "Make thick besan paste with tamarind-jaggery and spices.",
    "Apply on leaves, stack and roll tight.",
    "Steam 20–25 minutes, cool, slice.",
    "Temper with mustard-sesame and serve."
  ]
},

bharli_vangi: {
  display: "Bharli Vangi",
  ingredients: [
    "Small brinjal – 1.5 kg",
    "Peanut + sesame powder – 350 g",
    "Goda masala – 40 g",
    "Jaggery – 50 g",
    "Tamarind – 40 g",
    "Oil – 150 ml",
    "Salt – to taste"
  ],
  method: [
    "Make stuffing mix with masala, jaggery, tamarind.",
    "Cut brinjals and stuff.",
    "Cook in oil on low flame with little water.",
    "Cook till tender, thick gravy."
  ]
}

});


/* ===================== THALI-WISE SETS ===================== */
Object.assign(window.THALI_DB, {

classic_maharashtrian_thali: {
  display: "Classic Maharashtrian Thali",
  items: [
    "kanda_pohe",          // optional starter (if serving breakfast style)
    "varan",
    "steam_rice",
    "batata_bhaji",
    "jowar_bhakri",
    "thecha",
    "solkadhi",
    "puranpoli"
  ],
  notes: [
    "Keep spice balanced.",
    "Add lemon, pickle, papad as per availability."
  ]
},

upvas_thali: {
  display: "Upvas (Fasting) Thali",
  items: [
    "sabudana_khichdi",
    "sabudana_vada",
    "rajgira_thalipeeth",
    "solkadhi"
  ],
  notes: [
    "Use sendha namak only.",
    "No onion/garlic as per upvas rule."
  ]
},

misal_combo: {
  display: "Misal Combo",
  items: [
    "misal",
    "tarri_pohe"
  ],
  notes: [
    "Serve with pav/farsan/onion.",
    "Tarri level: mild/medium/spicy option."
  ]
},

festival_sweet_platter: {
  display: "Festival Sweet Platter",
  items: [
    "tilgul_ladoo",
    "shrikhand",
    "basundi",
    "sheera",
    "gajar_halwa"
  ],
  notes: [
    "Use chilled items cold chain.",
    "Label allergens: dairy, nuts."
  ]
},

balgopal_thali_set: {
  display: "Balgopal Special Set",
  items: [
    "balgopal_thali",
    "balgopal_vada_pav",
    "shrikhand"
  ],
  notes: [
    "Mild spice only.",
    "Offer star reward sticker for kids."
  ]
}

});
/* ===================== SET 5 — BHOJAN GURU (Dish → Mood/Occasion/Season + Combos) ===================== */
window.BHOJAN_GURU = window.BHOJAN_GURU || {};

Object.assign(window.BHOJAN_GURU, {

  /* ---------- QUICK SNACKS / STREET ---------- */
  vada_pav: {
    display: "Vada Pav",
    mood: ["comfort", "quick bite", "nostalgic"],
    occasion: ["snack", "evening chai", "travel"],
    season: ["all", "monsoon"],
    spice: "medium",
    best_with: ["masala_tea", "ginger_tea", "solkadhi"],
    combo: [
      { name: "Vada Pav + Cutting Chai", items: ["vada_pav", "simple_tea"] },
      { name: "Vada Pav + Solkadhi Cooldown", items: ["vada_pav", "solkadhi"] }
    ],
    upsell: ["batata_vada_4pcs", "kothimbir_vadi", "sheera"],
    tags: ["bestseller", "street-food", "kids-fav"]
  },

  misal_pav: {
    display: "Misal Pav",
    mood: ["power", "spicy kick", "weekend vibe"],
    occasion: ["brunch", "breakfast", "party starter"],
    season: ["monsoon", "winter", "all"],
    spice: "spicy",
    best_with: ["buttermilk", "solkadhi"],
    combo: [
      { name: "Misal Pav + Cool Drink", items: ["misal_pav", "solkadhi"] },
      { name: "Misal Pav + Sweet Finish", items: ["misal_pav", "puranpoli"] }
    ],
    upsell: ["kanda_bhaji", "dahi_bhat", "shrikhand"],
    tags: ["bestseller", "spicy", "mumbai-style"]
  },

  kanda_bhaji: {
    display: "Kanda Bhaji",
    mood: ["crunchy", "chai-time", "monsoon love"],
    occasion: ["snack", "starter"],
    season: ["monsoon", "winter"],
    spice: "mild",
    best_with: ["masala_tea", "ginger_tea"],
    combo: [
      { name: "Bhaji + Chai", items: ["kanda_bhaji", "masala_tea"] }
    ],
    upsell: ["vada_pav", "thecha", "solkadhi"],
    tags: ["crispy", "monsoon-special"]
  },

  /* ---------- THALI / MEALS ---------- */
  purnabramha_special_thali: {
    display: "Purnabramha Special Thali",
    mood: ["royal", "satisfying", "full meal"],
    occasion: ["lunch", "dinner", "family"],
    season: ["all"],
    spice: "balanced",
    best_with: ["solkadhi", "piyush"],
    combo: [
      { name: "Thali + Solkadhi", items: ["purnabramha_special_thali", "solkadhi"] },
      { name: "Thali + Sweet", items: ["purnabramha_special_thali", "puranpoli"] }
    ],
    upsell: ["ukadicha_modak", "shrikhand", "piyush"],
    tags: ["signature", "premium", "family-fav"]
  },

  masale_bhat: {
    display: "Masale Bhat",
    mood: ["warming", "homestyle", "simple joy"],
    occasion: ["lunch", "tiffin", "corporate"],
    season: ["winter", "monsoon", "all"],
    spice: "mild",
    best_with: ["kadhi", "raita", "solkadhi"],
    combo: [
      { name: "Masale Bhat + Kadhi", items: ["masale_bhat", "kadhi"] },
      { name: "Masale Bhat + Curd Bowl", items: ["masale_bhat", "dahi"] }
    ],
    upsell: ["kothimbir_vadi", "batata_bhaji", "piyush"],
    tags: ["tiffin-friendly", "comfort"]
  },

  kadhi: {
    display: "Kadhi",
    mood: ["light", "soothing", "digestion-friendly"],
    occasion: ["lunch", "post-travel", "family meal"],
    season: ["summer", "all"],
    spice: "mild",
    best_with: ["steam_rice", "masale_bhat"],
    combo: [
      { name: "Kadhi-Chawal Comfort", items: ["kadhi", "steam_rice"] }
    ],
    upsell: ["papad", "pickle", "ghee"],
    tags: ["light", "classic"]
  },

  dahi_bhat: {
    display: "Dahi Bhat",
    mood: ["cooling", "calm", "simple"],
    occasion: ["lunch", "summer special", "kid-friendly"],
    season: ["summer", "all"],
    spice: "very mild",
    best_with: ["masala_mirchi", "pickle", "papad"],
    combo: [
      { name: "Dahi Bhat + Crunch", items: ["dahi_bhat", "papad"] }
    ],
    upsell: ["masale_bhat", "kadhi", "gajar_koshimbir"],
    tags: ["kids-fav", "cooling"]
  },

  /* ---------- SWEETS ---------- */
  ukadicha_modak: {
    display: "Ukadicha Modak",
    mood: ["festive", "devotional", "celebration"],
    occasion: ["festival", "party dessert", "gift"],
    season: ["festival", "all"],
    spice: "sweet",
    best_with: ["piyush", "warm milk"],
    combo: [
      { name: "Modak + Piyush", items: ["ukadicha_modak", "piyush"] }
    ],
    upsell: ["shrikhand", "sheera", "basundi"],
    tags: ["festival-special", "premium", "bestseller"]
  },

  puranpoli: {
    display: "Puran Poli",
    mood: ["warm", "classic", "family nostalgia"],
    occasion: ["thali dessert", "festival", "guest treat"],
    season: ["winter", "festival", "all"],
    spice: "sweet",
    best_with: ["warm ghee", "milk", "piyush"],
    combo: [
      { name: "Puran Poli + Ghee", items: ["puranpoli", "ghee"] },
      { name: "Puran Poli + Piyush", items: ["puranpoli", "piyush"] }
    ],
    upsell: ["shrikhand", "basundi", "gajar_halwa"],
    tags: ["classic", "bestseller"]
  },

  shrikhand: {
    display: "Shrikhand",
    mood: ["cooling", "celebration", "refreshing"],
    occasion: ["dessert", "party", "thali finish"],
    season: ["summer", "all"],
    spice: "sweet",
    best_with: ["puri", "thali", "fruit"],
    combo: [
      { name: "Shrikhand + Puri", items: ["shrikhand", "puri"] }
    ],
    upsell: ["aamrakhand", "basundi", "tilgul_ladoo"],
    tags: ["summer-hit", "premium"]
  },

  /* ---------- UPVAS ---------- */
  sabudana_khichdi: {
    display: "Sabudana Khichdi",
    mood: ["light energy", "fasting comfort", "clean food"],
    occasion: ["upvas", "breakfast", "light lunch"],
    season: ["all"],
    spice: "mild",
    best_with: ["upvas_chutney", "curd", "solkadhi"],
    combo: [
      { name: "Upvas Comfort Combo", items: ["sabudana_khichdi", "solkadhi"] }
    ],
    upsell: ["sabudana_vada", "rajgira_thalipeeth"],
    tags: ["upvas", "gluten-free"]
  },

  sabudana_vada: {
    display: "Sabudana Vada",
    mood: ["crispy", "fasting treat", "snack"],
    occasion: ["upvas", "starter", "evening snack"],
    season: ["all"],
    spice: "mild",
    best_with: ["upvas_chutney", "curd"],
    combo: [
      { name: "Upvas Crunch Combo", items: ["sabudana_vada", "sabudana_khichdi"] }
    ],
    upsell: ["solkadhi", "rajgira_thalipeeth"],
    tags: ["upvas", "crispy"]
  },

  /* ---------- BALGOPAL / KIDS ---------- */
  balgopal_thali: {
    display: "Balgopal Thali",
    mood: ["happy", "safe", "comfort"],
    occasion: ["kids meal", "family outing", "school holiday"],
    season: ["all"],
    spice: "very mild",
    best_with: ["lassi", "piyush", "shrikhand"],
    combo: [
      { name: "Balgopal Hero Combo", items: ["balgopal_thali", "shrikhand"] }
    ],
    upsell: ["vada_pav", "sheera"],
    tags: ["kids-fav", "mild", "star-reward"]
  }

});


/* Optional helper: get suggestions by mood / occasion / season */
window.getBhojanSuggestions = function({ mood=null, occasion=null, season=null } = {}) {
  const db = window.BHOJAN_GURU || {};
  return Object.keys(db)
    .map(k => ({ key:k, ...db[k] }))
    .filter(x => {
      const okMood = !mood || (x.mood || []).includes(mood);
      const okOcc  = !occasion || (x.occasion || []).includes(occasion);
      const okSea  = !season || (x.season || []).includes(season) || (x.season || []).includes("all");
      return okMood && okOcc && okSea;
    });
};
/* ===================== SET 6 — AUTO COMBO ENGINE (Uses MENU + RECIPE_DB + BHOJAN_GURU) ===================== */
/*
What this gives you:
1) findMenuItemByName(name)  -> returns {sectionIndex, itemIndex, row, section}
2) normalizeKey(name)        -> makes stable key like "vada_pav"
3) buildAutoCombosForItem(name, opts) -> returns array of combo cards (ready for UI)
4) buildAutoCombosForCart(cartNames, opts) -> cart-level suggestions (cooldown drink, sweet finish, etc.)
5) price helpers (AUS/IND) and safe fallbacks

Assumptions about MENU row format (same as your earlier code):
["Name","Desc", priceAUS, stars, img, badge1, badge2, ...]
- If your indices differ, change IDX below.
*/

window.AUTO_COMBOS = window.AUTO_COMBOS || {};

(function(){

  /* ====== CONFIG ====== */
  const IDX = {
    NAME: 0,
    DESC: 1,
    PRICE_AUS: 2,
    STARS: 3,
    IMG: 4,
    // If you have Perth/India split pricing elsewhere, we keep safe fallback.
    PRICE_IND: 9 // <— if you do not have it, it will ignore & fallback
  };

  const STOP_WORDS = new Set([
    "the","and","&","with","without","special","classic","style","pb","purnabramha",
    "veg","vegetarian","mini","large","small","pcs","pc","piece","pieces",
    "combo","thali","plate","bowl"
  ]);

  const KEY_ALIASES = {
    "vadapav":"vada_pav",
    "vada-pav":"vada_pav",
    "misal":"misal_pav",
    "misalpav":"misal_pav",
    "kanda bhaji":"kanda_bhaji",
    "ukadiche modak":"ukadicha_modak",
    "modak":"ukadicha_modak",
    "puran poli":"puranpoli",
    "puranpoli":"puranpoli",
    "dahi bhat":"dahi_bhat",
    "masale bhat":"masale_bhat"
  };

  const DRINK_KEYS = new Set(["solkadhi","buttermilk","lassi","piyush","simple_tea","masala_tea","ginger_tea","black_tea"]);
  const SWEET_KEYS = new Set(["ukadicha_modak","puranpoli","shrikhand","sheera","basundi","tilgul_ladoo","gajar_halwa"]);

  /* ====== UTILS ====== */
  function safeStr(x){ return (x==null) ? "" : String(x); }

  function normalizeKey(name){
    let s = safeStr(name).trim().toLowerCase();

    // quick alias match
    if(KEY_ALIASES[s]) return KEY_ALIASES[s];

    // cleanup symbols
    s = s
      .replace(/[\u2019']/g,"")
      .replace(/[^a-z0-9\s-]/g," ")
      .replace(/[-]+/g," ")
      .replace(/\s+/g," ")
      .trim();

    if(KEY_ALIASES[s]) return KEY_ALIASES[s];

    // remove stop words
    const parts = s.split(" ").filter(w => w && !STOP_WORDS.has(w));
    s = parts.join(" ");

    // snake_case
    s = s.replace(/\s+/g,"_");

    // if empty, fallback
    return s || "item";
  }

  function money(n){
    const x = Number(n);
    if(!isFinite(x)) return null;
    return Math.round(x * 100) / 100;
  }

  function getRowPrice(row, region){
    if(!row) return null;
    if(region === "IND"){
      const p = money(row[IDX.PRICE_IND]);
      if(p!=null) return p;
    }
    const p2 = money(row[IDX.PRICE_AUS]);
    return p2!=null ? p2 : null;
  }

  function findMenuItemByName(name){
    const MENU = window.MENU || [];
    const target = safeStr(name).trim().toLowerCase();
    for(let si=0; si<MENU.length; si++){
      const sec = MENU[si];
      const items = (sec && sec.items) ? sec.items : [];
      for(let ii=0; ii<items.length; ii++){
        const row = items[ii];
        const nm = safeStr(row[IDX.NAME]).trim().toLowerCase();
        if(nm === target){
          return { sectionIndex: si, itemIndex: ii, row, section: sec.section };
        }
      }
    }
    // partial / contains match fallback
    for(let si=0; si<MENU.length; si++){
      const sec = MENU[si];
      const items = (sec && sec.items) ? sec.items : [];
      for(let ii=0; ii<items.length; ii++){
        const row = items[ii];
        const nm = safeStr(row[IDX.NAME]).trim().toLowerCase();
        if(nm.includes(target) || target.includes(nm)){
          return { sectionIndex: si, itemIndex: ii, row, section: sec.section };
        }
      }
    }
    return null;
  }

  function findMenuItemByKey(key){
    // try exact key match against normalized menu names
    const MENU = window.MENU || [];
    for(let si=0; si<MENU.length; si++){
      const sec = MENU[si];
      const items = (sec && sec.items) ? sec.items : [];
      for(let ii=0; ii<items.length; ii++){
        const row = items[ii];
        const nm = safeStr(row[IDX.NAME]);
        if(normalizeKey(nm) === key){
          return { sectionIndex: si, itemIndex: ii, row, section: sec.section };
        }
      }
    }
    return null;
  }

  function buildComboCard({ title, reason, items, region="AUS" }){
    // items = array of {name, key, price, img}
    const total = items.reduce((sum,it)=> sum + (money(it.price)||0), 0);
    return {
      title,
      reason,
      items,
      total: money(total),
      currency: (region==="IND") ? "₹" : "$"
    };
  }

  function getItemInfoFromKey(key, region){
    // try Bhojan Guru display then menu
    const BG = window.BHOJAN_GURU || {};
    const display = (BG[key] && BG[key].display) ? BG[key].display : null;

    let found = null;
    if(display) found = findMenuItemByName(display);
    if(!found) found = findMenuItemByKey(key);

    if(found && found.row){
      return {
        key,
        name: safeStr(found.row[IDX.NAME]),
        price: getRowPrice(found.row, region),
        img: found.row[IDX.IMG] || null
      };
    }

    // fallback: unknown item (still show name)
    return {
      key,
      name: display || key.replace(/_/g," "),
      price: null,
      img: null
    };
  }

  function pickFirstExisting(keys, region){
    for(const k of keys){
      const info = getItemInfoFromKey(k, region);
      // consider existing if it exists in menu (price not null OR name matched)
      if(info && info.name && info.name !== k.replace(/_/g," ")){
        return info;
      }
      // if price exists also ok
      if(info && info.price!=null) return info;
    }
    return null;
  }

  /* ====== COMBO GENERATOR ====== */

  function buildAutoCombosForItem(itemName, opts={}){
    const region = opts.region || "AUS"; // "AUS" or "IND"
    const BG = window.BHOJAN_GURU || {};
    const RECIPE = window.RECIPE_DB || {};

    const baseFound = findMenuItemByName(itemName);
    const baseKey = normalizeKey(itemName);
    const bgKey = BG[baseKey] ? baseKey : (BG[normalizeKey(itemName)] ? normalizeKey(itemName) : baseKey);

    const baseInfo = (baseFound && baseFound.row)
      ? { key: baseKey, name: safeStr(baseFound.row[IDX.NAME]), price: getRowPrice(baseFound.row, region), img: baseFound.row[IDX.IMG] || null }
      : { key: baseKey, name: itemName, price: null, img: null };

    const out = [];

    const bg = BG[bgKey] || null;
    const spice = bg?.spice || RECIPE[bgKey]?.spice_level || null;

    // 1) Best with drink (cooldown if spicy)
    if(bg && Array.isArray(bg.best_with) && bg.best_with.length){
      const drink = pickFirstExisting(bg.best_with, region) || getItemInfoFromKey(bg.best_with[0], region);
      if(drink){
        let reason = "A perfect pairing.";
        if(spice && (spice === "spicy" || spice === "high")) reason = "Balances spice and refreshes your palate.";
        if(DRINK_KEYS.has(drink.key)) reason = reason;
        out.push(buildComboCard({
          title: `${baseInfo.name} + ${drink.name}`,
          reason,
          items: [baseInfo, drink],
          region
        }));
      }
    }

    // 2) Sweet finish (if base is spicy or meal)
    const likelyMeal = /thali|bhat|rice|kadhi|usal|dal|bhakri/i.test(baseInfo.name);
    if(spice === "spicy" || likelyMeal){
      const sweetPick = pickFirstExisting(["ukadicha_modak","puranpoli","shrikhand","sheera"], region);
      if(sweetPick){
        out.push(buildComboCard({
          title: `${baseInfo.name} + Sweet Finish`,
          reason: "End your meal the Maharashtrian way—sweet, soothing, satisfying.",
          items: [baseInfo, sweetPick],
          region
        }));
      }
    }

    // 3) Upsell trio (top 2 upsells + base)
    if(bg && Array.isArray(bg.upsell) && bg.upsell.length){
      const picks = [];
      for(const k of bg.upsell){
        const info = getItemInfoFromKey(k, region);
        // accept if name exists
        if(info && info.name){
          // avoid duplicate-ish
          if(!picks.find(p=>p.key===info.key)) picks.push(info);
        }
        if(picks.length >= 2) break;
      }
      if(picks.length){
        out.push(buildComboCard({
          title: `Make it a Mini Feast`,
          reason: "Popular add-ons people love with this item.",
          items: [baseInfo, ...picks],
          region
        }));
      }
    }

    // 4) Occasion-based combo from Bhojan Guru presets (if present)
    if(bg && Array.isArray(bg.combo) && bg.combo.length){
      for(const c of bg.combo.slice(0,2)){
        const itemInfos = (c.items || []).map(k => getItemInfoFromKey(k, region)).filter(Boolean);
        // ensure base included
        const hasBase = itemInfos.some(x => normalizeKey(x.name) === baseKey || x.key === baseKey);
        const merged = hasBase ? itemInfos : [baseInfo, ...itemInfos];
        out.push(buildComboCard({
          title: c.name || "Recommended Combo",
          reason: "Chef-recommended combination.",
          items: merged,
          region
        }));
      }
    }

    // De-duplicate combos by title
    const seen = new Set();
    return out.filter(c => {
      const t = (c.title || "").toLowerCase();
      if(seen.has(t)) return false;
      seen.add(t);
      return true;
    });
  }

  function buildAutoCombosForCart(cartNames=[], opts={}){
    const region = opts.region || "AUS";
    const BG = window.BHOJAN_GURU || {};
    const RECIPE = window.RECIPE_DB || {};

    const keys = cartNames.map(n => normalizeKey(n));
    const hasSpicy = keys.some(k => {
      const s = BG[k]?.spice || RECIPE[k]?.spice_level || "";
      return String(s).toLowerCase().includes("spicy") || String(s).toLowerCase().includes("high");
    });

    const hasDrink = keys.some(k => DRINK_KEYS.has(k));
    const hasSweet = keys.some(k => SWEET_KEYS.has(k));

    const suggestions = [];

    // Cooldown drink suggestion
    if(hasSpicy && !hasDrink){
      const drink = pickFirstExisting(["solkadhi","buttermilk","lassi"], region);
      if(drink){
        suggestions.push(buildComboCard({
          title: "Add a Cooldown Drink",
          reason: "Your cart has spicy items—this will balance the heat.",
          items: [drink],
          region
        }));
      }
    }

    // Sweet finish suggestion
    const mealLike = cartNames.some(n => /thali|bhat|rice|kadhi|usal|dal|bhakri/i.test(n));
    if((mealLike || cartNames.length >= 2) && !hasSweet){
      const sweet = pickFirstExisting(["puranpoli","ukadicha_modak","shrikhand","sheera"], region);
      if(sweet){
        suggestions.push(buildComboCard({
          title: "Sweet Finish?",
          reason: "A classic ending for a complete Maharashtrian meal.",
          items: [sweet],
          region
        }));
      }
    }

    // Party starter suggestion (add crunchy snack)
    const hasSnack = cartNames.some(n => /vada|bhaji|vadi|pakoda|pav/i.test(n));
    if(!hasSnack){
      const crunchy = pickFirstExisting(["kanda_bhaji","kothimbir_vadi","batata_vada_4pcs"], region);
      if(crunchy){
        suggestions.push(buildComboCard({
          title: "Add a Crunchy Starter",
          reason: "Great for sharing while you wait for the main meal.",
          items: [crunchy],
          region
        }));
      }
    }

    // De-dup
    const seen = new Set();
    return suggestions.filter(s => {
      const t = (s.title || "").toLowerCase();
      if(seen.has(t)) return false;
      seen.add(t);
      return true;
    });
  }

  /* ====== EXPORTS ====== */
  window.AUTO_COMBOS.normalizeKey = normalizeKey;
  window.AUTO_COMBOS.findMenuItemByName = findMenuItemByName;
  window.AUTO_COMBOS.buildAutoCombosForItem = buildAutoCombosForItem;
  window.AUTO_COMBOS.buildAutoCombosForCart = buildAutoCombosForCart;

})();

