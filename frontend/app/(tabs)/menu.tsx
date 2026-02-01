import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Share,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';
import { menuData, categories } from '../../src/data/menuData';
import { shareMenuItem, openWhatsApp } from '../../src/utils/whatsapp';

export default function MenuScreen() {
  const { selectedCenter, menuCountry, setMenuCountry } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Filter menu data
  const filteredMenu = useMemo(() => {
    return menuData
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => {
          const matchesSearch =
            item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.description.toLowerCase().includes(searchQuery.toLowerCase());
          const matchesCategory =
            selectedCategory === 'all' || item.category === selectedCategory;
          return matchesSearch && matchesCategory;
        }),
      }))
      .filter((section) => section.items.length > 0);
  }, [searchQuery, selectedCategory]);

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const handleShare = async (item: any) => {
    try {
      const message = shareMenuItem(item, selectedCenter);
      await Share.share({ message });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const getPrice = (item: any) => {
    return menuCountry === 'Australia' ? item.priceAUD : item.priceINR;
  };

  const getCurrencySymbol = () => {
    return menuCountry === 'Australia' ? '$' : '₹';
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Country Toggle */}
      <View style={styles.header}>
        <View style={styles.countryToggle}>
          <TouchableOpacity
            style={[
              styles.countryButton,
              menuCountry === 'Australia' && styles.countryButtonActive,
            ]}
            onPress={() => setMenuCountry('Australia')}
          >
            <Text
              style={[
                styles.countryText,
                menuCountry === 'Australia' && styles.countryTextActive,
              ]}
            >
              Australia
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.countryButton,
              menuCountry === 'India' && styles.countryButtonActive,
            ]}
            onPress={() => setMenuCountry('India')}
          >
            <Text
              style={[
                styles.countryText,
                menuCountry === 'India' && styles.countryTextActive,
              ]}
            >
              India
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <MaterialCommunityIcons
          name="magnify"
          size={20}
          color={colors.textSecondary}
        />
        <TextInput
          style={styles.searchInput}
          placeholder="Search dishes..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholderTextColor={colors.textSecondary}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <MaterialCommunityIcons name="close" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Category Filters */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoriesContainer}
        contentContainerStyle={styles.categoriesContent}
      >
        {categories.map((cat) => (
          <TouchableOpacity
            key={cat.id}
            style={[
              styles.categoryChip,
              selectedCategory === cat.id && styles.categoryChipActive,
            ]}
            onPress={() => setSelectedCategory(cat.id)}
          >
            <MaterialCommunityIcons
              name={cat.icon as any}
              size={18}
              color={
                selectedCategory === cat.id ? colors.white : colors.primary
              }
            />
            <Text
              style={[
                styles.categoryChipText,
                selectedCategory === cat.id && styles.categoryChipTextActive,
              ]}
            >
              {cat.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Menu Items */}
      <ScrollView style={styles.menuContainer} showsVerticalScrollIndicator={false}>
        {filteredMenu.map((section) => (
          <View key={section.id} style={styles.section}>
            <TouchableOpacity
              style={styles.sectionHeader}
              onPress={() => toggleSection(section.id)}
            >
              <Text style={styles.sectionTitle}>{section.name}</Text>
              <MaterialCommunityIcons
                name={
                  expandedSections.has(section.id)
                    ? 'chevron-up'
                    : 'chevron-down'
                }
                size={24}
                color={colors.primary}
              />
            </TouchableOpacity>

            {expandedSections.has(section.id) && (
              <View style={styles.itemsContainer}>
                {section.items.map((item) => (
                  <View key={item.id} style={styles.itemCard}>
                    <View style={styles.itemContent}>
                      <View style={styles.itemHeader}>
                        <Text style={styles.itemName}>{item.name}</Text>
                        <Text style={styles.itemPrice}>
                          {getCurrencySymbol()}{getPrice(item)}
                        </Text>
                      </View>
                      <Text style={styles.itemDescription} numberOfLines={2}>
                        {item.description}
                      </Text>
                      {item.bestWith && (
                        <Text style={styles.itemBestWith}>
                          Best with: {item.bestWith}
                        </Text>
                      )}
                    </View>
                    <TouchableOpacity
                      style={styles.shareButton}
                      onPress={() => handleShare(item)}
                    >
                      <MaterialCommunityIcons
                        name="share-variant"
                        size={20}
                        color={colors.primary}
                      />
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            )}
          </View>
        ))}

        {filteredMenu.length === 0 && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons
              name="food-off"
              size={64}
              color={colors.textSecondary}
            />
            <Text style={styles.emptyText}>No dishes found</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  countryToggle: {
    flexDirection: 'row',
    backgroundColor: colors.backgroundLight,
    borderRadius: 8,
    padding: 4,
  },
  countryButton: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 6,
  },
  countryButtonActive: {
    backgroundColor: colors.primary,
  },
  countryText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  countryTextActive: {
    color: colors.white,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    marginHorizontal: 16,
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: colors.text,
  },
  categoriesContainer: {
    marginTop: 12,
  },
  categoriesContent: {
    paddingHorizontal: 16,
    gap: 8,
  },
  categoryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.white,
    gap: 6,
  },
  categoryChipActive: {
    backgroundColor: colors.primary,
  },
  categoryChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
  },
  categoryChipTextActive: {
    color: colors.white,
  },
  menuContainer: {
    flex: 1,
    marginTop: 16,
  },
  section: {
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.backgroundLight,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  itemsContainer: {
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  itemCard: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  itemContent: {
    flex: 1,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  itemName: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginRight: 8,
  },
  itemPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.primary,
  },
  itemDescription: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  itemBestWith: {
    fontSize: 12,
    color: colors.accent,
    fontStyle: 'italic',
    marginTop: 4,
  },
  shareButton: {
    padding: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: colors.textSecondary,
  },
});