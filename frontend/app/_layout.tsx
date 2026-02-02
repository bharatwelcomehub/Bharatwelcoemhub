import React from 'react';
import { Slot, SplashScreen } from 'expo-router';
import { Provider as PaperProvider, MD3LightTheme } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, DefaultTheme } from '@react-navigation/native';

// Prevent splash screen from auto-hiding
SplashScreen.preventAutoHideAsync();

const paperTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#5d4037',      // Dark Brown
    secondary: '#d4af37',    // Gold
  },
};

const navigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#5d4037',      // Dark Brown
    background: '#ffffff',
    card: '#ffffff',
    text: '#1a1a1a',
    border: '#e0e0e0',
  },
};

export default function RootLayout() {
  React.useEffect(() => {
    SplashScreen.hideAsync();
  }, []);

  return (
    <SafeAreaProvider>
      <ThemeProvider value={navigationTheme}>
        <PaperProvider theme={paperTheme}>
          <Slot />
        </PaperProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}