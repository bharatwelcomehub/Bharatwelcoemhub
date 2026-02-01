import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors } from '../../src/theme/colors';

export default function AIScreen() {
  const aiTools = [
    {
      id: 'bhojan-guru',
      title: 'Bhojan Guru',
      description: 'Get personalized thali recommendations based on your preferences or body needs',
      icon: 'chef-hat',
      color: colors.primary,
      comingSoon: false,
    },
    {
      id: 'wish-generator',
      title: 'Celebration Wish Generator',
      description: 'Generate beautiful Marathi wishes for special occasions',
      icon: 'party-popper',
      color: colors.accent,
      comingSoon: false,
    },
    {
      id: 'guest-response',
      title: 'Guest Response Generator',
      description: 'Auto-generate replies to customer WhatsApp enquiries',
      icon: 'message-reply-text',
      color: colors.primary,
      comingSoon: false,
    },
  ];

  const handleToolPress = (toolId: string) => {
    Alert.alert(
      'Coming Soon',
      'AI features are being integrated with OpenAI GPT-5.2. This will be available shortly!',
      [{ text: 'OK' }]
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <MaterialCommunityIcons name="robot" size={64} color={colors.primary} />
          <Text style={styles.headerTitle}>AI Powered Tools</Text>
          <Text style={styles.headerSubtitle}>
            Smart features to enhance your Purnabramha experience
          </Text>
        </View>

        <View style={styles.toolsContainer}>
          {aiTools.map((tool) => (
            <TouchableOpacity
              key={tool.id}
              style={styles.toolCard}
              onPress={() => handleToolPress(tool.id)}
              activeOpacity={0.7}
            >
              <View style={[styles.toolIconContainer, { backgroundColor: tool.color }]}>
                <MaterialCommunityIcons name={tool.icon as any} size={32} color={colors.white} />
              </View>
              <View style={styles.toolContent}>
                <Text style={styles.toolTitle}>{tool.title}</Text>
                <Text style={styles.toolDescription}>{tool.description}</Text>
              </View>
              <MaterialCommunityIcons
                name="chevron-right"
                size={24}
                color={colors.textSecondary}
              />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.infoBox}>
          <MaterialCommunityIcons name="information" size={24} color={colors.info} />
          <Text style={styles.infoText}>
            These AI features use advanced language models to provide personalized recommendations and content.
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
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: 16,
    marginBottom: 8,
  },
  headerSubtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  toolsContainer: {
    padding: 16,
    gap: 12,
  },
  toolCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    gap: 12,
  },
  toolIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toolContent: {
    flex: 1,
  },
  toolTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  toolDescription: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  infoBox: {
    flexDirection: 'row',
    backgroundColor: colors.backgroundLight,
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 24,
    padding: 16,
    borderRadius: 8,
    gap: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
});