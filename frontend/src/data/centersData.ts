// Purnabramha Centers Configuration
export interface Center {
  id: string;
  name: string;
  displayName: string;
  country: 'Australia' | 'India';
  city: string;
  whatsappNumber: string; // International format
  currency: 'AUD' | 'INR';
  currencySymbol: string;
}

export const centers: Center[] = [
  {
    id: 'pb-perth',
    name: 'PB-Perth',
    displayName: 'Perth',
    country: 'Australia',
    city: 'Perth',
    whatsappNumber: '61401832922',
    currency: 'AUD',
    currencySymbol: '$'
  },
  {
    id: 'pb-hsr',
    name: 'PB-HSR',
    displayName: 'HSR Bangalore',
    country: 'India',
    city: 'Bangalore',
    whatsappNumber: '918550078515',
    currency: 'INR',
    currencySymbol: '₹'
  },
  {
    id: 'pb-thane',
    name: 'PB-Thane',
    displayName: 'Thane Mumbai',
    country: 'India',
    city: 'Mumbai',
    whatsappNumber: '918904749084',
    currency: 'INR',
    currencySymbol: '₹'
  },
  {
    id: 'pb-sambhajinagar',
    name: 'PB-SambhajiNagar',
    displayName: 'Ch. Sambhajinagar',
    country: 'India',
    city: 'Sambhajinagar',
    whatsappNumber: '918971049084',
    currency: 'INR',
    currencySymbol: '₹'
  },
  {
    id: 'pb-dombivli',
    name: 'PB-Dombivli',
    displayName: 'Dombivli Mumbai',
    country: 'India',
    city: 'Mumbai',
    whatsappNumber: '919606455433',
    currency: 'INR',
    currencySymbol: '₹'
  },
  {
    id: 'pb-hinjawadi',
    name: 'PB-Hinjawadi',
    displayName: 'Hinjawadi Pune',
    country: 'India',
    city: 'Pune',
    whatsappNumber: '919606455434',
    currency: 'INR',
    currencySymbol: '₹'
  },
  {
    id: 'pb-kharadi',
    name: 'PB-KharadiNyati',
    displayName: 'Kharadi Pune',
    country: 'India',
    city: 'Pune',
    whatsappNumber: '919900089803',
    currency: 'INR',
    currencySymbol: '₹'
  }
];

// Helper function to get center by ID
export const getCenterById = (centerId: string): Center | undefined => {
  return centers.find(c => c.id === centerId);
};

// Helper function to get centers by country
export const getCentersByCountry = (country: 'Australia' | 'India'): Center[] => {
  return centers.filter(c => c.country === country);
};
