// Complete Purnabramha Menu Data with AUS and IND pricing
export interface MenuItem {
  id: string;
  name: string;
  description: string;
  priceAUD: number;
  priceINR: number;
  image?: string;
  bestWith?: string;
  category: string;
  section: string;
}

export interface MenuSection {
  id: string;
  name: string;
  items: MenuItem[];
}

// Menu organized by sections
export const menuData: MenuSection[] = [
  {
    id: 'balgopal',
    name: 'Balgopal (Kids Menu)',
    items: [
      {
        id: 'bg_shrikhand_puri',
        name: 'BG Shrikhanda Puri Bhaji',
        description: 'Sweet yoghurt dessert served with puris and spiced potato curry',
        priceAUD: 15.99,
        priceINR: 219,
        category: 'balgopal',
        section: 'Heavy Brunch'
      },
      {
        id: 'bg_misal_pav',
        name: 'BG Misal Pav',
        description: 'Spicy mixed lentil curry topped with farsan, served with soft bread rolls',
        priceAUD: 12.99,
        priceINR: 189,
        category: 'balgopal',
        section: 'Heavy Brunch'
      },
      {
        id: 'bg_mungdal_khichadi',
        name: 'BG MungDal Khichadi',
        description: 'Soft, comforting khichadi made with mung dal and rice',
        priceAUD: 8.99,
        priceINR: 199,
        category: 'balgopal',
        section: 'Heavy Brunch'
      },
      {
        id: 'bg_sabudana_khichadi',
        name: 'BG Sabudana Khichadi',
        description: 'Sago pearls cooked with potatoes and peanuts - perfect for kids',
        priceAUD: 12.99,
        priceINR: 189,
        category: 'balgopal',
        section: 'Heavy Brunch'
      },
      {
        id: 'bg_aloo_paratha',
        name: 'BG Aloocha Paratha',
        description: 'Soft flatbread stuffed with seasoned mashed potatoes',
        priceAUD: 7.99,
        priceINR: 189,
        category: 'balgopal',
        section: 'Heavy Brunch'
      },
      {
        id: 'bg_vada_pav',
        name: 'BG Vada Pav',
        description: 'Spiced potato fritter in soft bun - kids favorite',
        priceAUD: 3.99,
        priceINR: 45,
        category: 'balgopal',
        section: 'Snacks'
      },
      {
        id: 'bg_sabudana_vada',
        name: 'BG Sabudana Vada (4 pcs)',
        description: 'Crispy sago and potato patties',
        priceAUD: 12.99,
        priceINR: 199,
        category: 'balgopal',
        section: 'Snacks'
      },
      {
        id: 'bg_kanda_pohe',
        name: 'BG Kanda Pohe',
        description: 'Flaked rice cooked with onions and mild spices',
        priceAUD: 7.99,
        priceINR: 129,
        category: 'balgopal',
        section: 'Snacks'
      },
      {
        id: 'bg_tedamedha_aloo',
        name: 'BG Tedamedha Aloo',
        description: 'Crispy fried potato snack for kids',
        priceAUD: 5.99,
        priceINR: 129,
        category: 'balgopal',
        section: 'Snacks'
      },
      {
        id: 'bg_thali',
        name: 'Balgopal Thali',
        description: 'Complete kids meal with dal, rice, roti, sabji and sweet',
        priceAUD: 29.99,
        priceINR: 399,
        category: 'balgopal',
        section: 'Lunch'
      },
      {
        id: 'bg_varan_fal',
        name: 'Balgopal Varan Fal',
        description: 'Small wheat dumplings in lentil curry - comfort food',
        priceAUD: 13.99,
        priceINR: 199,
        category: 'balgopal',
        section: 'Lunch'
      },
      {
        id: 'bg_tup_varan_bhat',
        name: 'Balgopal Tup Varan Bhat',
        description: 'Rice with lentil curry and ghee',
        priceAUD: 9.99,
        priceINR: 149,
        category: 'balgopal',
        section: 'Lunch'
      },
      {
        id: 'bg_puranpoli',
        name: 'Balgopal Puranpoli',
        description: 'Sweet lentil-stuffed flatbread',
        priceAUD: 9.99,
        priceINR: 149,
        category: 'balgopal',
        section: 'Sweet'
      },
      {
        id: 'bg_shrikhanda',
        name: 'Balgopal Shrikhanda',
        description: 'Creamy sweetened yogurt with saffron',
        priceAUD: 9.99,
        priceINR: 199,
        category: 'balgopal',
        section: 'Sweet'
      },
      {
        id: 'bg_khova_poli',
        name: 'Balgopal Khova Poli',
        description: 'Flatbread stuffed with sweet milk solids',
        priceAUD: 10.99,
        priceINR: 149,
        category: 'balgopal',
        section: 'Sweet'
      }
    ]
  },
  {
    id: 'snacks',
    name: 'Snacks',
    items: [
      {
        id: 'kanda_bhaji',
        name: 'Kanda Bhaji (20 pcs)',
        description: 'Crispy onion fritters served hot with tamarind chutney — a monsoon classic',
        priceAUD: 12.99,
        priceINR: 649,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'maaswadi',
        name: 'Maaswadi (4 pcs)',
        description: 'Gram flour rolls filled with spicy coconut and peanut mix, served with curry',
        priceAUD: 19.99,
        priceINR: 999,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'sabudana_vada',
        name: 'Sabudana Vada (4 pcs)',
        description: 'Traditional deep fried snack from Maharashtra',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'snacks_platter',
        name: 'Snacks Platter',
        description: 'Perfect for families who wish to explore variety of snacks together',
        priceAUD: 42.99,
        priceINR: 2149,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'batate_vada',
        name: 'Batate Vada (4 pcs)',
        description: 'Classic potato fritters seasoned with spices and fried until golden brown',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'kachori',
        name: 'Kachori (6 pcs)',
        description: 'Deep-fried pastry pockets filled with spiced green peas — crunchy and flavourful',
        priceAUD: 16.99,
        priceINR: 849,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'vada_pav',
        name: 'Vada Pav',
        description: 'Spiced potato fritter served in soft bun with tangy chutney and fried green chilli',
        priceAUD: 4.99,
        priceINR: 249,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'kanda_pohe',
        name: 'Kanda Pohe',
        description: 'Flaked rice cooked with onions, peanuts, mustard seeds, curry leaves, and mild spices',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'tarri_pohe',
        name: 'Tarri Pohe',
        description: 'Flaked rice in spicy curry gravy',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'dadpe_pohe',
        name: 'Dadpe Pohe',
        description: 'Flattened rice mixed with fresh coconut, yoghurt, and mild spices — refreshing cold snack',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'alu_vadi',
        name: 'Alu Vadi (8 pcs)',
        description: 'Savory roll of taro leaves, spiced to perfection for a delectable Maharashtrian treat',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'pudachi_vadi',
        name: 'Pudachi Vadi (10 pcs)',
        description: 'Crispy gram flour rolls stuffed with coconut, coriander, and spices',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'kothimbir_vadi',
        name: 'Kothimbir Vadi (10 pcs)',
        description: 'Coriander and gram flour cakes steamed, then lightly pan-fried for crunchy texture',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'vada_sambar',
        name: 'Vada Sample',
        description: 'Potato fritters served with spicy curry, chopped onion, and crunchy sev',
        priceAUD: 10.99,
        priceINR: 549,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'bread_pakoda',
        name: 'Bread Pakoda',
        description: 'Bread stuffed with spiced potato mash, dipped in gram flour batter, and fried golden',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'masala_bread_pakoda',
        name: 'Masala Bread Pakoda',
        description: 'Spiced version of bread fritters stuffed with seasoned potato mix',
        priceAUD: 10.99,
        priceINR: 549,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'ukad',
        name: 'Ukad',
        description: 'Fodanichi Ukad steamed, spiced, and sublime, a Maharashtrian snack',
        priceAUD: 10.99,
        priceINR: 549,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'kaccha_chiwada',
        name: 'Kaccha Chiwada',
        description: 'Light poha snack mixed with onions, tomatoes, and fresh chillies',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'papad_bowl',
        name: 'Papad Bowl',
        description: 'Seasonal papads in a symphony of crunch and zest',
        priceAUD: 9.99,
        priceINR: 499,
        category: 'snacks',
        section: 'Snacks'
      },
      {
        id: 'mataki_bhel',
        name: 'Mataki Bhel',
        description: 'Sprouted lentil salad mixed with chutneys, spices, and crispy toppings',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'snacks',
        section: 'Snacks'
      }
    ]
  },
  {
    id: 'heavy_brunch',
    name: 'Heavy Brunch',
    items: [
      {
        id: 'thalipith',
        name: 'Thalipith (2 pc)',
        description: 'Multigrain savoury pancakes made with spiced flour mix, served with yoghurt or chutney',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'ghavan',
        name: 'Ghavan (3 pc)',
        description: 'Thin rice flour pan cake from the Konkan region of Maharashtra',
        priceAUD: 12.99,
        priceINR: 649,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'dhirde',
        name: 'Dhirde (3 pc)',
        description: 'Thin, soft pancakes made from wheat and gram flour, flavoured with garlic and curd',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'misal_pav',
        name: 'Misal Pav',
        description: 'Spicy mixed lentil curry topped with farsan, served with soft bread rolls',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'ukarpendi',
        name: 'Ukarpendi',
        description: 'Savoury wheat flour upma cooked with curd and onion — soft and filling',
        priceAUD: 9.99,
        priceINR: 499,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'shrikhand_puri_bhaji',
        name: 'Shrikhanada Puri Bhaji',
        description: 'Sweet yoghurt dessert served with puris and spiced potato curry',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'aloo_paratha',
        name: 'Aloocha Paratha (1 pc)',
        description: 'Soft flatbread stuffed with seasoned mashed potatoes — served with pickle and curd',
        priceAUD: 7.99,
        priceINR: 399,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'varan_fal',
        name: 'Varan Fal',
        description: 'Small wheat dumplings cooked in rich yellow lentil curry, a comforting homestyle dish',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'puri_bhaji',
        name: 'Puri Bhaji',
        description: 'Deep-fried bread served with dry spiced potato curry',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'shengole',
        name: 'Shengole',
        description: 'Spicy gram and wheat flour rings cooked in curry, served hot',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      },
      {
        id: 'masala_varan_fal',
        name: 'Masala Varan Fal',
        description: 'Small wheat SPICY STUFFED dumplings cooked in rich yellow lentil curry',
        priceAUD: 22.99,
        priceINR: 1149,
        category: 'heavy_brunch',
        section: 'Heavy Brunch'
      }
    ]
  },
  {
    id: 'main_course',
    name: 'Main Course',
    items: [
      {
        id: 'ravan_pithala',
        name: 'Ravan Pithala',
        description: 'Extra spicy version of gram flour curry good with bhakar, curd, and chutney',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'pithala_yellow',
        name: 'Pithala (Yellow)',
        description: 'Thick gram flour curry — comforting and mildly spiced',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'bharit',
        name: 'Bharit (Saturdays)',
        description: 'Brinjal bharit is one of the most authentic recipes of Purnabramha',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'dal_vanga',
        name: 'Dal Vanga',
        description: 'Brinjal prep with Tur dal and spices served with three fulkas',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'mix_cauliflower_bhaji',
        name: 'Mix Cauliflower Bhaji',
        description: 'Mix Vegetable just like homemade preparation',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'chef_special_bhaji',
        name: 'Chef Special Bhaji',
        description: 'The best of all, our chef special Bhaji served in three different spice levels',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'shev_bhaji',
        name: 'Shev Bhaji',
        description: 'Crunchy chickpea noodles in a rich curry',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'patodi_rassa',
        name: 'Patodi Rassa',
        description: 'Gram flour rolls in spicy curry good with bhakar and chilli paste',
        priceAUD: 24.99,
        priceINR: 1249,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'maaswadi_rassa',
        name: 'Maaswadi Rassa',
        description: 'Crispy chickpea noodles cooked in spicy curry — a Maharashtra favourite',
        priceAUD: 24.99,
        priceINR: 1249,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'patal_bhaji',
        name: 'Patal Bhaji (Sundays)',
        description: 'Mixed greens curry made with chana dal and spinach or colocasia leaves',
        priceAUD: 23.99,
        priceINR: 1199,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'mungwadi_rassa',
        name: 'Mungwadi Rassa',
        description: 'Gram flour rolls filled with peanut and spice mixture in tangy red curry',
        priceAUD: 22.99,
        priceINR: 1149,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'bharli_vangi',
        name: 'Bharli Vangi',
        description: 'Stuffed baby eggplants cooked in rich, spiced coconut gravy',
        priceAUD: 24.99,
        priceINR: 1249,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'zhunka',
        name: 'Zhunka',
        description: 'Spiced chickpea flour stir-fry with onions — a traditional rustic dish',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'kaju_curry',
        name: 'Kaju Curry',
        description: 'Cashew and dry fruit curry in creamy, mildly sweet sauce',
        priceAUD: 26.99,
        priceINR: 1349,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'akkha_masur',
        name: 'Akkha Masur',
        description: 'Whole red lentils simmered in black masala gravy — earthy and spicy',
        priceAUD: 22.99,
        priceINR: 1149,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'kadhi_gole',
        name: 'Kadhi Gole',
        description: 'Soothing gram flour balls dipped & cooked in Kadhi. A Non Spicy preparation',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'jeera_aloo',
        name: 'Dry / Jeera Aloo',
        description: 'Potatoes tossed in cumin seeds and mild spices — a simple comfort dish',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'main_course',
        section: 'Bhaji'
      },
      {
        id: 'matki_usal',
        name: 'Matki Usal / Barbati Usal',
        description: 'Sprouted lentils cooked in spicy onion-tomato sauce, garnished with coriander',
        priceAUD: 20.99,
        priceINR: 1049,
        category: 'main_course',
        section: 'Bhaji'
      }
    ]
  },
  {
    id: 'dal',
    name: 'Dal / Varan',
    items: [
      {
        id: 'mataki_amti',
        name: 'Mataki Amti',
        description: 'Spicy sprouted lentil curry in tangy gravy — full of protein',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'lasun_varan',
        name: 'Lasun Varan',
        description: 'Garlic-flavoured lentil curry with green chillies — aromatic and comforting',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'sadha_varan',
        name: 'Sadha Varan',
        description: 'Plain yellow lentil curry with mild tempering of garlic and green chilli',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'takachi_kadhi',
        name: 'Takachi Kadhi',
        description: 'Tangy yoghurt-based curry thickened with gram flour — light and refreshing',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'kataachi_amti',
        name: 'Kataachi Amti',
        description: 'Spicy lentil soup made from chana dal with coconut and special masalas',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'jeera_varan',
        name: 'Jeera Varan',
        description: 'Lentil curry with cumin seasoning — simple and fragrant',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'dal',
        section: 'Dal'
      },
      {
        id: 'chef_special_dal',
        name: 'Chef Special Dal / Fodanicha Varan',
        description: 'Tur dal tempered with garlic and spices — homestyle and mild',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'dal',
        section: 'Dal'
      }
    ]
  },
  {
    id: 'rice',
    name: 'Rice',
    items: [
      {
        id: 'steam_rice',
        name: 'Steam Rice',
        description: 'Steamed rice cooked to perfection — a daily staple',
        priceAUD: 9.99,
        priceINR: 499,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'dahi_bhat',
        name: 'Dahi Bhat',
        description: 'Creamy yoghurt rice with tempered mustard seeds and curry leaves',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'kanda_rice',
        name: 'Kanda Rice',
        description: 'Rice cooked with onions, turmeric, and mild spices',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'tup_bhat',
        name: 'Tup Bhat',
        description: 'Chef special Rice tossed in Desi Ghee, Black Pepper, Cloves and Dry Fruits',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'bhaji_bhat',
        name: 'Bhaji Bhat',
        description: 'Spiced rice cooked with green leafy vegetables — served with kadhi or tamarind sauce',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'gola_bhat',
        name: 'Gola Bhat',
        description: 'Rice served with steamed gram flour dumplings in spicy sauce',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'ravan_bhat',
        name: 'Ravan Bhat',
        description: 'Spicy and tangy rice with a bold flavour kick',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'masale_bhat',
        name: 'Masale Bhat',
        description: 'Spiced rice cooked with vegetables and traditional Maharashtrian masala',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'tup_varan_bhat',
        name: 'Tup Varan Bhat',
        description: 'Fragrant ghee rice with pepper, cloves, and dry fruits',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'khajur_bhat',
        name: 'Khajur Bhat',
        description: 'Our Chef\'s Creation. Rice flavored with Dates and House\'s Secret Spice Mixes',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'rice',
        section: 'Rice'
      },
      {
        id: 'rice_platter',
        name: 'Rice Platter',
        description: 'A selection of assorted rice varieties served as a platter',
        priceAUD: 29.99,
        priceINR: 1499,
        category: 'rice',
        section: 'Rice'
      }
    ]
  },
  {
    id: 'desserts',
    name: 'Desserts',
    items: [
      {
        id: 'modak',
        name: 'Modak',
        description: 'Stuffing made of coconut & jaggery stuffed in rice flour dough and steamed',
        priceAUD: 18.99,
        priceINR: 949,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'shrikhanda',
        name: 'Shrikhanda',
        description: 'Indian sweetmeat made of hung Curd with perfectly blended sugar, cardamom & kesar',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'shirvale',
        name: 'Shirvale',
        description: 'Traditional Marathi recipe from Konkan villages made of rice flour and coconut milk',
        priceAUD: 27.99,
        priceINR: 1399,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'puranpoli',
        name: 'Puranpoli',
        description: 'Sweet lentil-stuffed flatbread - significance during Holi festival',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'khava_poli',
        name: 'Khava Poli',
        description: 'Milk reduced to form Khava used for making variety of Indian sweets',
        priceAUD: 9.99,
        priceINR: 499,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'tilgul_poli',
        name: 'Tilgul Poli',
        description: 'Made of sesame seeds & jaggery with flavour of cardamom & nutmeg',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'kharvas',
        name: 'Kharvas',
        description: 'The first Cow milk pie made in our own godhan shala in Pune',
        priceAUD: 29.99,
        priceINR: 1499,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'amrakhanda',
        name: 'Amrakhanda (Seasonal)',
        description: 'Hung Curd with sugar, cardamom, kesar and Mango flavor',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'sheera_rava',
        name: 'Sheera (Rava)',
        description: 'Simple preparation of Rava (semolina), sugar, khoya and milk',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'basundi',
        name: 'Basundi',
        description: 'Signature recipe of our Chef prepared from reduced milk flavoured with Cardamom',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'shewaya_kheer',
        name: 'Shewaya Kheer',
        description: 'Thin layered spagetti shaped dough boiled in milk and served with dry fruits',
        priceAUD: 13.99,
        priceINR: 699,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'aamras',
        name: 'Aamras (Seasonal)',
        description: 'Sweet dessert made out of mangos',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'chirote',
        name: 'Chirote (6 pcs)',
        description: 'Delicacy predominantly served in Maharashtra as well as Karnataka',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'mungdal_halwa',
        name: 'Mungdal Halwa',
        description: 'Mungdal halwa made with pure desi ghee and khoya',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'gulshela',
        name: 'Gulshela',
        description: 'Typical Nagpuri style Dessert made of milk, Yellow Pumkin, jaggery and sugar',
        priceAUD: 24.99,
        priceINR: 1249,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'gajar_halwa',
        name: 'Gajar Halwa (Seasonal)',
        description: 'Combination of nuts, milk, sugar, khoya and ghee with grated carrot',
        priceAUD: 15.99,
        priceINR: 799,
        category: 'desserts',
        section: 'Sweet'
      },
      {
        id: 'gulabjam',
        name: 'Gulabjam (3 pcs)',
        description: 'Specially made with pure ingredients by our chefs',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'desserts',
        section: 'Sweet'
      }
    ]
  },
  {
    id: 'drinks',
    name: 'Drinks',
    items: [
      {
        id: 'simple_tea',
        name: 'Simple Tea',
        description: 'Classic Indian-style black tea brewed with milk and sugar — warm and comforting',
        priceAUD: 3.99,
        priceINR: 199,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'masala_tea',
        name: 'Masala Tea',
        description: 'Traditional spiced tea with milk, ginger, and aromatic spices — rich and fragrant',
        priceAUD: 4.99,
        priceINR: 249,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'ginger_tea',
        name: 'Ginger Tea',
        description: 'Freshly brewed tea infused with ginger — soothing and refreshing',
        priceAUD: 4.99,
        priceINR: 249,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'black_tea',
        name: 'Black Tea',
        description: 'Plain brewed tea without milk — light and aromatic',
        priceAUD: 3.99,
        priceINR: 199,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'simple_milk_coffee',
        name: 'Simple Milk Coffee',
        description: 'Hot coffee made with milk and sugar — smooth and creamy',
        priceAUD: 4.99,
        priceINR: 249,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'black_coffee',
        name: 'Black Coffee',
        description: 'Strong, unsweetened coffee served hot — bold and energising',
        priceAUD: 4.99,
        priceINR: 249,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'masala_coffee',
        name: 'Masala Coffee',
        description: 'Special coffee blended with nutmeg and cardamom for unique aromatic taste',
        priceAUD: 5.99,
        priceINR: 299,
        category: 'drinks',
        section: 'Tea / Coffee'
      },
      {
        id: 'solkadhi',
        name: 'Solkadhi',
        description: 'Traditional Konkan drink made from coconut milk and kokum, lightly spiced — cooling and tangy',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'piyush',
        name: 'Piyush',
        description: 'Sweet, thick beverage made with yoghurt, milk, and saffron — creamy and indulgent',
        priceAUD: 11.99,
        priceINR: 599,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'mango_piyush',
        name: 'Mango Piyush',
        description: 'Piyush with mango flavor — seasonal delight',
        priceAUD: 14.99,
        priceINR: 749,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'kokum',
        name: 'Kokum',
        description: 'Tangy kokum drink — healthy and rejuvenating',
        priceAUD: 7.99,
        priceINR: 399,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'masala_kokum',
        name: 'Masala Kokum',
        description: 'Spiced kokum drink enriched with house masala',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'buttermilk',
        name: 'Butter Milk',
        description: 'Chilled drink made from yoghurt and water, lightly seasoned with spices — cool and digestive',
        priceAUD: 7.99,
        priceINR: 399,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'masala_buttermilk',
        name: 'Masala Butter Milk',
        description: 'Spiced version of buttermilk',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'lime_juice',
        name: 'Lime Juice',
        description: 'Fresh lime juice balanced with salt and sugar',
        priceAUD: 6.99,
        priceINR: 349,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      },
      {
        id: 'masala_lime',
        name: 'Masala Lime',
        description: 'Lime juice with Purnabramha\'s signature spice mix — perfectly refreshing',
        priceAUD: 8.99,
        priceINR: 449,
        category: 'drinks',
        section: 'Non Tea / Drinks'
      }
    ]
  },
  {
    id: 'soup',
    name: 'Soup / Saar',
    items: [
      {
        id: 'tomato_saar',
        name: 'Tomato Saar',
        description: 'Tangy tomato soup with onion, pepper, and mild Indian spices',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'soup',
        section: 'Saar/Soup'
      },
      {
        id: 'vedik_soup',
        name: 'Vedik Soup',
        description: 'Vedic Jawar Soup—cooling summer delicacy, steeped in Maharashtrian tradition',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'soup',
        section: 'Saar/Soup'
      },
      {
        id: 'daal_soup',
        name: 'Daal Soup',
        description: 'Lentil soup made with split pigeon peas, turmeric, and drizzle of ghee',
        priceAUD: 16.99,
        priceINR: 849,
        category: 'soup',
        section: 'Saar/Soup'
      },
      {
        id: 'pumpkin_soup',
        name: 'Pumpkin Soup (Sunday Only)',
        description: 'Comforting flavors of Pumpkin Saar with black pepper, pumpkin, and ginger',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'soup',
        section: 'Saar/Soup'
      },
      {
        id: 'pandhara_rassa',
        name: 'Pandhara Rassa',
        description: 'Creamy coconut and pepper-based soup, mildly spiced and rich in flavour',
        priceAUD: 17.99,
        priceINR: 899,
        category: 'soup',
        section: 'Saar/Soup'
      }
    ]
  }
];

// Categories for filtering
export const categories = [
  { id: 'all', name: 'All', icon: 'food' },
  { id: 'snacks', name: 'Snacks', icon: 'food-variant' },
  { id: 'main_course', name: 'Main Course', icon: 'pot-steam' },
  { id: 'rice', name: 'Rice', icon: 'rice' },
  { id: 'dal', name: 'Dal', icon: 'bowl-mix' },
  { id: 'desserts', name: 'Desserts', icon: 'cupcake' },
  { id: 'drinks', name: 'Drinks', icon: 'cup' },
  { id: 'balgopal', name: 'Kids', icon: 'baby-face' }
];
