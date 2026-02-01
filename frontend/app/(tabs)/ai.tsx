import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Image,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';
import { openWhatsApp } from '../../src/utils/whatsapp';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export default function AIScreen() {
  const { selectedCenter } = useAppStore();
  const [activeTab, setActiveTab] = useState<'bhojan' | 'wish' | 'guest'>('bhojan');
  const [loading, setLoading] = useState(false);

  // Bhojan Guru state
  const [bhojanMode, setBhojanMode] = useState<'region' | 'body'>('region');
  const [selectedRegion, setSelectedRegion] = useState('Pune');
  const [bodyAnswers, setBodyAnswers] = useState({
    energy: 'Normal',
    appetite: 'Normal',
    digestion: 'Good',
    mood: 'Neutral',
    activity: 'Moderate',
    special: 'None'
  });
  const [recommendations, setRecommendations] = useState<string[]>([]);

  // Wish Generator state
  const [eventType, setEventType] = useState('');
  const [namesForWish, setNamesForWish] = useState('');
  const [fromName, setFromName] = useState('');
  const [generatedWish, setGeneratedWish] = useState('');
  const [wishImageUrl, setWishImageUrl] = useState('');

  // Guest Response state
  const [guestMessage, setGuestMessage] = useState('');
  const [guestReply, setGuestReply] = useState('');

  const handleBhojanGuru = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/bhojan-guru`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: bhojanMode,
          region: bhojanMode === 'region' ? selectedRegion : null,
          questions: bhojanMode === 'body' ? bodyAnswers : null,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setRecommendations(data.recommendations);
    } catch (error) {
      Alert.alert('Error', 'Could not get recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleWishGenerator = async () => {
    if (!eventType || !namesForWish || !fromName) {
      Alert.alert('Error', 'Fill all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/wish-generator`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          center: selectedCenter.displayName,
          event_type: eventType,
          names: namesForWish,
          from_name: fromName,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setGeneratedWish(`${data.wish_text}\n\n${data.wish_marathi}`);
      setWishImageUrl(data.wish_image_url || '');
    } catch (error) {
      Alert.alert('Error', 'Could not generate wish');
    } finally {
      setLoading(false);
    }
  };

  const downloadWishImage = async () => {
    if (!wishImageUrl) return;
    
    try {
      const filename = `purnabramha_wish_${Date.now()}.png`;
      const result = await FileSystem.downloadAsync(
        wishImageUrl,
        FileSystem.documentDirectory + filename
      );
      
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(result.uri);
        Alert.alert('Success', 'Image ready to share!');
      }
    } catch (error) {
      Alert.alert('Error', 'Could not download image');
    }
  };

  const handleGuestResponse = async () => {
    if (!guestMessage) {
      Alert.alert('Error', 'Enter message');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/guest-response`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          guest_message: guestMessage,
          center: selectedCenter.displayName,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setGuestReply(data.reply);
    } catch (error) {
      Alert.alert('Error', 'Could not generate response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'bhojan' && styles.tabActive]}
            onPress={() => setActiveTab('bhojan')}
          >
            <MaterialCommunityIcons
              name="chef-hat"
              size={20}
              color={activeTab === 'bhojan' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'bhojan' && styles.tabTextActive]}>
              Bhojan Guru
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'wish' && styles.tabActive]}
            onPress={() => setActiveTab('wish')}
          >
            <MaterialCommunityIcons
              name="party-popper"
              size={20}
              color={activeTab === 'wish' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'wish' && styles.tabTextActive]}>
              Wishes
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'guest' && styles.tabActive]}
            onPress={() => setActiveTab('guest')}
          >
            <MaterialCommunityIcons
              name="message-reply-text"
              size={20}
              color={activeTab === 'guest' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'guest' && styles.tabTextActive]}>
              Guest Reply
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {activeTab === 'bhojan' && (
            <View style={styles.section}>
              <Text style={styles.title}>Bhojan Guru</Text>
              <Text style={styles.subtitle}>Get personalized thali recommendations</Text>

              <View style={styles.modeSelector}>
                <TouchableOpacity
                  style={[styles.modeButton, bhojanMode === 'region' && styles.modeButtonActive]}
                  onPress={() => setBhojanMode('region')}
                >
                  <Text style={[styles.modeButtonText, bhojanMode === 'region' && styles.modeButtonTextActive]}>
                    Region Thali
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modeButton, bhojanMode === 'body' && styles.modeButtonActive]}
                  onPress={() => setBhojanMode('body')}
                >
                  <Text style={[styles.modeButtonText, bhojanMode === 'body' && styles.modeButtonTextActive]}>
                    Body Need Thali
                  </Text>
                </TouchableOpacity>
              </View>

              {bhojanMode === 'region' ? (
                <View style={styles.inputGroup}>
                  <Text style={styles.label}>Select Region</Text>
                  <View style={styles.regionGrid}>
                    {['Pune', 'Mumbai', 'Konkan', 'Vidarbha', 'Marathwada'].map((region) => (
                      <TouchableOpacity
                        key={region}
                        style={[styles.regionChip, selectedRegion === region && styles.regionChipActive]}
                        onPress={() => setSelectedRegion(region)}
                      >
                        <Text style={[styles.regionChipText, selectedRegion === region && styles.regionChipTextActive]}>
                          {region}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ) : (
                <View style={styles.questionsContainer}>
                  <Text style={styles.questionTitle}>Answer 6 Quick Questions:</Text>
                  
                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>1. Energy Level:</Text>
                    <View style={styles.optionsRow}>
                      {['Low', 'Normal', 'High'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.energy === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, energy: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.energy === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>2. Appetite:</Text>
                    <View style={styles.optionsRow}>
                      {['Low', 'Normal', 'High'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.appetite === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, appetite: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.appetite === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>3. Digestion:</Text>
                    <View style={styles.optionsRow}>
                      {['Sensitive', 'Good', 'Strong'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.digestion === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, digestion: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.digestion === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>4. Current Mood:</Text>
                    <View style={styles.optionsRow}>
                      {['Stressed', 'Neutral', 'Happy'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.mood === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, mood: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.mood === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>5. Activity Level:</Text>
                    <View style={styles.optionsRow}>
                      {['Sedentary', 'Moderate', 'Active'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.activity === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, activity: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.activity === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>

                  <View style={styles.questionBox}>
                    <Text style={styles.questionLabel}>6. Special Needs:</Text>
                    <View style={styles.optionsRow}>
                      {['None', 'Light', 'Protein'].map(opt => (
                        <TouchableOpacity
                          key={opt}
                          style={[styles.optionChip, bodyAnswers.special === opt && styles.optionChipActive]}
                          onPress={() => setBodyAnswers({...bodyAnswers, special: opt})}
                        >
                          <Text style={[styles.optionText, bodyAnswers.special === opt && styles.optionTextActive]}>{opt}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                </View>
              )}

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleBhojanGuru}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="lightbulb-on" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Get Recommendations</Text>
                  </>
                )}
              </TouchableOpacity>

              {recommendations.length > 0 && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Your Personalized Thali:</Text>
                  {recommendations.map((item, index) => (
                    <Text key={index} style={styles.resultItem}>
                      • {item}
                    </Text>
                  ))}
                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, `My Purnabramha Order:\n${recommendations.join('\n')}`)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={20} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Send to WhatsApp</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {activeTab === 'wish' && (
            <View style={styles.section}>
              <Text style={styles.title}>Celebration Wish Generator</Text>
              <Text style={styles.subtitle}>Generate beautiful Marathi wishes with image</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Event Type *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., Birthday, Anniversary"
                  value={eventType}
                  onChangeText={setEventType}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Name(s) *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Person's name"
                  value={namesForWish}
                  onChangeText={setNamesForWish}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>From *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Your name"
                  value={fromName}
                  onChangeText={setFromName}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleWishGenerator}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="auto-fix" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Generate Wish</Text>
                  </>
                )}
              </TouchableOpacity>

              {generatedWish && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Generated Wish:</Text>
                  <Text style={styles.wishText}>{generatedWish}</Text>
                  
                  {wishImageUrl && (
                    <View style={styles.imageContainer}>
                      <Image source={{ uri: wishImageUrl }} style={styles.wishImage} resizeMode="contain" />
                      <TouchableOpacity style={styles.downloadButton} onPress={downloadWishImage}>
                        <MaterialCommunityIcons name="download" size={18} color={colors.white} />
                        <Text style={styles.downloadButtonText}>Download Image</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, generatedWish)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={18} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Share</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {activeTab === 'guest' && (
            <View style={styles.section}>
              <Text style={styles.title}>Guest Response Generator</Text>
              <Text style={styles.subtitle}>Auto-generate replies with emoticons</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Guest Message *</Text>
                <TextInput
                  style={[styles.input, styles.textArea]}
                  placeholder="Paste customer's message..."
                  value={guestMessage}
                  onChangeText={setGuestMessage}
                  multiline
                  numberOfLines={4}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleGuestResponse}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="reply" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Generate Reply</Text>
                  </>
                )}
              </TouchableOpacity>

              {guestReply && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Suggested Reply:</Text>
                  <Text style={styles.replyText}>{guestReply}</Text>
                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, guestReply)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={18} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Send</Text>
                  </TouchableOpacity>
                </View>
              )}
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
  flex: {
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
    paddingVertical: 12,
    gap: 6,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.primary,
  },
  tabTextActive: {
    color: colors.white,
  },
  content: {
    flex: 1,
  },
  section: {
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
  modeSelector: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  modeButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.primary,
    alignItems: 'center',
  },
  modeButtonActive: {
    backgroundColor: colors.primary,
  },
  modeButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  modeButtonTextActive: {
    color: colors.white,
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
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  regionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  regionChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.white,
  },
  regionChipActive: {
    backgroundColor: colors.primary,
  },
  regionChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.primary,
  },
  regionChipTextActive: {
    color: colors.white,
  },
  questionsContainer: {
    marginBottom: 20,
  },
  questionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 16,
  },
  questionBox: {
    marginBottom: 16,
  },
  questionLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  optionsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  optionChip: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.accent,
    backgroundColor: colors.white,
    alignItems: 'center',
  },
  optionChipActive: {
    backgroundColor: colors.accent,
  },
  optionText: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.accent,
  },
  optionTextActive: {
    color: colors.white,
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    gap: 8,
    marginTop: 8,
  },
  generateButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.white,
  },
  resultBox: {
    marginTop: 24,
    padding: 16,
    backgroundColor: colors.backgroundLight,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 12,
  },
  resultItem: {
    fontSize: 14,
    color: colors.text,
    marginBottom: 6,
    lineHeight: 20,
  },
  wishText: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 22,
    marginBottom: 16,
  },
  replyText: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 22,
    marginBottom: 16,
  },
  imageContainer: {
    marginBottom: 16,
  },
  wishImage: {
    width: '100%',
    height: 300,
    borderRadius: 8,
    marginBottom: 12,
  },
  downloadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.accent,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  downloadButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
  whatsappButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#25D366',
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  whatsappButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
});
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';
import { useAppStore } from '../../src/store/appStore';
import { openWhatsApp } from '../../src/utils/whatsapp';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export default function AIScreen() {
  const { selectedCenter } = useAppStore();
  const [activeTab, setActiveTab] = useState<'bhojan' | 'wish' | 'guest'>('bhojan');
  const [loading, setLoading] = useState(false);

  // Bhojan Guru state
  const [selectedRegion, setSelectedRegion] = useState('Pune');
  const [recommendations, setRecommendations] = useState<string[]>([]);

  // Wish Generator state
  const [eventType, setEventType] = useState('');
  const [namesForWish, setNamesForWish] = useState('');
  const [fromName, setFromName] = useState('');
  const [generatedWish, setGeneratedWish] = useState('');

  // Guest Response state
  const [guestMessage, setGuestMessage] = useState('');
  const [guestReply, setGuestReply] = useState('');

  const handleBhojanGuru = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/bhojan-guru`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'region',
          region: selectedRegion,
          questions: null,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setRecommendations(data.recommendations);
    } catch (error) {
      Alert.alert('Error', 'Could not get recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleWishGenerator = async () => {
    if (!eventType || !namesForWish || !fromName) {
      Alert.alert('Error', 'Fill all fields');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/wish-generator`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          center: selectedCenter.displayName,
          event_type: eventType,
          names: namesForWish,
          from_name: fromName,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setGeneratedWish(`${data.wish_text}\\n\\n${data.wish_marathi}`);
    } catch (error) {
      Alert.alert('Error', 'Could not generate wish');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestResponse = async () => {
    if (!guestMessage) {
      Alert.alert('Error', 'Enter message');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/ai/guest-response`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          guest_message: guestMessage,
          center: selectedCenter.displayName,
        }),
      });

      if (!response.ok) throw new Error('Failed');

      const data = await response.json();
      setGuestReply(data.reply);
    } catch (error) {
      Alert.alert('Error', 'Could not generate response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'bhojan' && styles.tabActive]}
            onPress={() => setActiveTab('bhojan')}
          >
            <MaterialCommunityIcons
              name="chef-hat"
              size={20}
              color={activeTab === 'bhojan' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'bhojan' && styles.tabTextActive]}>
              Bhojan Guru
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'wish' && styles.tabActive]}
            onPress={() => setActiveTab('wish')}
          >
            <MaterialCommunityIcons
              name="party-popper"
              size={20}
              color={activeTab === 'wish' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'wish' && styles.tabTextActive]}>
              Wishes
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'guest' && styles.tabActive]}
            onPress={() => setActiveTab('guest')}
          >
            <MaterialCommunityIcons
              name="message-reply-text"
              size={20}
              color={activeTab === 'guest' ? colors.white : colors.primary}
            />
            <Text style={[styles.tabText, activeTab === 'guest' && styles.tabTextActive]}>
              Guest Reply
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {activeTab === 'bhojan' && (
            <View style={styles.section}>
              <Text style={styles.title}>Bhojan Guru</Text>
              <Text style={styles.subtitle}>Get personalized thali recommendations</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Select Region</Text>
                <View style={styles.regionGrid}>
                  {['Pune', 'Mumbai', 'Konkan', 'Vidarbha', 'Marathwada'].map((region) => (
                    <TouchableOpacity
                      key={region}
                      style={[styles.regionChip, selectedRegion === region && styles.regionChipActive]}
                      onPress={() => setSelectedRegion(region)}
                    >
                      <Text style={[styles.regionChipText, selectedRegion === region && styles.regionChipTextActive]}>
                        {region}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleBhojanGuru}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="lightbulb-on" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Get Recommendations</Text>
                  </>
                )}
              </TouchableOpacity>

              {recommendations.length > 0 && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Your Personalized Thali:</Text>
                  {recommendations.map((item, index) => (
                    <Text key={index} style={styles.resultItem}>
                      • {item}
                    </Text>
                  ))}
                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, `My Purnabramha Order:\\n${recommendations.join('\\n')}`)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={20} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Send to WhatsApp</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {activeTab === 'wish' && (
            <View style={styles.section}>
              <Text style={styles.title}>Celebration Wish Generator</Text>
              <Text style={styles.subtitle}>Generate beautiful Marathi wishes</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Event Type *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., Birthday, Anniversary"
                  value={eventType}
                  onChangeText={setEventType}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Name(s) *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Person's name"
                  value={namesForWish}
                  onChangeText={setNamesForWish}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>From *</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Your name"
                  value={fromName}
                  onChangeText={setFromName}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleWishGenerator}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="auto-fix" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Generate Wish</Text>
                  </>
                )}
              </TouchableOpacity>

              {generatedWish && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Generated Wish:</Text>
                  <Text style={styles.wishText}>{generatedWish}</Text>
                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, generatedWish)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={18} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Share</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {activeTab === 'guest' && (
            <View style={styles.section}>
              <Text style={styles.title}>Guest Response Generator</Text>
              <Text style={styles.subtitle}>Auto-generate replies to customer inquiries</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.label}>Guest Message *</Text>
                <TextInput
                  style={[styles.input, styles.textArea]}
                  placeholder="Paste customer's message..."
                  value={guestMessage}
                  onChangeText={setGuestMessage}
                  multiline
                  numberOfLines={4}
                  placeholderTextColor={colors.textSecondary}
                />
              </View>

              <TouchableOpacity
                style={styles.generateButton}
                onPress={handleGuestResponse}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} />
                ) : (
                  <>
                    <MaterialCommunityIcons name="reply" size={20} color={colors.white} />
                    <Text style={styles.generateButtonText}>Generate Reply</Text>
                  </>
                )}
              </TouchableOpacity>

              {guestReply && (
                <View style={styles.resultBox}>
                  <Text style={styles.resultTitle}>Suggested Reply:</Text>
                  <Text style={styles.replyText}>{guestReply}</Text>
                  <TouchableOpacity
                    style={styles.whatsappButton}
                    onPress={() => openWhatsApp(selectedCenter.whatsappNumber, guestReply)}
                  >
                    <MaterialCommunityIcons name="whatsapp" size={18} color={colors.white} />
                    <Text style={styles.whatsappButtonText}>Send</Text>
                  </TouchableOpacity>
                </View>
              )}
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
  flex: {
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
    paddingVertical: 12,
    gap: 6,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.primary,
  },
  tabTextActive: {
    color: colors.white,
  },
  content: {
    flex: 1,
  },
  section: {
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
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  regionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  regionChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.white,
  },
  regionChipActive: {
    backgroundColor: colors.primary,
  },
  regionChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.primary,
  },
  regionChipTextActive: {
    color: colors.white,
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    gap: 8,
    marginTop: 8,
  },
  generateButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.white,
  },
  resultBox: {
    marginTop: 24,
    padding: 16,
    backgroundColor: colors.backgroundLight,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 12,
  },
  resultItem: {
    fontSize: 14,
    color: colors.text,
    marginBottom: 6,
    lineHeight: 20,
  },
  wishText: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 22,
    marginBottom: 16,
  },
  replyText: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 22,
    marginBottom: 16,
  },
  whatsappButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#25D366',
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  whatsappButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.white,
  },
});