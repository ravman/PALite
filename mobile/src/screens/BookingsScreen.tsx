import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput, StyleSheet, Alert,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props {
  navigation: any;
  prefill?: Record<string, string>;
}

const SPACE_ICONS: Record<string, string> = {
  gym: '🏋️', pool: '🏊', clubhouse: '🎉', tennis: '🎾', badminton: '🏸',
  yoga: '🧘', dance: '💃', party_hall: '🎊', library: '📚', other: '📅',
};
const AVATAR_COLORS = ['#6C8EF0', '#7EC8A4', '#E8A87C', '#C9A0DC', '#5BA3C9'];

function spaceColor(name: string) {
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

function fmtTime(t: string) {
  if (!t) return '';
  const [h, m] = t.split(':');
  const hh = parseInt(h); const ampm = hh >= 12 ? 'PM' : 'AM';
  return `${hh === 0 ? 12 : hh > 12 ? hh - 12 : hh}:${m} ${ampm}`;
}

function statusColors(s: string) {
  if (s === 'confirmed') return { color: '#3CB371', borderColor: '#3CB371', bg: 'rgba(60,179,113,.12)' };
  if (s === 'pending')   return { color: '#E8A020', borderColor: '#E8A020', bg: 'rgba(232,160,32,.12)' };
  return { color: '#E05555', borderColor: '#E05555', bg: 'rgba(224,85,85,.12)' };
}

function buildDateStrip() {
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(); d.setDate(d.getDate() + i);
    days.push({ label: i === 0 ? 'Today' : String(d.getDate()), value: d.toISOString().split('T')[0] });
  }
  return days;
}

