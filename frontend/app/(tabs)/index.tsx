import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { CenterSelector } from '../../src/components/CenterSelector';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';

const { width } = Dimensions.get('window');

export default function HomeScreen() {
  const router = useRouter();
  const { selectedCenter } = useAppStore();

  const quickActions = [
    {
      id: 'menu',
      title: 'Open Menu',
      icon: 'food',
      route: '/menu',
      gradient: [colors.primary, colors.primaryLight],
    },
    {
      id: 'booking',
      title: 'Table Booking',
      icon: 'calendar-check',
      route: '/bookings',
      gradient: [colors.accent, colors.accentLight],
    },
    {
      id: 'tiffin',
      title: 'Tiffin / Lunch Box',
      icon: 'food-takeout-box',
      route: '/bookings',
      gradient: [colors.primary, colors.primaryDark],
    },
    {
      id: 'ai',
      title: 'AI Bhojan Guru',
      icon: 'robot',
      route: '/ai',
      gradient: [colors.accent, colors.accentDark],
    },
  ];

  const featuredCategories = [
    { id: 'snacks', name: 'Snacks', icon: 'food-variant' },
    { id: 'main_course', name: 'Main Course', icon: 'pot-steam' },
    { id: 'rice', name: 'Rice', icon: 'rice' },
    { id: 'dal', name: 'Dal', icon: 'bowl-mix' },
    { id: 'desserts', name: 'Desserts', icon: 'cupcake' },
    { id: 'drinks', name: 'Drinks', icon: 'cup' },
    { id: 'balgopal', name: 'Balgopal', icon: 'baby-face' },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Center Selector */}
        <CenterSelector />

        {/* Hero Section */}
        <View style={styles.hero}>
          <View style={styles.heroContent}>
            <Text style={styles.heroTitle}>Purnabramha</Text>
            <Text style={styles.heroSubtitle}>
              Premium Maharashtrian Vegetarian Cuisine
            </Text>
            <View style={styles.heroBadge}>
              <MaterialCommunityIcons name="leaf" size={16} color={colors.success} />
              <Text style={styles.heroBadgeText}>100% Vegetarian</Text>
            </View>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            {quickActions.map((action) => (
              <TouchableOpacity
                key={action.id}
                style={styles.actionCard}
                onPress={() => router.push(action.route as any)}
                activeOpacity={0.7}
              >
                <View
                  style={[
                    styles.actionIconContainer,
                    { backgroundColor: colors.primary },
                  ]}
                >
                  <MaterialCommunityIcons
                    name={action.icon as any}
                    size={32}
                    color={colors.white}
                  />
                </View>
                <Text style={styles.actionTitle}>{action.title}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Featured Categories */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Featured Categories</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categoriesScroll}
          >
            {featuredCategories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={styles.categoryCard}
                onPress={() => router.push('/menu')}
              >
                <View style={styles.categoryIcon}>
                  <MaterialCommunityIcons
                    name={category.icon as any}
                    size={28}
                    color={colors.primary}
                  />
                </View>
                <Text style={styles.categoryName}>{category.name}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Location Info */}
        <View style={styles.section}>
          <View style={styles.infoCard}>
            <MaterialCommunityIcons
              name="map-marker"
              size={24}
              color={colors.primary}
            />
            <View style={styles.infoContent}>
              <Text style={styles.infoTitle}>Current Location</Text>
              <Text style={styles.infoText}>
                {selectedCenter.displayName}, {selectedCenter.country}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Serving authentic Maharashtrian cuisine with love
          </Text>
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
  hero: {
    backgroundColor: colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 32,
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 16,
  },
  heroContent: {
    alignItems: 'center',
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: colors.white,
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 16,
    color: colors.white,
    textAlign: 'center',
    opacity: 0.9,
    marginBottom: 16,
  },
  heroBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  heroBadgeText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.success,
  },
  section: {
    marginTop: 24,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  actionCard: {
    width: (width - 48) / 2,
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionIconContainer: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    textAlign: 'center',
  },
  categoriesScroll: {
    paddingRight: 16,
    gap: 12,
  },
  categoryCard: {
    width: 100,
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  categoryIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.backgroundLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  categoryName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
    textAlign: 'center',
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    gap: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoContent: {
    flex: 1,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: 4,
  },
  infoText: {
    fontSize: 16,
    color: colors.text,
    fontWeight: '500',
  },
  footer: {
    marginTop: 32,
    marginBottom: 24,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});