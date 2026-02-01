import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { useAppStore } from '../store/appStore';
import { openWhatsApp } from '../utils/whatsapp';

interface TiffinItem {
  id: string;
  name: string;
  basePrice: number;
}

const tiffinItems: TiffinItem[] = [
  { id: '1', name: 'Puri Bhaji', basePrice: 14 },
  { id: '2', name: 'Misal Pav', basePrice: 15 },
  { id: '3', name: 'Poha', basePrice: 12 },
  { id: '4', name: 'Thalipith', basePrice: 14 },
  { id: '5', name: 'Sabudana Khichadi', basePrice: 13 },
  { id: '6', name: 'Shrikhand Puri', basePrice: 18 },
];

const addons = [
  { id: 'buttermilk', name: 'Buttermilk', price: 3 },
  { id: 'kokum', name: 'Kokum', price: 3 },
];

export const TiffinBooking = () => {
  const { selectedCenter } = useAppStore();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [selectedDays, setSelectedDays] = useState<Set<string>>(new Set());
  const [selectedItems, setSelectedItems] = useState<{[key: string]: {item: string, addon: string}}>({});

  const isPerthCenter = selectedCenter.country === 'Australia';
  const isIndiaCenter = selectedCenter.country === 'India';

  // Generate next 3 weeks
  const weeks = useMemo(() => {
    const result = [];
    const today = new Date();
    for (let w = 0; w < 3; w++) {
      const weekDays = [];
      for (let d = 0; d < 7; d++) {
        const date = new Date(today);
        date.setDate(today.getDate() + (w * 7) + d);
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const isWeekday = dayName !== 'Sat' && dayName !== 'Sun';
        weekDays.push({
          date: date.toLocaleDateString('en-GB'),
          dayName,
          isWeekday,
          key: `w${w}-d${d}`,
        });
      }
      result.push(weekDays);
    }
    return result;
  }, []);

  const toggleDay = (dayKey: string) => {
    setSelectedDays(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dayKey)) {
        newSet.delete(dayKey);
        // Remove item selection for this day
        setSelectedItems(prevItems => {
          const newItems = {...prevItems};
          delete newItems[dayKey];
          return newItems;
        });
      } else {
        newSet.add(dayKey);
      }
      return newSet;
    });
  };

  const setDayItem = (dayKey: string, itemId: string, addonId: string) => {
    setSelectedItems(prev => ({
      ...prev,
      [dayKey]: { item: itemId, addon: addonId }
    }));
  };

  // Calculate pricing
  const { totalAmount, breakdown } = useMemo(() => {
    let total = 0;
    const items: any[] = [];

    if (isPerthCenter) {
      // Perth logic: Check if all weekdays selected
      const weekdaysInWeek = weeks[selectedWeek - 1]?.filter(d => d.isWeekday) || [];
      const selectedWeekdays = weekdaysInWeek.filter(d => selectedDays.has(d.key));
      const allWeekdaysSelected = selectedWeekdays.length === weekdaysInWeek.length;
      
      const pricePerDay = allWeekdaysSelected ? 18 : 20;
      total = selectedWeekdays.length * pricePerDay;
      
      items.push({
        name: `Tiffin Service (${selectedWeekdays.length} days)`,
        price: pricePerDay,
        qty: selectedWeekdays.length,
        subtotal: total
      });
    } else if (isIndiaCenter) {
      // India logic: Per-item pricing with addon
      selectedDays.forEach(dayKey => {
        const selection = selectedItems[dayKey];
        if (selection) {
          const item = tiffinItems.find(i => i.id === selection.item);
          const addon = addons.find(a => a.id === selection.addon);
          if (item && addon) {
            const itemTotal = item.basePrice + addon.price;
            total += itemTotal;
            items.push({
              name: `${item.name} + ${addon.name}`,
              price: itemTotal,
              qty: 1,
              subtotal: itemTotal
            });
          }
        }
      });
      
      // Add 5% GST
      const gst = total * 0.05;
      total += gst;
      items.push({
        name: 'GST (5%)',
        price: gst,
        qty: 1,
        subtotal: gst
      });
    }

    return { totalAmount: total, breakdown: items };
  }, [selectedDays, selectedItems, selectedWeek, isPerthCenter, isIndiaCenter]);

  const handleSubmit = async () => {
    if (!name || !phone) {
      Alert.alert('Error', 'Please fill name and phone');
      return;
    }

    if (selectedDays.size === 0) {
      Alert.alert('Error', 'Please select at least one day');
      return;
    }

    if (isIndiaCenter) {
      // Check if all selected days have items
      const allDaysHaveItems = Array.from(selectedDays).every(day => selectedItems[day]);
      if (!allDaysHaveItems) {
        Alert.alert('Error', 'Please select items for all selected days');
        return;
      }
    }

    // Generate WhatsApp message
    const daysList = Array.from(selectedDays)
      .map(key => {
        const week = weeks[selectedWeek - 1];
        const day = week?.find(d => d.key === key);
        return day ? `${day.dayName} ${day.date}` : key;
      })
      .join(', ');

    const itemsList = isIndiaCenter 
      ? breakdown.map(b => `${b.name} x${b.qty} - ${selectedCenter.currencySymbol}${b.subtotal.toFixed(2)}`).join('\\n')
      : '';

    const message = `🔹 Namaskar from Purnabramha!

Tiffin / Lunch Box Booking:

📍 Location: ${selectedCenter.displayName}
👤 Name: ${name}
📱 Phone: ${phone}
📅 Week: ${selectedWeek}
📅 Days: ${daysList}
${itemsList ? `\\nItems:\\n${itemsList}` : ''}

💰 Total Amount: ${selectedCenter.currencySymbol}${totalAmount.toFixed(2)}

Please confirm the tiffin booking. Thank you!`;

    try {
      await openWhatsApp(selectedCenter.whatsappNumber, message);
      Alert.alert('Success', 'Opening WhatsApp to confirm!');
    } catch (error) {
      Alert.alert('Error', 'Could not open WhatsApp');
    }
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <Text style={styles.title}>Tiffin / Heavy Brunch Booking</Text>
      <Text style={styles.subtitle}>Select days and customize your weekly meals</Text>

      {/* Customer Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Your Details</Text>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Name *</Text>
          <TextInput
            style={styles.input}
            placeholder="Your name"
            value={name}
            onChangeText={setName}
            placeholderTextColor={colors.textSecondary}
          />
        </View>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>Phone *</Text>
          <TextInput
            style={styles.input}
            placeholder="Your phone"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            placeholderTextColor={colors.textSecondary}
          />
        </View>
      </View>

      {/* Week Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Select Week</Text>
        <View style={styles.weekSelector}>
          {[1, 2, 3].map(week => (
            <TouchableOpacity
              key={week}
              style={[styles.weekButton, selectedWeek === week && styles.weekButtonActive]}
              onPress={() => setSelectedWeek(week)}
            >
              <Text style={[styles.weekButtonText, selectedWeek === week && styles.weekButtonTextActive]}>
                Week {week}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Day Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Select Days (Weekdays Only)</Text>
        {isPerthCenter && (
          <Text style={styles.pricingNote}>
            ⚡ All weekdays selected: $18/day | Any day skipped: $20/day
          </Text>
        )}
        <View style={styles.daysGrid}>
          {weeks[selectedWeek - 1]?.filter(d => d.isWeekday).map(day => (
            <TouchableOpacity
              key={day.key}
              style={[styles.dayCard, selectedDays.has(day.key) && styles.dayCardActive]}
              onPress={() => toggleDay(day.key)}
            >
              <Text style={[styles.dayName, selectedDays.has(day.key) && styles.dayNameActive]}>
                {day.dayName}
              </Text>
              <Text style={[styles.dayDate, selectedDays.has(day.key) && styles.dayDateActive]}>
                {day.date.split('/').slice(0, 2).join('/')}
              </Text>
              {selectedDays.has(day.key) && (
                <MaterialCommunityIcons name="check-circle" size={20} color={colors.white} />
              )}
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Item Selection for India */}
      {isIndiaCenter && selectedDays.size > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Select Items for Each Day</Text>
          {Array.from(selectedDays).map(dayKey => {
            const week = weeks[selectedWeek - 1];
            const day = week?.find(d => d.key === dayKey);
            const selection = selectedItems[dayKey] || { item: '', addon: '' };

            return (
              <View key={dayKey} style={styles.dayItemSelector}>
                <Text style={styles.dayItemTitle}>
                  {day?.dayName} {day?.date}
                </Text>
                
                {/* Item Selection */}
                <Text style={styles.itemLabel}>Choose Main Item:</Text>
                <View style={styles.itemGrid}>
                  {tiffinItems.map(item => (
                    <TouchableOpacity
                      key={item.id}
                      style={[
                        styles.itemChip,
                        selection.item === item.id && styles.itemChipActive
                      ]}
                      onPress={() => setDayItem(dayKey, item.id, selection.addon)}
                    >
                      <Text style={[
                        styles.itemChipText,
                        selection.item === item.id && styles.itemChipTextActive
                      ]}>
                        {item.name}
                      </Text>
                      <Text style={[
                        styles.itemChipPrice,
                        selection.item === item.id && styles.itemChipPriceActive
                      ]}>
                        ₹{item.basePrice}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {/* Addon Selection */}
                {selection.item && (
                  <>
                    <Text style={styles.itemLabel}>Choose Addon (Mandatory):</Text>
                    <View style={styles.addonRow}>
                      {addons.map(addon => (
                        <TouchableOpacity
                          key={addon.id}
                          style={[
                            styles.addonChip,
                            selection.addon === addon.id && styles.addonChipActive
                          ]}
                          onPress={() => setDayItem(dayKey, selection.item, addon.id)}
                        >
                          <Text style={[
                            styles.addonChipText,
                            selection.addon === addon.id && styles.addonChipTextActive
                          ]}>
                            {addon.name} (+₹{addon.price})
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </>
                )}
              </View>
            );
          })}
        </View>
      )}

      {/* Summary */}
      {selectedDays.size > 0 && (
        <View style={styles.summary}>
          <Text style={styles.summaryTitle}>Order Summary</Text>
          {breakdown.map((item, idx) => (
            <View key={idx} style={styles.summaryRow}>
              <Text style={styles.summaryItem}>{item.name}</Text>
              <Text style={styles.summaryPrice}>
                {selectedCenter.currencySymbol}{item.subtotal.toFixed(2)}
              </Text>
            </View>
          ))}
          <View style={styles.summaryTotal}>
            <Text style={styles.summaryTotalText}>Total</Text>
            <Text style={styles.summaryTotalPrice}>
              {selectedCenter.currencySymbol}{totalAmount.toFixed(2)}
            </Text>
          </View>

          <TouchableOpacity style={styles.submitButton} onPress={handleSubmit}>
            <MaterialCommunityIcons name="whatsapp" size={20} color={colors.white} />
            <Text style={styles.submitButtonText}>Send to WhatsApp</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 24,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  input: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
    color: colors.text,
  },
  weekSelector: {
    flexDirection: 'row',
    gap: 12,
  },
  weekButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.primary,
    alignItems: 'center',
    backgroundColor: colors.white,
  },
  weekButtonActive: {
    backgroundColor: colors.primary,
  },
  weekButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  weekButtonTextActive: {
    color: colors.white,
  },
  pricingNote: {
    fontSize: 12,
    color: colors.accent,
    marginBottom: 12,
    fontWeight: '600',
  },
  daysGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  dayCard: {
    width: '30%',
    backgroundColor: colors.white,
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  dayCardActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  dayName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  dayNameActive: {
    color: colors.white,
  },
  dayDate: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  dayDateActive: {
    color: colors.white,
  },
  dayItemSelector: {
    backgroundColor: colors.backgroundLight,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  dayItemTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  itemLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
    marginTop: 8,
    marginBottom: 8,
  },
  itemGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  itemChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.white,
  },
  itemChipActive: {
    backgroundColor: colors.primary,
  },
  itemChipText: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.primary,
  },
  itemChipTextActive: {
    color: colors.white,
  },
  itemChipPrice: {
    fontSize: 11,
    color: colors.textSecondary,
  },
  itemChipPriceActive: {
    color: colors.white,
  },
  addonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  addonChip: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.white,
    alignItems: 'center',
  },
  addonChipActive: {
    backgroundColor: colors.accent,
  },
  addonChipText: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.accent,
  },
  addonChipTextActive: {
    color: colors.white,
  },
  summary: {
    backgroundColor: colors.backgroundLight,
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryItem: {
    fontSize: 14,
    color: colors.text,
    flex: 1,
  },
  summaryPrice: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  summaryTotal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  summaryTotalText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  summaryTotalPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.primary,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#25D366',
    borderRadius: 8,
    paddingVertical: 14,
    gap: 8,
    marginTop: 16,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.white,
  },
});
