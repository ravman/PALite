import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import FormModal from '../components/FormModal';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props {
  navigation: any;
  prefill?: Record<string, string>;
  ctx?: any;
}

type TabType = 'expected' | 'inside' | 'history';

const TYPE_COLORS: Record<string, string> = {
  guest: '#8B9FD4', cab: '#5BA3C9', delivery: '#E8A87C', daily_help: '#7EC8A4', other: '#9B8EC4',
};

function avatarColor(name: string) {
  const palette = ['#5BA3C9', '#8B9FD4', '#7EC8A4', '#E8A87C', '#C9A0DC'];
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return palette[h % palette.length];
}

function fmtTime(ts: string | null) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function typeLabel(t: string) {
  return t.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function statusColors(s: string) {
  if (s === 'Approved' || s === 'Inside' || s === 'Active')
    return { color: '#3CB371', borderColor: '#3CB371', bg: 'rgba(60,179,113,.12)' };
  if (s === 'Waiting')
    return { color: '#E8A020', borderColor: '#E8A020', bg: 'rgba(232,160,32,.12)' };
  if (s === 'Denied' || s === 'Expired')
    return { color: '#E05555', borderColor: '#E05555', bg: 'rgba(224,85,85,.12)' };
  return { color: colors.text2, borderColor: colors.border, bg: colors.card2 };
}

function buildDateStrip() {
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(); d.setDate(d.getDate() + i);
    days.push({ label: i === 0 ? 'Today' : String(d.getDate()), value: d.toISOString().split('T')[0] });
  }
  return days;
}

