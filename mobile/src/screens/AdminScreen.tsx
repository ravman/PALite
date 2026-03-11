import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Modal, TextInput, Alert,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props { navigation: any; ctx: any; }

export default function AdminScreen({ navigation, ctx }: Props) {
  const [tab, setTab] = useState<'overview' | 'residents' | 'moves' | 'invoices' | 'docs'>('overview');
  const [stats, setStats] = useState<any>(null);
  const [residents, setResidents] = useState<any[]>([]);
  const [moves, setMoves] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [rejectModal, setRejectModal] = useState<{ type: string; id: string; name: string } | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [raiseModal, setRaiseModal] = useState(false);
  const [raiseForm, setRaiseForm] = useState({ title: '', amount: '', invoiceType: 'maintenance', dueDate: '', sendTo: 'all' });
  const [submitting, setSubmitting] = useState(false);

  const loadAll = () => {
    api('/api/admin/dashboard').then(setStats);
    api('/api/admin/residents/pending').then(d => setResidents(Array.isArray(d) ? d : []));
    api('/api/admin/move-requests/pending').then(d => setMoves(Array.isArray(d) ? d : []));
    api('/api/admin/invoices').then(d => setInvoices(Array.isArray(d) ? d : []));
    api('/api/admin/documents/pending').then(d => setDocs(Array.isArray(d) ? d : []));
  };
  useEffect(() => { loadAll(); }, []);

  const approve = async (type: string, id: string) => {
    setSubmitting(true);
    if (type === 'resident') await api(`/api/admin/residents/${id}/approve`, { method: 'POST' });
    else if (type === 'move') await api(`/api/admin/move-requests/${id}/approve`, { method: 'POST' });
    else if (type === 'doc') await api(`/api/admin/documents/${id}/verify`, { method: 'POST' });
    setSubmitting(false);
    loadAll();
  };

  const reject = async () => {
    if (!rejectModal) return;
    setSubmitting(true);
    const body = JSON.stringify({ reason: rejectReason });
    if (rejectModal.type === 'resident') await api(`/api/admin/residents/${rejectModal.id}/reject`, { method: 'POST', body });
    else if (rejectModal.type === 'move') await api(`/api/admin/move-requests/${rejectModal.id}/reject`, { method: 'POST', body });
    setSubmitting(false);
    setRejectModal(null);
    setRejectReason('');
    loadAll();
  };

  const raiseInvoice = async () => {
    if (!raiseForm.title || !raiseForm.amount) { Alert.alert('Error', 'Title and amount required'); return; }
    setSubmitting(true);
    await api('/api/admin/invoices', {
      method: 'POST',
      body: JSON.stringify({ ...raiseForm, amount: parseFloat(raiseForm.amount) }),
    });
    setSubmitting(false);
    setRaiseModal(false);
    setRaiseForm({ title: '', amount: '', invoiceType: 'maintenance', dueDate: '', sendTo: 'all' });
    loadAll();
  };

  const pendingTotal = (stats?.pendingApprovals || 0) + (stats?.pendingMoves || 0) + (stats?.pendingDocuments || 0);

  const ApproveRow = ({ label, sub, type, id, name }: any) => (
    <View style={styles.approveRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.cardTitle}>{label}</Text>
        {sub && <Text style={styles.cardSub}>{sub}</Text>}
      </View>
      <View style={styles.approveActions}>
        <TouchableOpacity style={styles.approveBtn} onPress={() => approve(type, id)} disabled={submitting}>
          <Text style={styles.approveBtnText}>✓</Text>
        </TouchableOpacity>
        {type !== 'doc' && (
          <TouchableOpacity style={styles.rejectBtn} onPress={() => setRejectModal({ type, id, name })} disabled={submitting}>
            <Text style={styles.rejectBtnText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <PageHeader title="Admin Panel" onBack={() => navigation.goBack()} />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabScroll} contentContainerStyle={styles.tabBar}>
        {(['overview', 'residents', 'moves', 'invoices', 'docs'] as const).map(t => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
              {t === 'overview' && pendingTotal > 0 ? ` (${pendingTotal})` : ''}
              {t === 'residents' && residents.length > 0 ? ` (${residents.length})` : ''}
              {t === 'moves' && moves.length > 0 ? ` (${moves.length})` : ''}
              {t === 'docs' && docs.length > 0 ? ` (${docs.length})` : ''}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>

        {tab === 'overview' && stats && (
          <>
            <View style={styles.statsGrid}>
              {[
                { label: 'Residents', value: stats.totalResidents, icon: '👥' },
                { label: 'Pending', value: pendingTotal, icon: '⏳', alert: pendingTotal > 0 },
                { label: 'Bookings', value: stats.activeBookings, icon: '📅' },
                { label: 'Invoices', value: stats.unpaidInvoices, icon: '💳', alert: stats.unpaidInvoices > 0 },
              ].map(s => (
                <View key={s.label} style={[styles.statCard, s.alert && { borderColor: colors.orange }]}>
                  <Text style={styles.statIcon}>{s.icon}</Text>
                  <Text style={[styles.statValue, s.alert && { color: colors.orange }]}>{s.value ?? '—'}</Text>
                  <Text style={styles.statLabel}>{s.label}</Text>
                </View>
              ))}
            </View>
            {residents.slice(0, 2).map(r => <ApproveRow key={r.id} type="resident" id={r.id} name={r.name} label={r.name} sub={`${r.unit_number} · ${r.resident_type}`} />)}
            {moves.slice(0, 2).map(m => <ApproveRow key={m.id} type="move" id={m.id} name={m.name} label={m.name} sub={m.move_type} />)}
            {docs.slice(0, 2).map(d => <ApproveRow key={d.id} type="doc" id={d.id} name={d.resident_name} label={d.resident_name} sub={d.doc_type} />)}
          </>
        )}

        {tab === 'residents' && (
          <>
            {residents.length === 0 && <Text style={styles.empty}>No pending approvals</Text>}
            {residents.map(r => <ApproveRow key={r.id} type="resident" id={r.id} name={r.name} label={r.name} sub={`${r.unit_number} · ${r.resident_type} · ${r.society_name}`} />)}
          </>
        )}

        {tab === 'moves' && (
          <>
            {moves.length === 0 && <Text style={styles.empty}>No pending move requests</Text>}
            {moves.map(m => <ApproveRow key={m.id} type="move" id={m.id} name={m.name} label={m.name} sub={`${m.move_type} · ${m.tentative_start}`} />)}
          </>
        )}

        {tab === 'invoices' && (
          <>
            <TouchableOpacity style={styles.addBtn} onPress={() => setRaiseModal(true)}>
              <Text style={styles.addBtnText}>+ Raise Invoice</Text>
            </TouchableOpacity>
            {invoices.length === 0 && <Text style={styles.empty}>No invoices yet</Text>}
            {invoices.map(inv => (
              <Card key={inv.id}>
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{inv.title}</Text>
                    <Text style={styles.cardSub}>₹{inv.amount} · {inv.invoice_type}</Text>
                    {inv.recipient_count > 1 && <Text style={styles.cardSub}>{inv.paid_count}/{inv.recipient_count} paid</Text>}
                  </View>
                  <Badge label={inv.status} variant={inv.status === 'paid' ? 'green' : inv.status === 'cancelled' ? 'red' : 'orange'} />
                </View>
              </Card>
            ))}
          </>
        )}

        {tab === 'docs' && (
          <>
            {docs.length === 0 && <Text style={styles.empty}>No documents pending</Text>}
            {docs.map(d => <ApproveRow key={d.id} type="doc" id={d.id} name={d.resident_name} label={d.resident_name} sub={d.doc_type} />)}
          </>
        )}
      </ScrollView>

      {/* Reject Modal */}
      <Modal visible={!!rejectModal} transparent animationType="slide" onRequestClose={() => setRejectModal(null)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setRejectModal(null)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Reject {rejectModal?.name}</Text>
            <Text style={styles.label}>Reason (optional)</Text>
            <TextInput
              style={styles.input}
              value={rejectReason}
              onChangeText={setRejectReason}
              placeholder="Enter reason..."
              placeholderTextColor={colors.text2}
              multiline
            />
            <View style={styles.row}>
              <TouchableOpacity style={[styles.btn, styles.rejectBtnFull]} onPress={reject} disabled={submitting}>
                <Text style={styles.btnText}>{submitting ? 'Rejecting...' : 'Confirm Reject'}</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.cancelBtnFull]} onPress={() => setRejectModal(null)}>
                <Text style={[styles.btnText, { color: colors.text }]}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>

      {/* Raise Invoice Modal */}
      <Modal visible={raiseModal} transparent animationType="slide" onRequestClose={() => setRaiseModal(false)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setRaiseModal(false)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            <Text style={styles.sheetTitle}>Raise Invoice</Text>
            <ScrollView showsVerticalScrollIndicator={false}>
              {[
                { key: 'title', label: 'Title *' },
                { key: 'amount', label: 'Amount (₹) *', numeric: true },
                { key: 'dueDate', label: 'Due Date (YYYY-MM-DD)' },
              ].map(f => (
                <View key={f.key}>
                  <Text style={styles.label}>{f.label}</Text>
                  <TextInput
                    style={styles.input}
                    value={(raiseForm as any)[f.key]}
                    onChangeText={v => setRaiseForm(r => ({ ...r, [f.key]: v }))}
                    placeholderTextColor={colors.text2}
                    placeholder={f.label.replace(' *', '')}
                    keyboardType={f.numeric ? 'numeric' : 'default'}
                  />
                </View>
              ))}
              <Text style={styles.label}>Category</Text>
              {['maintenance', 'utility', 'parking', 'amenity', 'fine', 'other'].map(t => (
                <TouchableOpacity key={t} style={[styles.typeChip, raiseForm.invoiceType === t && styles.typeChipActive]}
                  onPress={() => setRaiseForm(r => ({ ...r, invoiceType: t }))}>
                  <Text style={[styles.typeChipText, raiseForm.invoiceType === t && { color: colors.white }]}>{t}</Text>
                </TouchableOpacity>
              ))}
              <Text style={[styles.label, { marginTop: 12 }]}>Send To</Text>
              {[['all', 'All residents'], ['owner', 'Owners only'], ['tenant', 'Tenants only']].map(([v, l]) => (
                <TouchableOpacity key={v} style={[styles.typeChip, raiseForm.sendTo === v && styles.typeChipActive]}
                  onPress={() => setRaiseForm(r => ({ ...r, sendTo: v }))}>
                  <Text style={[styles.typeChipText, raiseForm.sendTo === v && { color: colors.white }]}>{l}</Text>
                </TouchableOpacity>
              ))}
              <View style={[styles.row, { marginTop: 16 }]}>
                <TouchableOpacity style={[styles.btn, styles.rejectBtnFull]} onPress={raiseInvoice} disabled={submitting}>
                  <Text style={styles.btnText}>{submitting ? 'Sending...' : 'Send Invoice'}</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.btn, styles.cancelBtnFull]} onPress={() => setRaiseModal(false)}>
                  <Text style={[styles.btnText, { color: colors.text }]}>Cancel</Text>
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
  tabScroll: { flexGrow: 0 },
  tabBar: { flexDirection: 'row', gap: 6, paddingHorizontal: spacing.xl, paddingVertical: 4 },
  tab: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { fontSize: 12, fontWeight: '600', color: colors.text2 },
  tabTextActive: { color: colors.white },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 40 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  statCard: {
    flex: 1, minWidth: '45%', backgroundColor: colors.card,
    borderRadius: radius.lg, padding: 14, borderWidth: 1, borderColor: colors.border,
    alignItems: 'center', gap: 4,
  },
  statIcon: { fontSize: 22 },
  statValue: { fontSize: 22, fontWeight: '700', color: colors.text },
  statLabel: { fontSize: 11, color: colors.text2 },
  approveRow: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: colors.card, borderRadius: radius.lg, padding: spacing.md,
    borderWidth: 1, borderColor: colors.border, marginBottom: 10,
  },
  approveActions: { flexDirection: 'row', gap: 6 },
  approveBtn: { backgroundColor: 'rgba(0,184,148,0.15)', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: 'rgba(0,184,148,0.3)' },
  approveBtnText: { color: colors.green, fontWeight: '700' },
  rejectBtn: { backgroundColor: 'rgba(225,112,85,0.12)', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: 'rgba(225,112,85,0.25)' },
  rejectBtnText: { color: colors.red, fontWeight: '700' },
  row: { flexDirection: 'row', gap: 10 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 2 },
  cardSub: { fontSize: 12, color: colors.text2 },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  addBtn: { backgroundColor: colors.accent, borderRadius: 10, padding: 12, alignItems: 'center', marginBottom: 12 },
  addBtnText: { color: colors.white, fontSize: 13, fontWeight: '600' },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: spacing.xl, paddingBottom: 36, maxHeight: '85%' },
  handle: { width: 40, height: 4, backgroundColor: colors.border, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  sheetTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 16 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6 },
  input: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, padding: spacing.md, color: colors.text, fontSize: 14, marginBottom: 12 },
  typeChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: colors.border, marginBottom: 6, alignSelf: 'flex-start' },
  typeChipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  typeChipText: { fontSize: 12, fontWeight: '600', color: colors.text2 },
  btn: { flex: 1, padding: 12, borderRadius: 10, alignItems: 'center' },
  rejectBtnFull: { backgroundColor: colors.red },
  cancelBtnFull: { backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border },
  btnText: { fontSize: 14, fontWeight: '600', color: colors.white },
});
