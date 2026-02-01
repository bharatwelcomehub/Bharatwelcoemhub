import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';
import { openWhatsApp, generateTableBookingMessage } from '../../src/utils/whatsapp';

export default function BookingsScreen() {
  const { selectedCenter } = useAppStore();
  const [activeTab, setActiveTab] = useState<'table' | 'tiffin'>('table');

  // Table Booking State
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [guests, setGuests] = useState('2');
  const [serviceType, setServiceType] = useState('dine-in');

  const handleTableBooking = async () => {
    if (!name || !phone || !date || !time) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }

    try {
      const message = generateTableBookingMessage({
        name,
        phone,
        date,
        time,
        guests: parseInt(guests),
        serviceType,
        center: selectedCenter,
      });

      await openWhatsApp(selectedCenter.whatsappNumber, message);
      
      // Reset form
      setName('');
      setPhone('');
      setDate('');
      setTime('');
      setGuests('2');
      setServiceType('dine-in');
      
      Alert.alert('Success', 'Opening WhatsApp to confirm your booking!');
    } catch (error) {
      Alert.alert('Error', 'Could not open WhatsApp. Please try again.');
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'table' && styles.tabActive]}
            onPress={() => setActiveTab('table')}
          >
            <MaterialCommunityIcons
              name="silverware-fork-knife"
              size={24}
              color={activeTab === 'table' ? colors.white : colors.primary}
            />
            <Text
              style={[
                styles.tabText,
                activeTab === 'table' && styles.tabTextActive,
              ]}
            >
              Table Booking
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'tiffin' && styles.tabActive]}
            onPress={() => setActiveTab('tiffin')}
          >
            <MaterialCommunityIcons
              name="food-takeout-box"
              size={24}
              color={activeTab === 'tiffin' ? colors.white : colors.primary}
            />
            <Text
              style={[
                styles.tabText,
                activeTab === 'tiffin' && styles.tabTextActive,
              ]}
            >
              Tiffin Service
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {activeTab === 'table' ? (
            <View style={styles.form}>
              <Text style={styles.formTitle}>Book Your Table</Text>
              <Text style={styles.formSubtitle}>
                Fill the form below and we'll confirm via WhatsApp
              </Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Full Name *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Enter your name"
                  value={name}
                  onChangeText={setName}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Phone Number *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Enter your phone"
                  value={phone}
                  onChangeText={setPhone}
                  keyboardType="phone-pad"
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Date *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="DD/MM/YYYY"
                  value={date}
                  onChangeText={setDate}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Time *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 7:00 PM"
                  value={time}
                  onChangeText={setTime}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Number of Guests</Text>
                <TextInput
                  style={styles.input}
                  placeholder="2"
                  value={guests}
                  onChangeText={setGuests}
                  keyboardType="number-pad"
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Service Type</Text>
                <View style={styles.radioGroup}>
                  <TouchableOpacity
                    style={styles.radioOption}
                    onPress={() => setServiceType('dine-in')}
                  >
                    <View style={styles.radioButton}>
                      {serviceType === 'dine-in' && (
                        <View style={styles.radioButtonInner} />
                      )}
                    </View>
                    <Text style={styles.radioLabel}>Dine-In</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.radioOption}
                    onPress={() => setServiceType('pickup')}
                  >
                    <View style={styles.radioButton}>
                      {serviceType === 'pickup' && (
                        <View style={styles.radioButtonInner} />
                      )}
                    </View>
                    <Text style={styles.radioLabel}>Pickup</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleTableBooking}
              >
                <MaterialCommunityIcons
                  name="whatsapp"
                  size={20}
                  color={colors.white}
                />
                <Text style={styles.submitButtonText}>Book via WhatsApp</Text>
              </TouchableOpacity>

              <Text style={styles.note}>
                * Manager will confirm your booking via WhatsApp
              </Text>
            </View>
          ) : (
            <View style={styles.comingSoon}>
              <MaterialCommunityIcons
                name="food-takeout-box"
                size={80}
                color={colors.textSecondary}
              />
              <Text style={styles.comingSoonTitle}>Tiffin Service</Text>
              <Text style={styles.comingSoonText}>
                Weekly tiffin booking with customizable meal plans.
              </Text>
              <Text style={styles.comingSoonSubtext}>
                Available for Perth (AUD pricing with special rules) and India centers (INR with GST).
              </Text>
              <TouchableOpacity style={styles.comingSoonButton}>
                <Text style={styles.comingSoonButtonText}>Contact on WhatsApp</Text>
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  keyboardView: {
    flex: 1,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  tabTextActive: {
    color: colors.white,
  },
  content: {
    flex: 1,
  },
  form: {
    padding: 16,
  },
  formTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  formSubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 20,
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
  radioGroup: {
    flexDirection: 'row',
    gap: 24,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  radioButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioButtonInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },
  radioLabel: {
    fontSize: 14,
    color: colors.text,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    gap: 8,
    marginTop: 8,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.white,
  },
  note: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 12,
    fontStyle: 'italic',
  },
  comingSoon: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    marginTop: 64,
  },
  comingSoonTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 16,
    marginBottom: 8,
  },
  comingSoonText: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 8,
  },
  comingSoonSubtext: {
    fontSize: 14,
    color: colors.textLight,
    textAlign: 'center',
    lineHeight: 20,
  },
  comingSoonButton: {
    marginTop: 24,
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: colors.accent,
    borderRadius: 8,
  },
  comingSoonButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
});