export default function VisitorsScreen({ navigation, prefill, ctx }: Props) {
  const [tab, setTab] = useState<TabType>('expected');
  const [entries, setEntries] = useState<any[]>([]);
  const [invites, setInvites] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [modal, setModal] = useState<'invite' | null>(null);
  const [invitePrefill, setInvitePrefill] = useState<Record<string, string>>({});
  const dateStrip = buildDateStrip();

  useEffect(() => {
    if (!prefill) return;
    const fields: Record<string, string> = {};
    if (prefill.visitorName) fields.visitorName = prefill.visitorName;
    if (prefill.visitorPhone) fields.visitorPhone = prefill.visitorPhone;
    if (prefill.visitorType) fields.visitorType = prefill.visitorType;
    if (prefill.purpose) fields.purpose = prefill.purpose;
    if (Object.keys(fields).length > 0) { setInvitePrefill(fields); setModal('invite'); }
  }, [prefill]);

  const loadData = useCallback(() => {
    if (tab === 'expected') {
      api('/api/visitors/my-invitations').then(d => setInvites(Array.isArray(d) ? d : []));
      api(`/api/visitors/my-entries?tab=expected&date=${selectedDate}`).then(d => setEntries(Array.isArray(d) ? d : []));
    } else {
      api(`/api/visitors/my-entries?tab=${tab}`).then(d => setEntries(Array.isArray(d) ? d : []));
    }
  }, [tab, selectedDate]);

  useEffect(() => { loadData(); }, [loadData]);

  const createInvite = async (d: Record<string, string>) => {
    const r = await api('/api/visitors/create-invite', { method: 'POST', body: JSON.stringify(d) });
    if (r.error) { Alert.alert('Error', r.error); return; }
    loadData();
    setModal(null);
  };

  const actOn = async (id: string, action: 'approve' | 'reject') => {
    setSubmitting(id);
    await api(`/api/visitors/${id}/${action}`, { method: 'POST' });
    setSubmitting(null); setExpanded(null); loadData();
  };

  // Build unified card list
  const cards = tab === 'expected' ? [
    ...invites
      .filter(inv => {
        const d = selectedDate;
        const from = inv.valid_from ? inv.valid_from.split('T')[0] : null;
        const to   = inv.valid_to   ? inv.valid_to.split('T')[0]   : null;
        if (from && to) return d >= from && d <= to;
        if (from) return d >= from;
        return inv.created_at?.split('T')[0] === d || !from;
      })
      .map((inv: any) => ({
        _type: 'invite', id: inv.id, name: inv.visitor_name, visitorType: inv.visitor_type,
        status: inv.status === 'active' ? 'Active' : inv.status === 'used' ? 'Inside' : 'Expired',
        statusKey: inv.status, time: inv.valid_from,
        unit: ctx?.apartment?.unit_number, residentName: ctx?.user?.name,
      })),
    ...entries.map((e: any) => ({
      _type: 'entry', id: e.id, name: e.visitor_name, visitorType: e.visitor_type,
      status: e.approval_status === 'approved' ? 'Approved' : e.approval_status === 'pending' ? 'Waiting' : e.approval_status === 'rejected' ? 'Denied' : e.approval_status,
      statusKey: e.approval_status, time: e.entry_time || e.created_at,
      unit: ctx?.apartment?.unit_number, residentName: ctx?.user?.name,
    })),
  ] : entries.map((e: any) => ({
    _type: 'entry', id: e.id, name: e.visitor_name, visitorType: e.visitor_type,
    status: e.exit_time ? 'Exited' : e.approval_status === 'approved' ? 'Inside' : e.approval_status === 'rejected' ? 'Denied' : e.approval_status,
    statusKey: e.approval_status, time: e.entry_time || e.created_at,
    unit: ctx?.apartment?.unit_number, residentName: ctx?.user?.name,
  }));

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Visitors</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModal('invite')}>
          <Text style={styles.addBtnText}>+</Text>
        </TouchableOpacity>
      </View>

      {/* Tab switcher */}
      <View style={styles.tabBar}>
        {(['expected', 'inside', 'history'] as TabType[]).map(t => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Date strip — Expected only */}
      {tab === 'expected' && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.dateStrip} contentContainerStyle={styles.dateStripContent}>
          <Text style={styles.dateStripIcon}>↺</Text>
          {dateStrip.map(d => (
            <TouchableOpacity key={d.value} style={[styles.datePill, selectedDate === d.value && styles.datePillActive]} onPress={() => setSelectedDate(d.value)}>
              <Text style={[styles.datePillText, selectedDate === d.value && styles.datePillTextActive]}>{d.label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* Cards */}
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {cards.length === 0 && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>👥</Text>
            <Text style={styles.emptyText}>{tab === 'expected' ? 'No visitors expected' : 'No entries found'}</Text>
          </View>
        )}
        {cards.map((card, i) => {
          const initials = (card.name || '?').split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase();
          const isWaiting = card.statusKey === 'pending';
          const isExpanded = expanded === card.id;
          const sc = statusColors(card.status);
          return (
            <TouchableOpacity
              key={card.id || i}
              style={styles.card}
              activeOpacity={isWaiting ? 0.7 : 1}
              onPress={() => { if (isWaiting) setExpanded(isExpanded ? null : card.id); }}
            >
              <View style={styles.cardRow}>
                {/* Avatar */}
                <View style={[styles.avatar, { backgroundColor: avatarColor(card.name || '') }]}>
                  <Text style={styles.avatarText}>{initials}</Text>
                </View>
                {/* Info */}
                <View style={styles.cardInfo}>
                  <Text style={styles.cardName}>{card.name}</Text>
                  <Text style={styles.cardSub}>For {card.unit || '—'} · {card.residentName || ''}</Text>
                  <View style={styles.chips}>
                    {(card.visitorType || 'guest').split(',').map((t: string) => (
                      <View key={t} style={[styles.chip, { borderColor: TYPE_COLORS[t.trim()] || '#8B9FD4' }]}>
                        <Text style={[styles.chipText, { color: TYPE_COLORS[t.trim()] || '#8B9FD4' }]}>{typeLabel(t.trim())}</Text>
                      </View>
                    ))}
                  </View>
                </View>
                {/* Status + time */}
                <View style={styles.cardRight}>
                  <View style={[styles.statusBadge, { backgroundColor: sc.bg, borderColor: sc.borderColor }]}>
                    <Text style={[styles.statusText, { color: sc.color }]}>{card.status}</Text>
                  </View>
                  {card.time ? <Text style={styles.timeText}>⏱ {fmtTime(card.time)}</Text> : null}
                </View>
              </View>

              {/* Approve / Deny */}
              {isWaiting && isExpanded && (
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.denyBtn} onPress={() => actOn(card.id, 'reject')} disabled={submitting === card.id}>
                    <Text style={styles.denyBtnText}>Deny</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.approveBtn} onPress={() => actOn(card.id, 'approve')} disabled={submitting === card.id}>
                    <Text style={styles.approveBtnText}>{submitting === card.id ? '…' : 'Approve'}</Text>
                  </TouchableOpacity>
                </View>
              )}
            </TouchableOpacity>
          );
        })}
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
  datePill: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.full, backgroundColor: colors.card2 },
  datePillActive: { backgroundColor: colors.accent },
  datePillText: { fontSize: 13, fontWeight: '600', color: colors.text },
  datePillTextActive: { color: colors.white },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 60 },
  emptyState: { alignItems: 'center', paddingTop: 60 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyText: { fontSize: 14, color: colors.text2 },
  card: { backgroundColor: colors.card2, borderRadius: radius.lg, marginBottom: 10, overflow: 'hidden', borderWidth: 1, borderColor: colors.border },
  cardRow: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: spacing.md },
  avatar: { width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: colors.white, fontSize: 15, fontWeight: '700' },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 15, fontWeight: '700', color: colors.text, marginBottom: 2 },
  cardSub: { fontSize: 12, color: colors.text2, marginBottom: 5 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 5 },
  chip: { paddingHorizontal: 9, paddingVertical: 2, borderRadius: radius.full, borderWidth: 1, backgroundColor: 'rgba(255,255,255,0.04)' },
  chipText: { fontSize: 11, fontWeight: '700' },
  cardRight: { alignItems: 'flex-end', gap: 5 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: radius.full, borderWidth: 1 },
  statusText: { fontSize: 11, fontWeight: '700' },
  timeText: { fontSize: 11, color: colors.text2 },
  actionRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, paddingHorizontal: spacing.md, paddingBottom: spacing.md },
  denyBtn: { paddingHorizontal: 20, paddingVertical: 8, borderRadius: radius.full, borderWidth: 1, borderColor: 'rgba(255,255,255,.2)', backgroundColor: 'rgba(255,255,255,.06)' },
  denyBtnText: { color: colors.text, fontSize: 13, fontWeight: '600' },
  approveBtn: { paddingHorizontal: 24, paddingVertical: 8, borderRadius: radius.full, backgroundColor: colors.accent },
  approveBtnText: { color: colors.white, fontSize: 13, fontWeight: '700' },
});
