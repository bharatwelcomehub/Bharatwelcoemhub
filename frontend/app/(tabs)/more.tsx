import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Linking,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';
import { openWhatsApp } from '../../src/utils/whatsapp';

export default function MoreScreen() {
  const { selectedCenter } = useAppStore();

  const handleCall = () => {
    const phoneNumber = `tel:+${selectedCenter.whatsappNumber}`;
    Linking.openURL(phoneNumber).catch(() => {
      Alert.alert('Error', 'Unable to make call');
    });
  };

  const handleWhatsApp = () => {
    openWhatsApp(selectedCenter.whatsappNumber, 'Namaskar! I would like to know more about Purnabramha.')
      .catch(() => Alert.alert('Error', 'Unable to open WhatsApp'));
  };

  const menuItems = [
    {
      id: 'about',
      title: 'About Purnabramha',
      icon: 'information',
      onPress: () => Alert.alert('About Us', 'Purnabramha is a premium multi-center Maharashtrian vegetarian restaurant chain serving authentic traditional cuisine with love and care.'),
    },
    {
      id: 'locations',
      title: 'Our Locations',
      icon: 'map-marker-multiple',
      onPress: () => Alert.alert('Locations', 'Perth (Australia)\nHSR Bangalore\nThane Mumbai\nSambhajinagar\nDombivli\nKharadi Pune\nHinjawadi Pune'),
    },
    {
      id: 'call',
      title: 'Call Us',
      icon: 'phone',
      onPress: handleCall,
    },
    {
      id: 'whatsapp',
      title: 'WhatsApp',
      icon: 'whatsapp',
      onPress: handleWhatsApp,
    },
    {
      id: 'franchise',
      title: 'Franchise Opportunities',
      icon: 'store',
      onPress: () => Alert.alert('Franchise', 'Interested in opening a Purnabramha franchise? Contact us for more details!'),
    },
    {
      id: 'careers',
      title: 'Careers',
      icon: 'briefcase',
      onPress: () => Alert.alert('Careers', 'Join the Purnabramha family! We are always looking for passionate team members.'),
    },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoContainer}>
            <MaterialCommunityIcons name="food" size={48} color={colors.primary} />
          </View>
          <Text style={styles.headerTitle}>Purnabramha</Text>
          <Text style={styles.headerSubtitle}>Premium Maharashtrian Cuisine</Text>
        </View>

        {/* Current Center Info */}
        <View style={styles.centerCard}>
          <View style={styles.centerHeader}>
            <MaterialCommunityIcons name="map-marker" size={24} color={colors.primary} />
            <Text style={styles.centerTitle}>Current Center</Text>
          </View>
          <Text style={styles.centerName}>{selectedCenter.displayName}</Text>
          <Text style={styles.centerCountry}>{selectedCenter.country}</Text>
        </View>

        {/* Menu Items */}
        <View style={styles.menuContainer}>
          {menuItems.map((item) => (
            <TouchableOpacity
              key={item.id}
              style={styles.menuItem}
              onPress={item.onPress}
              activeOpacity={0.7}
            >
              <View style={styles.menuIconContainer}>
                <MaterialCommunityIcons
                  name={item.icon as any}
                  size={24}
                  color={colors.primary}
                />
              </View>
              <Text style={styles.menuItemText}>{item.title}</Text>
              <MaterialCommunityIcons
                name="chevron-right"
                size={24}
                color={colors.textSecondary}
              />
            </TouchableOpacity>
          ))}
        </View>

        {/* Policies */}
        <View style={styles.policiesContainer}>
          <Text style={styles.policiesTitle}>Our Commitment</Text>
          <View style={styles.policyItem}>
            <MaterialCommunityIcons name="leaf" size={20} color={colors.success} />
            <Text style={styles.policyText}>100% Vegetarian</Text>
          </View>
          <View style={styles.policyItem}>
            <MaterialCommunityIcons name="shield-check" size={20} color={colors.success} />
            <Text style={styles.policyText}>Hygienic & Fresh Ingredients</Text>
          </View>
          <View style={styles.policyItem}>
            <MaterialCommunityIcons name="account-group" size={20} color={colors.success} />
            <Text style={styles.policyText}>Traditional Maharashtrian Recipes</Text>
          </View>
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Version 1.0.0</Text>
          <Text style={styles.footerText}>© 2025 Purnabramha</Text>
          <Text style={styles.footerSubtext}>Made with ❤️ for food lovers</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  logoContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.backgroundLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  centerCard: {
    backgroundColor: colors.white,
    marginHorizontal: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  centerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  centerTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  centerName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  centerCountry: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  menuContainer: {
    marginTop: 16,
    backgroundColor: colors.white,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    gap: 12,
  },
  menuIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.backgroundLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuItemText: {
    flex: 1,
    fontSize: 16,
    color: colors.text,
    fontWeight: '500',
  },
  policiesContainer: {
    marginHorizontal: 16,
    marginTop: 24,
    padding: 16,
    backgroundColor: colors.white,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  policiesTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  policyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  policyText: {
    fontSize: 14,
    color: colors.text,
  },
  footer: {
    alignItems: 'center',
    padding: 24,
    marginTop: 16,
  },
  footerText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  footerSubtext: {
    fontSize: 12,
    color: colors.textSecondary,
    fontStyle: 'italic',
    marginTop: 8,
  },
});