import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, Image, Modal } from 'react-native';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

export default function NewsScreen({ navigation }: { navigation: any }) {
  const [news, setNews] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);

  useEffect(() => { api('/api/news').then(d => setNews(Array.isArray(d) ? d : [])); }, []);

  const categoryColor: Record<string, string> = {
    announcement: 'purple', event: 'green', alert: 'red', maintenance: 'orange',
  };

  return (
    <View style={styles.container}>
      <PageHeader title="Society News" onBack={() => navigation.goBack()} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {news.length === 0 && <Text style={styles.empty}>No announcements yet</Text>}
        {news.map(n => (
          <Card key={n.id} onPress={() => setSelected(n)}>
            {n.photos?.length > 0 && (
              <Image source={{ uri: n.photos[0] }} style={styles.newsImage} />
            )}
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{n.title}</Text>
                <Text style={styles.cardSub} numberOfLines={2}>{n.content}</Text>
                <Text style={styles.cardSub}>{n.created_at?.split('T')[0]}</Text>
              </View>
              <Badge label={n.category || 'news'} variant={categoryColor[n.category] || 'purple'} />
            </View>
          </Card>
        ))}
      </ScrollView>

      <Modal visible={!!selected} transparent animationType="slide" onRequestClose={() => setSelected(null)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setSelected(null)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            {selected?.photos?.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
                {selected.photos.map((p: string, i: number) => (
                  <Image key={i} source={{ uri: p }} style={styles.detailPhoto} />
                ))}
              </ScrollView>
            )}
            <View style={styles.row}>
              <Text style={styles.sheetTitle}>{selected?.title}</Text>
              <Badge label={selected?.category || 'news'} variant={categoryColor[selected?.category] || 'purple'} />
            </View>
            <Text style={styles.cardSub}>{selected?.created_at?.split('T')[0]} · {selected?.author_name}</Text>
            <Text style={styles.newsContent}>{selected?.content}</Text>
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
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 40 },
  newsImage: { width: '100%', height: 140, borderRadius: 10, marginBottom: 10 },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4, flex: 1 },
  cardSub: { fontSize: 12, color: colors.text2, marginTop: 2 },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: spacing.xl, paddingBottom: 36, maxHeight: '85%' },
  handle: { width: 40, height: 4, backgroundColor: colors.border, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  detailPhoto: { width: 200, height: 140, borderRadius: 10, marginRight: 8 },
  sheetTitle: { fontSize: 18, fontWeight: '700', color: colors.text, flex: 1 },
  newsContent: { fontSize: 14, color: colors.text, lineHeight: 22, marginTop: 12 },
  closeBtn: { backgroundColor: colors.card2, borderRadius: 10, padding: 12, alignItems: 'center', marginTop: 16, borderWidth: 1, borderColor: colors.border },
  closeBtnText: { color: colors.text, fontSize: 14, fontWeight: '600' },
});
