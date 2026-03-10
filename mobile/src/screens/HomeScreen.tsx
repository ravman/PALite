import React, { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { api } from '../api';
import { colors, spacing } from '../theme';

const { width } = Dimensions.get('window');
const TILE_SIZE = (width - 40 - 10) / 2;

const TILES = [
  { key: 'gate',    label: 'Gate',          color: '#9B7B6A', screen: 'Visitors' },
  { key: 'booking', label: 'Space Booking', color: '#6B7FA3', screen: 'Bookings' },
  { key: 'visitor', label: 'Visitors',      color: '#C4A882', screen: 'Visitors' },
  { key: 'market',  label: 'Marketplace',   color: '#8A9E8A', screen: 'Marketplace' },
  { key: 'news',    label: 'Society News',  color: '#B06B5A', screen: 'News' },
  { key: 'profile', label: 'My Profile',    color: '#6A7D9B', screen: 'Profile' },
];

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning,';
  if (h < 17) return 'Good Afternoon,';
  return 'Good Evening,';
}

export default function HomeScreen({ ctx, navigate }: { ctx: any; navigate: (screen: string) => void }) {
  const insets = useSafeAreaInsets();
  const [approvals, setApprovals] = useState<any>({ entries: [], deliveries: [] });
  const firstName = ctx?.user?.name?.split(' ')[0] || 'Resident';
  const aptLabel = ctx?.apartment
    ? `${ctx.apartment.unit_number}, ${ctx?.society?.name || ''}`
    : 'No apartment set';
  const pendingCount = (approvals.entries?.length || 0) + (approvals.deliveries?.length || 0);

  useEffect(() => {
    api('/api/visitors/pending-approvals').then(setApprovals).catch(() => {});
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingTop: insets.top, paddingBottom: 100 }}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>{getGreeting()}</Text>
          <Text style={styles.name}>{firstName}</Text>
          <TouchableOpacity style={styles.locRow} onPress={() => navigate('Profile')}>
            <Text style={styles.locText}>📍 {aptLabel}</Text>
            <Text style={styles.locChevron}> ›</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.topRight}>
          <View style={styles.weatherPill}>
            <Text style={styles.weatherText}>☁️ 26°C</Text>
          </View>
          <TouchableOpacity style={styles.notifBtn} onPress={() => navigate('Visitors')}>
            <Text style={styles.notifIcon}>🔔</Text>
            {pendingCount > 0 && <View style={styles.notifDot} />}
          </TouchableOpacity>
          <TouchableOpacity style={styles.avatar} onPress={() => navigate('Profile')}>
            <Text style={styles.avatarText}>{firstName[0]}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Tile Grid */}
      <View style={styles.grid}>
        {TILES.map(t => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tile, { backgroundColor: t.color }]}
            onPress={() => navigate(t.screen)}
            activeOpacity={0.8}
          >
            <Text style={styles.tileEmoji}>
              {t.key === 'gate' ? '🛵' : t.key === 'booking' ? '🏊' : t.key === 'visitor' ? '👥'
                : t.key === 'market' ? '🛍️' : t.key === 'news' ? '📰' : '👤'}
            </Text>
            <Text style={styles.tileLabel}>{t.label}</Text>
            {t.key === 'gate' && pendingCount > 0 && (
              <View style={styles.tileBadge}>
                <Text style={styles.tileBadgeText}>{pendingCount} pending</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    paddingHorizontal: spacing.xl, paddingVertical: spacing.lg,
  },
  greeting: { fontSize: 13, color: colors.text2 },
  name: { fontSize: 26, fontWeight: '700', color: colors.white, marginVertical: 2 },
  locRow: { flexDirection: 'row', alignItems: 'center' },
  locText: { fontSize: 12, color: colors.text2 },
  locChevron: { fontSize: 12, color: colors.text2 },
  topRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  weatherPill: {
    backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 30,
    paddingHorizontal: 10, paddingVertical: 5,
  },
  weatherText: { fontSize: 12, fontWeight: '600', color: colors.text },
  notifBtn: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.08)',
    alignItems: 'center', justifyContent: 'center',
  },
  notifIcon: { fontSize: 16 },
  notifDot: {
    position: 'absolute', top: 6, right: 6,
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: colors.red, borderWidth: 1.5, borderColor: colors.bg,
  },
  avatar: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { fontSize: 14, fontWeight: '700', color: colors.white },
  grid: {
    flexDirection: 'row', flexWrap: 'wrap',
    paddingHorizontal: 20, gap: 10,
  },
  tile: {
    width: TILE_SIZE, height: TILE_SIZE, borderRadius: 20,
    padding: 16, justifyContent: 'flex-end', overflow: 'hidden',
  },
  tileEmoji: { fontSize: 40, position: 'absolute', top: 16, left: 16, opacity: 0.8 },
  tileLabel: { fontSize: 15, fontWeight: '600', color: colors.white },
  tileBadge: {
    position: 'absolute', top: 10, right: 10,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 20, paddingHorizontal: 8, paddingVertical: 2,
  },
  tileBadgeText: { fontSize: 10, fontWeight: '700', color: colors.white },
});
