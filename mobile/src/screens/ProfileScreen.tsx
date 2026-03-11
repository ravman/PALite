import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import FormModal from '../components/FormModal';
import { api, clearToken } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props { navigation: any; ctx: any; onLogout: () => void; switchApt: (id: string) => void; }

export default function ProfileScreen({ navigation, ctx, onLogout, switchApt }: Props) {
  const [profile, setProfile] = useState<any>(null);
  const [tab, setTab] = useState<'info' | 'vehicles' | 'pets' | 'family' | 'invoices' | 'moves'>('info');
  const [modal, setModal] = useState<'vehicle' | 'pet' | 'family' | 'move' | null>(null);
  const [moves, setMoves] = useState<any[]>([]);

  const loadProfile = () => api('/api/residents/profile').then(setProfile);
  const loadMoves   = () => api('/api/move-requests/my').then(d => setMoves(Array.isArray(d) ? d : []));

  useEffect(() => { loadProfile(); loadMoves(); }, []);

  const addVehicle = async (d: any) => {
    await api('/api/residents/vehicles', { method: 'POST', body: JSON.stringify(d) });
    loadProfile(); setModal(null);
  };
  const addPet = async (d: any) => {
    await api('/api/residents/pets', { method: 'POST', body: JSON.stringify(d) });
    loadProfile(); setModal(null);
  };
  const inviteFamily = async (d: any) => {
    await api('/api/residents/invite-family', { method: 'POST', body: JSON.stringify(d) });
    loadProfile(); setModal(null);
  };
  const createMove = async (d: any) => {
    await api('/api/move-requests', { method: 'POST', body: JSON.stringify({ ...d, documents: [] }) });
    loadMoves(); setModal(null);
  };

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: async () => { await clearToken(); onLogout(); } },
    ]);
  };

  if (!profile) return <View style={styles.container}><Text style={{ color: colors.text2, padding: 40 }}>Loading...</Text></View>;

  const TABS = ['info', 'vehicles', 'pets', 'family', 'moves', 'invoices'] as const;

  return (
    <View style={styles.container}>
      <PageHeader title="My Profile" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={styles.content}>
        <Card>
          <Text style={styles.name}>{profile.user.name}</Text>
          <Text style={styles.cardSub}>{profile.user.phone} • {profile.user.email || 'No email'}</Text>
        </Card>

        {profile.residencies.length > 1 && (
          <>
            <Text style={styles.sectionTitle}>My Properties</Text>
            {profile.residencies.map((r: any) => (
              <Card key={r.id} onPress={() => switchApt(r.apartment_id)} style={{ borderColor: r.apartment_id === ctx?.activeApartment ? colors.accent : colors.border }}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{r.unit_number} – {r.tower_name}</Text>
                    <Text style={styles.cardSub}>{r.society_name}</Text>
                  </View>
                  <Badge label={r.resident_type} variant={r.status === 'approved' ? 'green' : 'orange'} />
                </View>
              </Card>
            ))}
          </>
        )}

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabBar} contentContainerStyle={{ gap: 6 }}>
          {TABS.map(t => (
            <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
              <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>{t.charAt(0).toUpperCase() + t.slice(1)}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {tab === 'info' && (
          <>
            <Card>
              <Text style={styles.cardTitle}>Current Residence</Text>
              <Text style={styles.cardSub}>{ctx?.apartment?.unit_number} • {ctx?.tower?.name} • {ctx?.society?.name}</Text>
              {ctx?.resident && <Badge label={`${ctx.resident.resident_type} – ${ctx.resident.status}`} variant={ctx.resident.status === 'approved' ? 'green' : 'orange'} />}
            </Card>
            <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
              <Text style={styles.logoutText}>Sign Out</Text>
            </TouchableOpacity>
          </>
        )}

        {tab === 'vehicles' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('vehicle')}>
              <Text style={styles.addBtnText}>+ Add Vehicle</Text>
            </TouchableOpacity>
            {profile.vehicles.map((v: any) => (
              <Card key={v.id}>
                <Text style={styles.cardTitle}>{v.make} {v.model}</Text>
                <Text style={styles.cardSub}>{v.registration_number} • {v.color} {v.vehicle_type}</Text>
              </Card>
            ))}
            {!profile.vehicles.length && <Text style={styles.empty}>No vehicles registered</Text>}
          </>
        )}

        {tab === 'pets' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('pet')}>
              <Text style={styles.addBtnText}>+ Add Pet</Text>
            </TouchableOpacity>
            {profile.pets.map((p: any) => (
              <Card key={p.id}>
                <Text style={styles.cardTitle}>{p.name}</Text>
                <Text style={styles.cardSub}>{p.breed} • {p.pet_type} • {p.age_years}yrs • {p.vaccinated ? 'Vaccinated' : 'Not vaccinated'}</Text>
              </Card>
            ))}
            {!profile.pets.length && <Text style={styles.empty}>No pets registered</Text>}
          </>
        )}

        {tab === 'family' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('family')}>
              <Text style={styles.addBtnText}>+ Invite Family</Text>
            </TouchableOpacity>
            {[...profile.family, ...profile.tenants].map((f: any) => (
              <Card key={f.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{f.name}</Text>
                    <Text style={styles.cardSub}>{f.phone} • {f.resident_type}</Text>
                  </View>
                  <Badge label={f.status} variant={f.status === 'approved' ? 'green' : 'orange'} />
                </View>
              </Card>
            ))}
            {!profile.family.length && !profile.tenants.length && <Text style={styles.empty}>No family or tenants</Text>}
          </>
        )}

        {tab === 'invoices' && (
          <>
            {profile.invoices.map((i: any) => (
              <Card key={i.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{i.description}</Text>
                    <Text style={styles.cardSub}>Rs. {i.amount}</Text>
                  </View>
                  <Badge label={i.status} variant={i.status === 'paid' ? 'green' : 'orange'} />
                </View>
              </Card>
            ))}
            {!profile.invoices.length && <Text style={styles.empty}>No invoices</Text>}
          </>
        )}

        {tab === 'moves' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('move')}>
              <Text style={styles.addBtnText}>+ Request Move In/Out</Text>
            </TouchableOpacity>
            {moves.map((m: any) => (
              <Card key={m.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{m.move_type === 'move_in' ? '📦 Move In' : '🚚 Move Out'}</Text>
                    <Text style={styles.cardSub}>{m.tentative_start} → {m.tentative_end}</Text>
                  </View>
                  <Badge label={m.status} variant={m.status === 'approved' ? 'green' : m.status === 'pending' ? 'orange' : 'red'} />
                </View>
                {m.status === 'rejected' && m.rejection_reason ? (
                  <View style={styles.rejectBox}>
                    <Text style={styles.rejectLabel}>Reason</Text>
                    <Text style={styles.rejectText}>{m.rejection_reason}</Text>
                  </View>
                ) : null}
              </Card>
            ))}
            {!moves.length && <Text style={styles.empty}>No move requests yet</Text>}
          </>
        )}
      </ScrollView>

      <FormModal visible={modal === 'vehicle'} title="Add Vehicle"
        fields={[{ key: 'vehicleType', label: 'Type', type: 'select', options: ['car', 'bike', 'scooter', 'bicycle'] }, { key: 'make', label: 'Make' }, { key: 'model', label: 'Model' }, { key: 'color', label: 'Color' }, { key: 'registrationNumber', label: 'Registration No.' }]}
        onClose={() => setModal(null)} onSubmit={addVehicle} />

      <FormModal visible={modal === 'pet'} title="Add Pet"
        fields={[{ key: 'petType', label: 'Type', type: 'select', options: ['dog', 'cat', 'bird', 'fish', 'other'] }, { key: 'name', label: 'Name' }, { key: 'breed', label: 'Breed' }, { key: 'ageYears', label: 'Age (years)', type: 'number' }]}
        onClose={() => setModal(null)} onSubmit={addPet} />

      <FormModal visible={modal === 'move'} title="Move Request"
        fields={[
          { key: 'moveType', label: 'Type', type: 'select', options: ['move_in', 'move_out'] },
          { key: 'tentativeStart', label: 'Start Date (YYYY-MM-DD)' },
          { key: 'tentativeEnd', label: 'End Date (YYYY-MM-DD)' },
          { key: 'notes', label: 'Notes' },
        ]}
        onClose={() => setModal(null)} onSubmit={createMove} />

      <FormModal visible={modal === 'family'} title="Invite Family Member"
        fields={[{ key: 'name', label: 'Name' }, { key: 'phone', label: 'Phone' }]}
        onClose={() => setModal(null)} onSubmit={inviteFamily} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.xl, paddingBottom: 60 },
  name: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardSub: { fontSize: 12, color: colors.text2 },
  sectionTitle: { fontSize: 13, fontWeight: '600', color: colors.text2, marginBottom: 8, marginTop: 4 },
  tabBar: { marginVertical: 12 },
  tab: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { fontSize: 12, fontWeight: '600', color: colors.text2 },
  tabTextActive: { color: colors.white },
  row: { flexDirection: 'row', alignItems: 'center' },
  addBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 12, alignItems: 'center', marginBottom: 12 },
  addBtnText: { color: colors.white, fontSize: 13, fontWeight: '600' },
  logoutBtn: { backgroundColor: colors.card2, borderRadius: 10, padding: 14, alignItems: 'center', marginTop: 8, borderWidth: 1, borderColor: colors.border },
  logoutText: { color: colors.text, fontSize: 14, fontWeight: '600' },
  empty: { textAlign: 'center', color: colors.text2, padding: 20 },
  rejectBox: { marginTop: 10, padding: 10, backgroundColor: 'rgba(225,112,85,.1)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(225,112,85,.25)' },
  rejectLabel: { fontSize: 11, fontWeight: '700', color: colors.red, marginBottom: 2 },
  rejectText: { fontSize: 13, color: colors.red },
});
