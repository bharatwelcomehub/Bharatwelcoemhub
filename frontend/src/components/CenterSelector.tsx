import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity, Text, Modal, FlatList } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAppStore } from '../store/appStore';
import { centers } from '../data/centersData';
import { colors } from '../theme/colors';

export const CenterSelector = () => {
  const { selectedCenter, setSelectedCenter } = useAppStore();
  const [modalVisible, setModalVisible] = useState(false);

  const handleSelectCenter = (center: any) => {
    setSelectedCenter(center);
    setModalVisible(false);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity 
        style={styles.selector}
        onPress={() => setModalVisible(true)}
      >
        <MaterialCommunityIcons name="map-marker" size={20} color={colors.primary} />
        <Text style={styles.centerText}>{selectedCenter.displayName}</Text>
        <MaterialCommunityIcons name="chevron-down" size={20} color={colors.primary} />
      </TouchableOpacity>

      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Location</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.text} />
              </TouchableOpacity>
            </View>

            <FlatList
              data={centers}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.centerItem,
                    item.id === selectedCenter.id && styles.centerItemActive
                  ]}
                  onPress={() => handleSelectCenter(item)}
                >
                  <View style={styles.centerInfo}>
                    <Text style={styles.centerName}>{item.displayName}</Text>
                    <Text style={styles.centerCountry}>{item.country}</Text>
                  </View>
                  {item.id === selectedCenter.id && (
                    <MaterialCommunityIcons name="check-circle" size={24} color={colors.primary} />
                  )}
                </TouchableOpacity>
              )}
            />
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  selector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.primary,
    gap: 8,
  },
  centerText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  centerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  centerItemActive: {
    backgroundColor: colors.backgroundLight,
  },
  centerInfo: {
    flex: 1,
  },
  centerName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  centerCountry: {
    fontSize: 14,
    color: colors.textSecondary,
  },
});