import { create } from 'zustand';
import { Center, centers } from '../data/centersData';

interface AppStore {
  // Selected center
  selectedCenter: Center;
  setSelectedCenter: (center: Center) => void;
  
  // Menu country toggle (AUS/IND)
  menuCountry: 'Australia' | 'India';
  setMenuCountry: (country: 'Australia' | 'India') => void;
}

export const useAppStore = create<AppStore>((set) => ({
  // Default to Perth
  selectedCenter: centers[0],
  setSelectedCenter: (center) => set({ selectedCenter: center }),
  
  // Default to Australia menu
  menuCountry: 'Australia',
  setMenuCountry: (country) => set({ menuCountry: country }),
}));
