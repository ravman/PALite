import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Image, Modal,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

const CATEGORIES = [
  { key: 'all',         label: 'All',         color: '#6C8EF0', bg: 'rgba(108,142,240,.15)' },
  { key: 'society',     label: 'Society',     color: '#4CAF7D', bg: 'rgba(76,175,125,.12)'  },
  { key: 'events',      label: 'Events',      color: '#E05555', bg: 'rgba(224,85,85,.12)'   },
  { key: 'maintenance', label: 'Maintenance', color: '#E8A020', bg: 'rgba(232,160,32,.12)'  },
];

function timeAgo(dt: string) {
  const diff = (Date.now() - new Date(dt).getTime()) / 1000;
  if (diff < 60)    return 'just now';
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function catStyle(key: string) {
  const c = CATEGORIES.find(x => x.key === key) || CATEGORIES[1];
  return { color: c.color, bg: c.bg, border: c.color + '55' };
}

function catEmoji(key: string) {
  if (key === 'events') return '🎉';
  if (key === 'maintenance') return '🔧';
  return '📢';
}

export default function NewsScreen({ navigation }: { navigation: any }) {
  const [news, setNews]         = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);
  const [category, setCategory] = useState('all');
  const [selected, setSelected] = useState<any>(null);

  useEffect(() => {
    api('/api/news').then(d => { setNews(Array.isArray(d) ? d : []); setLoading(false); });
  }, []);

  const filtered = category === 'all' ? news : news.filter(n => (n.category || 'society') === category);

  return (
    <View style={styles.container}>
      <PageHeader title="News" onBack={() => navigation.goBack()} />

      {/* Category pills */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.pillsRow} contentContainerStyle={styles.pillsContent}>
        {CATEGORIES.map(c => {
          const active = category === c.key;
          return (
            <TouchableOpacity
              key={c.key}
              style={[styles.pill, { borderColor: active ? c.color : colors.border, backgroundColor: active ? c.bg : 'transparent' }]}
              onPress={() => setCategory(c.key)}
            >
              <Text style={[styles.pillText, { color: active ? c.color : colors.text2 }]}>{c.label}</Text>
              {active && c.key !== 'all' && <View style={[styles.pillDot, { backgroundColor: c.color }]} />}
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* List */}
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {loading && <Text style={styles.empty}>Loading…</Text>}
        {!loading && filtered.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📰</Text>
            <Text style={styles.empty}>No {category === 'all' ? '' : category} announcements yet</Text>
          </View>
        )}
        {filtered.map(n => {
          const thumb = n.images && n.images.length > 0 ? n.images[0] : null;
          const cat   = n.category || 'society';
          const cs    = catStyle(cat);
          return (
            <TouchableOpacity key={n.id} style={styles.card} onPress={() => setSelected(n)} activeOpacity={0.75}>
              {/* Thumbnail */}
              <View style={styles.thumb}>
                {thumb
                  ? <Image source={{ uri: thumb }} style={styles.thumbImg} />
                  : <Text style={styles.thumbEmoji}>{catEmoji(cat)}</Text>}
              </View>
              {/* Text */}
              <View style={styles.cardBody}>
                {n.is_pinned ? <Text style={styles.pinned}>📌 PINNED</Text> : null}
                <Text style={styles.cardTitle} numberOfLines={1}>{n.title}</Text>
                <View style={styles.cardMeta}>
                  <View style={[styles.catBadge, { backgroundColor: cs.bg, borderColor: cs.border }]}>
                    <Text style={[styles.catBadgeText, { color: cs.color }]}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</Text>
                  </View>
                  <Text style={styles.timeText}>⏱ {timeAgo(n.created_at)}</Text>
                </View>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Detail sheet */}
      <Modal visible={!!selected} transparent animationType="slide" onRequestClose={() => setSelected(null)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setSelected(null)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            {selected?.images?.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
                {selected.images.map((p: string, i: number) => (
                  <Image key={i} source={{ uri: p }} style={styles.detailPhoto} />
                ))}
              </ScrollView>
            )}
            <Text style={styles.sheetTitle}>{selected?.title}</Text>
            <Text style={styles.sheetMeta}>{selected?.author_name} · {timeAgo(selected?.created_at || '')}</Text>
            {selected?.body ? <Text style={styles.sheetBody}>{selected.body}</Text> : null}
            <TouchableOpacity style={styles.closeBtn} onPress={() => setSelected(null)}>
              <Text style={styles.closeBtnText}>Close</Text>
            </TouchableOpacity>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  pillsRow: { flexGrow: 0 },
  pillsContent: { flexDirection: 'row', paddingHorizontal: spacing.xl, paddingBottom: spacing.md, gap: 8 },
  pill: { paddingHorizontal: 18, paddingVertical: 7, borderRadius: radius.full, borderWidth: 1, position: 'relative' },
  pillText: { fontSize: 13, fontWeight: '600' },
  pillDot: { position: 'absolute', bottom: -2, alignSelf: 'center', width: 5, height: 5, borderRadius: 3 },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 60 },
  card: { backgroundColor: colors.card2, borderRadius: radius.lg, marginBottom: 10, padding: spacing.md, flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 1, borderColor: colors.border },
  thumb: { width: 60, height: 60, borderRadius: 12, overflow: 'hidden', backgroundColor: colors.card, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  thumbImg: { width: '100%', height: '100%' },
  thumbEmoji: { fontSize: 26 },
  cardBody: { flex: 1 },
  pinned: { fontSize: 10, color: colors.accent, fontWeight: '700', marginBottom: 2 },
  cardTitle: { fontSize: 14, fontWeight: '700', color: colors.text, marginBottom: 5 },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  catBadge: { paddingHorizontal: 9, paddingVertical: 2, borderRadius: radius.full, borderWidth: 1 },
  catBadgeText: { fontSize: 11, fontWeight: '600' },
  timeText: { fontSize: 11, color: colors.text2 },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyIcon: { fontSize: 36, marginBottom: 12 },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: spacing.xl, paddingBottom: 36, maxHeight: '85%' },
  handle: { width: 40, height: 4, backgroundColor: colors.border, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  detailPhoto: { width: 200, height: 140, borderRadius: 10, marginRight: 8 },
  sheetTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 4 },
  sheetMeta: { fontSize: 12, color: colors.text2, marginBottom: 12 },
  sheetBody: { fontSize: 14, color: colors.text, lineHeight: 22 },
  closeBtn: { backgroundColor: colors.card2, borderRadius: 10, padding: 12, alignItems: 'center', marginTop: 16, borderWidth: 1, borderColor: colors.border },
  closeBtnText: { color: colors.text, fontSize: 14, fontWeight: '600' },
});
