import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme';

const variants: Record<string, { bg: string; text: string }> = {
  green:  { bg: 'rgba(0,184,148,0.15)',   text: colors.green },
  red:    { bg: 'rgba(225,112,85,0.15)',   text: colors.red },
  orange: { bg: 'rgba(253,203,110,0.15)',  text: colors.orange },
  purple: { bg: 'rgba(108,92,231,0.15)',   text: colors.accent },
};

export default function Badge({ label, variant = 'green' }: { label: string; variant?: string }) {
  const v = variants[variant] || variants.green;
  return (
    <View style={[styles.badge, { backgroundColor: v.bg }]}>
      <Text style={[styles.text, { color: v.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 20 },
  text: { fontSize: 11, fontWeight: '600' },
});
