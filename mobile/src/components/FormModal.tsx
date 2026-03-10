import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Modal, KeyboardAvoidingView, Platform,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { colors, radius, spacing } from '../theme';

interface Field {
  key: string;
  label: string;
  type?: 'text' | 'select' | 'number' | 'date' | 'datetime-local';
  options?: string[];
}

interface Props {
  visible: boolean;
  title: string;
  fields: Field[];
  initialData?: Record<string, string>;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => void;
}

export default function FormModal({ visible, title, fields, initialData, onClose, onSubmit }: Props) {
  const [data, setData] = useState<Record<string, string>>(initialData || {});
  const set = (k: string, v: string) => setData(d => ({ ...d, [k]: v }));
  const voiceFilledCount = Object.keys(initialData || {}).length;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={onClose}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.kvContainer}>
          <TouchableOpacity activeOpacity={1} onPress={() => {}}>
            <View style={styles.sheet}>
              <View style={styles.handle} />
              <Text style={styles.title}>{title}</Text>

              {voiceFilledCount > 0 && (
                <View style={styles.voiceBanner}>
                  <Text style={styles.voiceBannerText}>🎤 Voice filled {voiceFilledCount} field{voiceFilledCount > 1 ? 's' : ''}</Text>
                </View>
              )}

              <ScrollView showsVerticalScrollIndicator={false}>
                {fields.map(f => (
                  <View key={f.key} style={styles.formGroup}>
                    <Text style={styles.label}>{f.label}</Text>
                    {f.type === 'select' ? (
                      <View style={[styles.input, styles.pickerWrap, initialData?.[f.key] ? styles.voiceFilled : {}]}>
                        <Picker
                          selectedValue={data[f.key] || ''}
                          onValueChange={v => set(f.key, v)}
                          style={{ color: colors.text }}
                          dropdownIconColor={colors.text2}
                        >
                          <Picker.Item label="Select..." value="" color={colors.text2} />
                          {f.options?.map(o => (
                            <Picker.Item key={o} label={o} value={o} color={colors.text} />
                          ))}
                        </Picker>
                      </View>
                    ) : (
                      <TextInput
                        style={[styles.input, initialData?.[f.key] ? styles.voiceFilled : {}]}
                        value={data[f.key] || ''}
                        onChangeText={v => set(f.key, v)}
                        placeholder={f.label}
                        placeholderTextColor={colors.text2}
                        keyboardType={f.type === 'number' ? 'numeric' : 'default'}
                      />
                    )}
                  </View>
                ))}

                <View style={styles.row}>
                  <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={() => onSubmit(data)}>
                    <Text style={styles.btnText}>Submit</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={onClose}>
                    <Text style={[styles.btnText, { color: colors.text }]}>Cancel</Text>
                  </TouchableOpacity>
                </View>
              </ScrollView>
            </View>
          </TouchableOpacity>
        </KeyboardAvoidingView>
      </TouchableOpacity>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  kvContainer: { justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: spacing.xl, paddingBottom: 36,
    maxHeight: '90%',
  },
  handle: {
    width: 40, height: 4, backgroundColor: colors.border,
    borderRadius: 2, alignSelf: 'center', marginBottom: 16,
  },
  title: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 16 },
  voiceBanner: {
    backgroundColor: 'rgba(108,92,231,0.12)', borderRadius: radius.md,
    padding: spacing.sm, marginBottom: 12,
  },
  voiceBannerText: { fontSize: 12, color: colors.accent2 },
  formGroup: { marginBottom: 14 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6 },
  input: {
    backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14,
  },
  pickerWrap: { padding: 0 },
  voiceFilled: { borderColor: colors.accent, backgroundColor: 'rgba(108,92,231,0.08)' },
  row: { flexDirection: 'row', gap: 10, marginTop: 16 },
  btn: { flex: 1, padding: 12, borderRadius: 10, alignItems: 'center' },
  btnPrimary: { backgroundColor: colors.accent },
  btnSecondary: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border },
  btnText: { fontSize: 14, fontWeight: '600', color: colors.white },
});