export default function BookingsScreen({ navigation, prefill }: Props) {
  const [spaces, setSpaces]     = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [tab, setTab]           = useState<'activities' | 'browse' | 'book'>('activities');
  const [spaceFilter, setSpaceFilter] = useState('');
  const [booking, setBooking]   = useState<any>({ spaceId: '', date: '', startTime: '', endTime: '', spotNumber: 1 });
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const dateStrip = buildDateStrip();

  useEffect(() => {
    api('/api/spaces').then(setSpaces);
    api('/api/bookings/my').then(setBookings);
  }, []);

  useEffect(() => {
    if (!prefill) return;
    if (prefill.spaceSearch) setSpaceFilter(prefill.spaceSearch.toLowerCase());
    if (prefill.date || prefill.startTime || prefill.endTime) {
      setTab('book');
      setBooking((b: any) => ({ ...b, date: prefill.date || b.date, startTime: prefill.startTime || b.startTime, endTime: prefill.endTime || b.endTime }));
    }
  }, [prefill]);

  const bookedDays = new Set(bookings.map((b: any) => b.booking_date));
  const dayBookings = bookings.filter((b: any) => b.booking_date === selectedDate);
  const filteredSpaces = spaces.filter(s => !spaceFilter || s.name.toLowerCase().includes(spaceFilter) || s.space_type?.toLowerCase().includes(spaceFilter));

  const bookSpace = async () => {
    if (!booking.spaceId || !booking.date || !booking.startTime || !booking.endTime) {
      Alert.alert('Error', 'Please fill all fields'); return;
    }
    const d = await api('/api/bookings', { method: 'POST', body: JSON.stringify(booking) });
    if (d.error) { Alert.alert('Error', d.error); return; }
    Alert.alert('Confirm Booking', `Total: Rs. ${d.totalCost}. Pay now?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Pay', onPress: async () => {
        const p = await api(`/api/bookings/${d.bookingId}/pay`, { method: 'POST' });
        Alert.alert('Paid!', `TXN: ${p.transactionId}`);
        api('/api/bookings/my').then(setBookings);
        setTab('activities');
      }},
    ]);
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>My Activities</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setTab('book')}>
          <Text style={styles.addBtnText}>+</Text>
        </TouchableOpacity>
      </View>

      {/* Tab bar */}
      <View style={[styles.tabBar, { gridTemplateColumns: tab === 'book' ? '1fr 1fr 1fr' : '1fr 1fr' }]}>
        {([['activities', 'Activities'], ['browse', 'Browse'], ...(tab === 'book' ? [['book', 'Book Now']] : [])] as [string, string][]).map(([k, l]) => (
          <TouchableOpacity key={k} style={[styles.tab, tab === k && styles.tabActive]} onPress={() => setTab(k as any)}>
            <Text style={[styles.tabText, tab === k && styles.tabTextActive]}>{l}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Activities tab */}
      {tab === 'activities' && (
        <>
          {/* Date strip */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dateStrip} contentContainerStyle={styles.dateStripContent}>
            <Text style={styles.dateStripIcon}>↺</Text>
            {dateStrip.map(d => {
              const hasDot = bookedDays.has(d.value);
              const active = selectedDate === d.value;
              return (
                <TouchableOpacity key={d.value} style={[styles.datePill, active && styles.datePillActive]} onPress={() => setSelectedDate(d.value)}>
                  <Text style={[styles.datePillText, active && styles.datePillTextActive]}>{d.label}</Text>
                  {hasDot && <View style={[styles.dateDot, { backgroundColor: active ? colors.white : colors.accent }]} />}
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
            {dayBookings.length === 0 && (
              <View style={styles.emptyState}>
                <Text style={styles.emptyIcon}>📅</Text>
                <Text style={styles.emptyText}>No activities on this day</Text>
                <TouchableOpacity style={styles.browseBtn} onPress={() => setTab('browse')}>
                  <Text style={styles.browseBtnText}>Browse Spaces</Text>
                </TouchableOpacity>
              </View>
            )}
            {dayBookings.map((b: any) => {
              const icon  = SPACE_ICONS[b.space_type] || '📅';
              const col   = spaceColor(b.space_name);
              const sc    = statusColors(b.status);
              const label = b.status === 'confirmed' ? 'Approved' : b.status === 'pending' ? 'Waiting' : 'Declined';
              return (
                <View key={b.id} style={styles.actCard}>
                  <View style={[styles.actIcon, { backgroundColor: col }]}>
                    <Text style={styles.actIconText}>{icon}</Text>
                  </View>
                  <View style={styles.actInfo}>
                    <Text style={styles.actName} numberOfLines={1}>{b.space_name}</Text>
                    <Text style={styles.actType}>{(b.space_type || '').replace('_', ' ')}</Text>
                  </View>
                  <View style={styles.actRight}>
                    <View style={[styles.statusBadge, { backgroundColor: sc.bg, borderColor: sc.borderColor }]}>
                      <Text style={[styles.statusText, { color: sc.color }]}>{label}</Text>
                    </View>
                    <Text style={styles.timeText}>⏱ {fmtTime(b.start_time)}</Text>
                  </View>
                </View>
              );
            })}
          </ScrollView>
        </>
      )}

      {/* Browse tab */}
      {tab === 'browse' && (
        <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search spaces..."
            placeholderTextColor={colors.text2}
            value={spaceFilter}
            onChangeText={t => setSpaceFilter(t.toLowerCase())}
          />
          {filteredSpaces.map(s => (
            <Card key={s.id} onPress={() => { setBooking({ spaceId: s.id, date: '', startTime: '', endTime: '', spotNumber: 1 }); setTab('book'); }}>
              <View style={styles.browseRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardTitle}>{s.name}</Text>
                  <Text style={styles.cardSub}>{s.description}</Text>
                </View>
                <Text style={styles.price}>Rs.{s.cost_per_hour}/hr</Text>
              </View>
            </Card>
          ))}
          {!filteredSpaces.length && <Text style={styles.empty}>No spaces found</Text>}
        </ScrollView>
      )}

      {/* Book tab */}
      {tab === 'book' && (
        <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
          <Text style={styles.label}>Space</Text>
          <View style={styles.pickerWrap}>
            <Picker selectedValue={booking.spaceId} onValueChange={v => setBooking((b: any) => ({ ...b, spaceId: v }))} style={{ color: colors.text }} dropdownIconColor={colors.text2}>
              <Picker.Item label="Select space..." value="" color={colors.text2} />
              {spaces.map(s => <Picker.Item key={s.id} label={`${s.name} – Rs.${s.cost_per_hour}/hr`} value={s.id} color={colors.text} />)}
            </Picker>
          </View>
          <Text style={styles.label}>Date (YYYY-MM-DD)</Text>
          <TextInput style={styles.input} value={booking.date} onChangeText={v => setBooking((b: any) => ({ ...b, date: v }))} placeholder="e.g. 2026-03-15" placeholderTextColor={colors.text2} />
          <View style={styles.grid2}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>Start</Text>
              <TextInput style={styles.input} value={booking.startTime} onChangeText={v => setBooking((b: any) => ({ ...b, startTime: v }))} placeholder="06:00" placeholderTextColor={colors.text2} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>End</Text>
              <TextInput style={styles.input} value={booking.endTime} onChangeText={v => setBooking((b: any) => ({ ...b, endTime: v }))} placeholder="07:00" placeholderTextColor={colors.text2} />
            </View>
          </View>
          <TouchableOpacity style={styles.bookBtn} onPress={bookSpace}>
            <Text style={styles.bookBtnText}>Book & Pay</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.xl, paddingTop: spacing.xl, paddingBottom: spacing.md },
  backBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.card2, alignItems: 'center', justifyContent: 'center' },
  backBtnText: { color: colors.text, fontSize: 22, fontWeight: '700', lineHeight: 26 },
  headerTitle: { fontSize: 20, fontWeight: '700', color: colors.text },
  addBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  addBtnText: { color: colors.white, fontSize: 22, fontWeight: '700', lineHeight: 26 },
  tabBar: { flexDirection: 'row', marginHorizontal: spacing.xl, marginBottom: spacing.md, backgroundColor: colors.card2, borderRadius: radius.lg, padding: 3, gap: 2 },
  tab: { flex: 1, paddingVertical: 9, borderRadius: 11, alignItems: 'center' },
  tabActive: { backgroundColor: colors.accent },
  tabText: { fontSize: 13, fontWeight: '600', color: colors.text2 },
  tabTextActive: { color: colors.white },
  dateStrip: { flexGrow: 0 },
  dateStripContent: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: spacing.xl, paddingBottom: spacing.md, gap: 8 },
  dateStripIcon: { fontSize: 16, color: colors.text2 },
  datePill: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.full, backgroundColor: colors.card2, position: 'relative', alignItems: 'center' },
  datePillActive: { backgroundColor: colors.accent },
  datePillText: { fontSize: 13, fontWeight: '600', color: colors.text },
  datePillTextActive: { color: colors.white },
  dateDot: { position: 'absolute', bottom: 2, width: 4, height: 4, borderRadius: 2 },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 60 },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyText: { fontSize: 14, color: colors.text2, marginBottom: 12 },
  browseBtn: { paddingHorizontal: 20, paddingVertical: 8, borderRadius: radius.full, backgroundColor: colors.accent },
  browseBtnText: { color: colors.white, fontSize: 13, fontWeight: '600' },
  actCard: { backgroundColor: colors.card2, borderRadius: radius.lg, marginBottom: 10, flexDirection: 'row', alignItems: 'center', gap: 12, padding: spacing.md, borderWidth: 1, borderColor: colors.border },
  actIcon: { width: 50, height: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  actIconText: { fontSize: 24 },
  actInfo: { flex: 1 },
  actName: { fontSize: 15, fontWeight: '700', color: colors.text, marginBottom: 2 },
  actType: { fontSize: 12, color: colors.text2, textTransform: 'capitalize' },
  actRight: { alignItems: 'flex-end', gap: 5 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: radius.full, borderWidth: 1 },
  statusText: { fontSize: 11, fontWeight: '700' },
  timeText: { fontSize: 11, color: colors.text2 },
  browseRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardSub: { fontSize: 12, color: colors.text2 },
  price: { fontSize: 14, fontWeight: '700', color: colors.accent },
  searchInput: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6, marginTop: 4 },
  input: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12 },
  pickerWrap: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, marginBottom: 12 },
  grid2: { flexDirection: 'row', gap: 10 },
  bookBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 8 },
  bookBtnText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
});
