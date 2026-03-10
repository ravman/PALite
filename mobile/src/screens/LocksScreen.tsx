import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import PageHeader from '../components/PageHeader';
import { colors } from '../theme';

export default function LocksScreen({ navigation }: { navigation: any }) {
  return (
    <View style={styles.container}>
      <PageHeader title="Smart Locks" onBack={() => navigation.goBack()} />
      <View style={styles.center}>
        <Text style={styles.icon}>🔒</Text>
        <Text style={styles.msg}>Smart lock integration coming soon</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  icon: { fontSize: 64 },
  msg: { fontSize: 14, color: colors.text2 },
});
