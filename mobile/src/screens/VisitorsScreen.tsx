import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import FormModal from '../components/FormModal';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props {
  navigation: any;
  prefill?: Record<string, string>;
  ctx?: any;
}

export default function VisitorsScreen({ navigation, prefill, ctx }: Props) {
  const [invites, setInvites] = useState<any[]>([]);
  const [moves, setMoves] = useState<any[]>([]);
  const [tab, setTab] = useState<'invitations' | 'moves'>('invitations');
  const [modal, setModal] = useState<'invite' | 'move' | null>(null);
  const [invitePrefill, setInvitePrefill] = useState<Record<string, string>>({});

  useEffect(() => {
    api('/api/visitors/my-invitations').then(setInvites);
    api('/api/move-requests/my').then(setMoves);
  }, []);

  useEffect(() => {
    if (!prefill) return;
    const fields: Record<string, string> = {};
    if (prefill.visitorName) fields.visitorName = prefill.visitorName;
    if (prefill.visitorPhone) fields.visitorPhone = prefill.visitorPhone;
    if (prefill.visitorType) fields.visitorType = prefill.visitorType;
    if (prefill.purpose) fields.purpose = prefill.purpose;
    if (Object.keys(fields).length > 0) { setInvitePrefill(fields); setModal('invite'); }
  }, [prefill]);

  const createInvite = async (d: Record<string, string>) => {
    const r = await api('/api/visitors/invite', { method: 'POST', body: JSON.stringify(d) });
    if (r.qrCode) Alert.alert('Invite Created', `QR Code: ${r.qrCode}`);
    api('/api/visitors/my-invitations').then(setInvites);
    setModal(null);
  };

  const createMove = async (d: Record<string, string>) => {
    await api('/api/move-requests', { method: 'POST', body: JSON.stringify(d) });
    api('/api/move-requests/my').then(setMoves);
    setModal(null);
  };

  return (
    <View style={styles.container}>
      <PageHeader title="Visitors & Moves" onBack={() => navigation.goBack()} />
      <View style={styles.tabBar}>
        {(['invitations', 'moves'] as const).map(t => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t === 'invitations' ? 'Invitations' : 'Move Requests'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {tab === 'invitations' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('invite')}>
              <Text style={styles.addBtnText}>+ Create Invitation</Text>
            </TouchableOpacity>
            {invites.map(i => (
              <Card key={i.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{i.visitor_name}</Text>
                    <Text style={styles.cardSub}>{i.visitor_type} • {i.visitor_phone || ''}</Text>
                  </View>
                  <Badge label={i.status} variant={i.status === 'active' ? 'green' : i.status === 'used' ? 'purple' : 'red'} />
                </View>
                {i.status === 'active' && (
                  <View style={styles.qrBox}>
                    <Text style={styles.qrText}>{i.qr_code}</Text>
                  </View>
                )}
              </Card>
            ))}
            {!invites.length && <Text style={styles.empty}>No invitations yet</Text>}
          </>
        )}

        {tab === 'moves' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setModal('move')}>
              <Text style={styles.addBtnText}>+ Request Move In/Out</Text>
            </TouchableOpacity>
            {moves.map(m => (
              <Card key={m.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{m.move_type === 'move_in' ? 'Move In' : 'Move Out'}</Text>
                    <Text style={styles.cardSub}>{m.tentative_start} to {m.tentative_end}</Text>
                  </View>
                  <Badge label={m.status} variant={m.status === 'approved' ? 'green' : m.status === 'pending' ? 'orange' : 'red'} />
                </View>
              </Card>
            ))}
            {!moves.length && <Text style={styles.empty}>No move requests</Text>}
          </>
        )}
      </ScrollView>

      <FormModal
        visible={modal === 'invite'}
        title="Create Invitation"
        initialData={invitePrefill}
        fields={[
          { key: 'visitorName', label: 'Visitor Name' },
          { key: 'visitorPhone', label: 'Phone' },
          { key: 'visitorType', label: 'Type', type: 'select', options: ['guest', 'cab', 'delivery', 'daily_help', 'other'] },
          { key: 'purpose', label: 'Purpose' },
          { key: 'validFrom', label: 'Valid From (YYYY-MM-DD HH:MM)' },
          { key: 'validTo', label: 'Valid To (YYYY-MM-DD HH:MM)' },
        ]}
        onClose={() => setModal(null)}
        onSubmit={createInvite}
      />

      <FormModal
        visible={modal === 'move'}
        title="Move Request"
        fields={[
          { key: 'moveType', label: 'Type', type: 'select', options: ['move_in', 'move_out'] },
          { key: 'tentativeStart', label: 'Start Date (YYYY-MM-DD)' },
          { key: 'tentativeEnd', label: 'End Date (YYYY-MM-DD)' },
          { key: 'notes', label: 'Notes' },
        ]}
        onClose={() => setModal(null)}
        onSubmit={createMove}
      />
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
  addBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: 'center', marginBottom: 16 },
  addBtnText: { color: colors.white, fontSize: 14, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center' },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 4 },
  cardSub: { fontSize: 12, color: colors.text2 },
  qrBox: { backgroundColor: colors.white, borderRadius: 8, padding: 12, marginTop: 10 },
  qrText: { color: '#000', fontFamily: 'monospace', fontSize: 12, fontWeight: '700', textAlign: 'center' },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
});
