import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, Image, Modal, Alert, FlatList,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Picker } from '@react-native-picker/picker';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props {
  navigation: any;
  prefill?: Record<string, string>;
}

export default function MarketplaceScreen({ navigation, prefill }: Props) {
  const [posts, setPosts] = useState<any[]>([]);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ postType: 'sell', title: '', description: '', price: '' });
  const [photos, setPhotos] = useState<string[]>([]);
  const [lightbox, setLightbox] = useState<{ images: string[]; index: number } | null>(null);

  const setF = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  useEffect(() => { api('/api/marketplace').then(setPosts); }, []);

  useEffect(() => {
    if (!prefill) return;
    const updates: Record<string, string> = {};
    if (prefill.postType) updates.postType = prefill.postType;
    if (prefill.title) updates.title = prefill.title;
    if (prefill.description) updates.description = prefill.description;
    if (prefill.price) updates.price = prefill.price;
    if (Object.keys(updates).length > 0) { setForm(f => ({ ...f, ...updates })); setModal(true); }
  }, [prefill]);

  const pickPhotos = async () => {
    if (photos.length >= 6) { Alert.alert('Max 6 photos'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      quality: 0.7,
      base64: true,
    });
    if (!result.canceled) {
      const newPhotos = result.assets
        .slice(0, 6 - photos.length)
        .map(a => `data:image/jpeg;base64,${a.base64}`);
      setPhotos(p => [...p, ...newPhotos]);
    }
  };

  const create = async () => {
    if (!form.title) { Alert.alert('Error', 'Title required'); return; }
    await api('/api/marketplace', {
      method: 'POST',
      body: JSON.stringify({ ...form, price: parseFloat(form.price) || 0, images: photos }),
    });
    api('/api/marketplace').then(setPosts);
    setModal(false);
    setForm({ postType: 'sell', title: '', description: '', price: '' });
    setPhotos([]);
  };

  return (
    <View style={styles.container}>
      <PageHeader title="Marketplace" onBack={() => navigation.goBack()} />
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModal(true)}>
          <Text style={styles.addBtnText}>+ New Listing</Text>
        </TouchableOpacity>

        {posts.map(p => (
          <Card key={p.id}>
            {p.images?.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.imageRow}>
                {p.images.map((img: string, i: number) => (
                  <TouchableOpacity key={i} onPress={() => setLightbox({ images: p.images, index: i })}>
                    <Image source={{ uri: img }} style={styles.postThumb} />
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{p.title}</Text>
                <Text style={styles.cardSub}>{p.description}</Text>
                <Text style={[styles.cardSub, { marginTop: 4 }]}>by {p.posted_by}</Text>
              </View>
              <View style={{ alignItems: 'flex-end', gap: 6 }}>
                <Text style={styles.price}>Rs.{p.price}</Text>
                <Badge label={p.post_type} variant={p.post_type === 'sell' ? 'purple' : 'orange'} />
              </View>
            </View>
          </Card>
        ))}
        {!posts.length && <Text style={styles.empty}>No listings in your society</Text>}
      </ScrollView>

      {/* Lightbox */}
      <Modal visible={!!lightbox} transparent animationType="fade" onRequestClose={() => setLightbox(null)}>
        <View style={styles.lightboxOverlay}>
          {lightbox && (
            <>
              <Image source={{ uri: lightbox.images[lightbox.index] }} style={styles.lightboxImage} resizeMode="contain" />
              <View style={styles.lightboxDots}>
                {lightbox.images.map((_: string, i: number) => (
                  <TouchableOpacity key={i} onPress={() => setLightbox(l => l ? { ...l, index: i } : l)}>
                    <View style={[styles.dot, i === lightbox.index && styles.dotActive]} />
                  </TouchableOpacity>
                ))}
              </View>
              <View style={styles.lightboxBtns}>
                <TouchableOpacity style={styles.lightboxBtn} onPress={() => setLightbox(l => l ? { ...l, index: Math.max(0, l.index - 1) } : l)}>
                  <Text style={styles.lightboxBtnText}>← Prev</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.lightboxBtn} onPress={() => setLightbox(l => l ? { ...l, index: Math.min(l.images.length - 1, l.index + 1) } : l)}>
                  <Text style={styles.lightboxBtnText}>Next →</Text>
                </TouchableOpacity>
              </View>
              <TouchableOpacity style={styles.lightboxClose} onPress={() => setLightbox(null)}>
                <Text style={styles.lightboxBtnText}>Close</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </Modal>

      {/* Create Post Modal */}
      <Modal visible={modal} transparent animationType="slide" onRequestClose={() => setModal(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setModal(false)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>New Listing</Text>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.label}>Photos (up to 6)</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 12 }}>
                {photos.map((src, i) => (
                  <View key={i} style={styles.thumbWrap}>
                    <Image source={{ uri: src }} style={styles.thumb} />
                    <TouchableOpacity style={styles.removeBtn} onPress={() => setPhotos(p => p.filter((_, idx) => idx !== i))}>
                      <Text style={styles.removeBtnText}>×</Text>
                    </TouchableOpacity>
                  </View>
                ))}
                {photos.length < 6 && (
                  <TouchableOpacity style={styles.addPhotoBtn} onPress={pickPhotos}>
                    <Text style={styles.addPhotoIcon}>📷</Text>
                    <Text style={styles.addPhotoText}>Add</Text>
                  </TouchableOpacity>
                )}
              </ScrollView>

              <Text style={styles.label}>Type</Text>
              <View style={styles.pickerWrap}>
                <Picker selectedValue={form.postType} onValueChange={v => setF('postType', v)} style={{ color: colors.text }} dropdownIconColor={colors.text2}>
                  <Picker.Item label="Sell" value="sell" color={colors.text} />
                  <Picker.Item label="Buy" value="buy" color={colors.text} />
                </Picker>
              </View>

              <Text style={styles.label}>Title *</Text>
              <TextInput style={styles.input} value={form.title} onChangeText={v => setF('title', v)} placeholder="e.g. Sofa for sale" placeholderTextColor={colors.text2} />

              <Text style={styles.label}>Description</Text>
              <TextInput style={[styles.input, { height: 80, textAlignVertical: 'top' }]} value={form.description} onChangeText={v => setF('description', v)} placeholder="Condition, details..." placeholderTextColor={colors.text2} multiline />

              <Text style={styles.label}>Price (Rs.)</Text>
              <TextInput style={styles.input} value={form.price} onChangeText={v => setF('price', v)} placeholder="0" placeholderTextColor={colors.text2} keyboardType="numeric" />

              <View style={styles.btnRow}>
                <TouchableOpacity style={styles.submitBtn} onPress={create}>
                  <Text style={styles.submitBtnText}>Post Listing</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.cancelBtn} onPress={() => setModal(false)}>
                  <Text style={styles.cancelBtnText}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
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
  addBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: 'center', marginBottom: 16 },
  addBtnText: { color: colors.white, fontSize: 14, fontWeight: '600' },
  imageRow: { marginBottom: 10 },
  postThumb: { width: 80, height: 80, borderRadius: 8, marginRight: 6 },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardSub: { fontSize: 12, color: colors.text2 },
  price: { fontSize: 15, fontWeight: '700', color: colors.green, fontFamily: 'monospace' },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  // Lightbox
  lightboxOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.95)', alignItems: 'center', justifyContent: 'center', padding: 20 },
  lightboxImage: { width: '100%', height: '60%' },
  lightboxDots: { flexDirection: 'row', gap: 8, marginTop: 16 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.3)' },
  dotActive: { backgroundColor: colors.white },
  lightboxBtns: { flexDirection: 'row', gap: 12, marginTop: 16 },
  lightboxBtn: { backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 8, paddingHorizontal: 20, paddingVertical: 10 },
  lightboxClose: { backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 8, paddingHorizontal: 20, paddingVertical: 10, marginTop: 8 },
  lightboxBtnText: { color: colors.white, fontSize: 14 },
  // Create modal
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: spacing.xl, paddingBottom: 36, maxHeight: '90%' },
  handle: { width: 40, height: 4, backgroundColor: colors.border, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  sheetTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 16 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6, marginTop: 4 },
  input: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12 },
  pickerWrap: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, marginBottom: 12 },
  thumbWrap: { position: 'relative', marginRight: 8 },
  thumb: { width: 72, height: 72, borderRadius: 10 },
  removeBtn: { position: 'absolute', top: 2, right: 2, width: 20, height: 20, borderRadius: 10, backgroundColor: 'rgba(0,0,0,0.7)', alignItems: 'center', justifyContent: 'center' },
  removeBtnText: { color: colors.white, fontSize: 14, lineHeight: 18 },
  addPhotoBtn: { width: 72, height: 72, borderRadius: 10, borderWidth: 2, borderStyle: 'dashed', borderColor: colors.border, alignItems: 'center', justifyContent: 'center' },
  addPhotoIcon: { fontSize: 24 },
  addPhotoText: { fontSize: 10, color: colors.text2, marginTop: 2 },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  submitBtn: { flex: 1, backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: 'center' },
  submitBtnText: { color: colors.white, fontSize: 14, fontWeight: '600' },
  cancelBtn: { flex: 1, backgroundColor: colors.card2, borderRadius: 10, padding: 14, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  cancelBtnText: { color: colors.text, fontSize: 14, fontWeight: '600' },
});
