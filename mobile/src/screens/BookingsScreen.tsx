import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, Alert,
} from 'react-native';
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

export default function BookingsScreen({ navigation, prefill }: Props) {
  const [spaces, setSpaces] = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [tab, setTab] = useState<'spaces' | 'my' | 'book'>('spaces');
  const [spaceFilter, setSpaceFilter] = useState('');
  const [booking, setBooking] = useState<any>({ spaceId: '', date: '', startTime: '', endTime: '', spotNumber: 1 });

  useEffect(() => {
    api('/api/spaces').then(setSpaces);
    api('/api/bookings/my').then(setBookings);
  }, []);

  useEffect(() => {
    if (!prefill) return;
    if (prefill.spaceSearch) setSpaceFilter(prefill.spaceSearch.toLowerCase());
    if (prefill.date || prefill.startTime || prefill.endTime) {
      setTab('book');
      setBooking((b: any) => ({
        ...b,
        date: prefill.date || b.date,
        startTime: prefill.startTime || b.startTime,
        endTime: prefill.endTime || b.endTime,
      }));
    }
  }, [prefill]);

  const filteredSpaces = spaces.filter(s =>
    !spaceFilter || s.name.toLowerCase().includes(spaceFilter) || s.space_type?.toLowerCase().includes(spaceFilter)
  );

  const bookSpace = async () => {
    if (!booking.spaceId || !booking.date || !booking.startTime || !booking.endTime) {
      Alert.alert('Error', 'Please fill all fields'); return;
    }
    const d = await api('/api/bookings', { method: 'POST', body: JSON.stringify(booking) });
    if (d.error) { Alert.alert('Error', d.error); return; }
    Alert.alert('Confirm Booking', `Total: Rs. ${d.totalCost}. Pay now?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Pay', onPress: async () => {
          const p = await api(`/api/bookings/${d.bookingId}/pay`, { method: 'POST' });
          Alert.alert('Paid!', `TXN: ${p.transactionId}`);
          api('/api/bookings/my').then(setBookings);
          setTab('my');
        }
      }
    ]);
  };

  const TABS = [
    { key: 'spaces', label: 'Spaces' },
    { key: 'my', label: 'My Bookings' },
    { key: 'book', label: 'Book Now' },
  ] as const;

  return (
    <View style={styles.container}>
      <PageHeader title="Bookings" onBack={() => navigation.goBack()} />
      <View style={styles.tabBar}>
        {TABS.map(t => (
          <TouchableOpacity key={t.key} style={[styles.tab, tab === t.key && styles.tabActive]} onPress={() => setTab(t.key)}>
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>{t.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {tab === 'spaces' && (
          <>
            <TextInput
              style={styles.searchInput}
              placeholder="Search spaces..."
              placeholderTextColor={colors.text2}
              value={spaceFilter}
              onChangeText={t => setSpaceFilter(t.toLowerCase())}
            />
            {filteredSpaces.map(s => (
              <Card key={s.id} onPress={() => { setBooking({ spaceId: s.id, date: prefill?.date || '', startTime: prefill?.startTime || '', endTime: prefill?.endTime || '', spotNumber: 1 }); setTab('book'); }}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{s.name}</Text>
                    <Text style={styles.cardSub}>{s.description}</Text>
                    <Text style={styles.cardSub}>{s.available_from} – {s.available_to} • Cap: {s.capacity}</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={styles.price}>Rs.{s.cost_per_hour}/hr</Text>
                    {s.is_shared && <Text style={styles.cardSub}>{s.total_spots} spots</Text>}
                  </View>
                </View>
              </Card>
            ))}
            {!filteredSpaces.length && <Text style={styles.empty}>No spaces found</Text>}
          </>
        )}

        {tab === 'my' && (
          <>
            {bookings.map(b => (
              <Card key={b.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{b.space_name}</Text>
                    <Text style={styles.cardSub}>{b.booking_date} {b.start_time}–{b.end_time}</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 6 }}>
                    <Text style={styles.price}>Rs.{b.total_cost}</Text>
                    <Badge label={b.status} variant={b.status === 'confirmed' ? 'green' : b.status === 'pending' ? 'orange' : 'red'} />
                    {b.invoice_status === 'unpaid' && (
                      <TouchableOpacity style={styles.payBtn} onPress={() => api(`/api/bookings/${b.id}/pay`, { method: 'POST' }).then(() => api('/api/bookings/my').then(setBookings))}>
                        <Text style={styles.payBtnText}>Pay</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              </Card>
            ))}
            {!bookings.length && <Text style={styles.empty}>No bookings yet</Text>}
          </>
        )}

        {tab === 'book' && (
          <>
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
                <Text style={styles.label}>Start time</Text>
                <TextInput style={styles.input} value={booking.startTime} onChangeText={v => setBooking((b: any) => ({ ...b, startTime: v }))} placeholder="06:00" placeholderTextColor={colors.text2} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.label}>End time</Text>
                <TextInput style={styles.input} value={booking.endTime} onChangeText={v => setBooking((b: any) => ({ ...b, endTime: v }))} placeholder="07:00" placeholderTextColor={colors.text2} />
              </View>
            </View>

            <TouchableOpacity style={styles.bookBtn} onPress={bookSpace}>
              <Text style={styles.bookBtnText}>Book & Pay</Text>
            </TouchableOpacity>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  tabBar: { flexDirection: 'row', gap: 6, paddingHorizontal: spacing.xl, marginBottom: 4 },
  tab: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { fontSize: 12, fontWeight: '600', color: colors.text2 },
  tabTextActive: { color: colors.white },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 40 },
  searchInput: {
    backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12,
  },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardSub: { fontSize: 12, color: colors.text2, marginTop: 2 },
  price: { fontSize: 16, fontWeight: '700', color: colors.accent2, fontFamily: 'monospace' },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6, marginTop: 4 },
  input: {
    backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12,
  },
  pickerWrap: {
    backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.sm, marginBottom: 12,
  },
  grid2: { flexDirection: 'row', gap: 10 },
  bookBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 8 },
  bookBtnText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  payBtn: { backgroundColor: colors.accent, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 4 },
  payBtnText: { color: colors.white, fontSize: 11, fontWeight: '600' },
});
