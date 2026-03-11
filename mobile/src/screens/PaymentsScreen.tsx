import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Modal, Alert,
} from 'react-native';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { api } from '../api';
import { colors, spacing, radius } from '../theme';

interface Props { navigation: any; }

export default function PaymentsScreen({ navigation }: Props) {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [tab, setTab] = useState<'outstanding' | 'history'>('outstanding');
  const [receipt, setReceipt] = useState<any>(null);
  const [paying, setPaying] = useState<string | null>(null);

  const load = () => api('/api/payments/invoices').then(d => setInvoices(Array.isArray(d) ? d : []));
  useEffect(() => { load(); }, []);

  const pay = async (invId: string) => {
    setPaying(invId);
    const d = await api(`/api/payments/pay/${invId}`, { method: 'POST' });
    setPaying(null);
    if (d.error) { Alert.alert('Error', d.error); return; }
    const r = await api(`/api/payments/receipt/${d.paymentId}`);
    setReceipt(r);
    load();
  };

  const outstanding = invoices.filter(i => i.my_status === 'unpaid' && i.status !== 'cancelled');
  const history = invoices.filter(i => i.my_status === 'paid' || i.status === 'cancelled');

  const isOverdue = (inv: any) => inv.due_date && new Date(inv.due_date) < new Date() && inv.my_status === 'unpaid';

  const typeIcon: Record<string, string> = {
    maintenance: '🏠', utility: '💡', booking: '📅', parking: '🚗',
    amenity: '🏊', fine: '⚠️', other: '📋',
  };

  return (
    <View style={styles.container}>
      <PageHeader title="Payments" onBack={() => navigation.goBack()} />

      <View style={styles.tabBar}>
        {(['outstanding', 'history'] as const).map(t => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && styles.tabActive]} onPress={() => setTab(t)}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t === 'outstanding' ? `Outstanding${outstanding.length ? ` (${outstanding.length})` : ''}` : 'History'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
        {tab === 'outstanding' && (
          <>
            {outstanding.length === 0 && <Text style={styles.empty}>All clear! No pending payments.</Text>}
            {outstanding.map(inv => (
              <Card key={inv.id}>
                <View style={styles.row}>
                  <Text style={styles.typeIcon}>{typeIcon[inv.invoice_type] || '📋'}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{inv.title || inv.description}</Text>
                    {inv.invoice_type && <Text style={styles.cardSub}>{inv.invoice_type}</Text>}
                    {inv.due_date && (
                      <Text style={[styles.cardSub, isOverdue(inv) && { color: colors.red }]}>
                        Due: {inv.due_date}{isOverdue(inv) ? ' ⚠️ Overdue' : ''}
                      </Text>
                    )}
                  </View>
                  <Text style={[styles.amount, isOverdue(inv) && { color: colors.red }]}>
                    ₹{inv.amount}
                  </Text>
                </View>
                <TouchableOpacity
                  style={[styles.payBtn, paying === inv.id && { opacity: 0.6 }]}
                  onPress={() => pay(inv.id)}
                  disabled={paying === inv.id}
                >
                  <Text style={styles.payBtnText}>{paying === inv.id ? 'Processing...' : 'Pay Now'}</Text>
                </TouchableOpacity>
              </Card>
            ))}
          </>
        )}

        {tab === 'history' && (
          <>
            {history.length === 0 && <Text style={styles.empty}>No payment history yet.</Text>}
            {history.map(inv => (
              <Card key={inv.id}>
                <View style={styles.row}>
                  <Text style={styles.typeIcon}>{typeIcon[inv.invoice_type] || '📋'}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{inv.title || inv.description}</Text>
                    {inv.paid_at && <Text style={styles.cardSub}>Paid {inv.paid_at.split('T')[0]}</Text>}
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 6 }}>
                    <Text style={styles.amount}>₹{inv.amount}</Text>
                    <Badge label={inv.status === 'cancelled' ? 'cancelled' : 'paid'} variant={inv.status === 'cancelled' ? 'red' : 'green'} />
                  </View>
                </View>
                {inv.my_status === 'paid' && inv.payment_id && (
                  <TouchableOpacity onPress={async () => {
                    const r = await api(`/api/payments/receipt/${inv.payment_id}`);
                    setReceipt(r);
                  }}>
                    <Text style={styles.receiptLink}>View Receipt →</Text>
                  </TouchableOpacity>
                )}
              </Card>
            ))}
          </>
        )}
      </ScrollView>

      {/* Receipt Modal */}
      <Modal visible={!!receipt} transparent animationType="slide" onRequestClose={() => setReceipt(null)}>
        <TouchableOpacity style={styles.overlay} activeOpacity={1} onPress={() => setReceipt(null)}>
          <TouchableOpacity activeOpacity={1} style={styles.sheet}>
            <View style={styles.handle} />
            <View style={styles.receiptStamp}>
              <Text style={styles.receiptStampText}>✓ PAID</Text>
            </View>
            <Text style={styles.receiptTitle}>{receipt?.title || receipt?.description}</Text>
            <View style={styles.receiptDivider} />
            <View style={styles.receiptRow}><Text style={styles.receiptLabel}>Amount</Text><Text style={styles.receiptValue}>₹{receipt?.amount}</Text></View>
            <View style={styles.receiptRow}><Text style={styles.receiptLabel}>Society</Text><Text style={styles.receiptValue}>{receipt?.society_name}</Text></View>
            {receipt?.apartment && <View style={styles.receiptRow}><Text style={styles.receiptLabel}>Unit</Text><Text style={styles.receiptValue}>{receipt?.apartment}</Text></View>}
            <View style={styles.receiptRow}><Text style={styles.receiptLabel}>Transaction</Text><Text style={[styles.receiptValue, { fontFamily: 'monospace', fontSize: 11 }]}>{receipt?.transaction_id}</Text></View>
            <View style={styles.receiptRow}><Text style={styles.receiptLabel}>Date</Text><Text style={styles.receiptValue}>{receipt?.paid_at?.split('T')[0]}</Text></View>
            <TouchableOpacity style={styles.closeBtn} onPress={() => setReceipt(null)}>
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
  tabBar: { flexDirection: 'row', gap: 6, paddingHorizontal: spacing.xl, marginBottom: 4 },
  tab: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: colors.border },
  tabActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  tabText: { fontSize: 12, fontWeight: '600', color: colors.text2 },
  tabTextActive: { color: colors.white },
  scroll: { flex: 1 },
  content: { padding: spacing.xl, paddingBottom: 40 },
  empty: { textAlign: 'center', color: colors.text2, padding: 40 },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  typeIcon: { fontSize: 24, marginTop: 2 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 2 },
  cardSub: { fontSize: 12, color: colors.text2, marginTop: 1 },
  amount: { fontSize: 18, fontWeight: '700', color: colors.accent2, fontFamily: 'monospace' },
  payBtn: { backgroundColor: colors.accent, borderRadius: 8, padding: 10, alignItems: 'center', marginTop: 10 },
  payBtnText: { color: colors.white, fontSize: 13, fontWeight: '600' },
  receiptLink: { color: colors.accent2, fontSize: 12, marginTop: 8 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: spacing.xl, paddingBottom: 36 },
  handle: { width: 40, height: 4, backgroundColor: colors.border, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  receiptStamp: { alignSelf: 'center', backgroundColor: 'rgba(0,184,148,0.15)', borderRadius: 50, paddingHorizontal: 20, paddingVertical: 6, borderWidth: 2, borderColor: colors.green, marginBottom: 12 },
  receiptStampText: { color: colors.green, fontWeight: '700', fontSize: 16 },
  receiptTitle: { fontSize: 16, fontWeight: '600', color: colors.text, textAlign: 'center', marginBottom: 12 },
  receiptDivider: { borderTopWidth: 1, borderStyle: 'dashed', borderColor: colors.border, marginVertical: 12 },
  receiptRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  receiptLabel: { fontSize: 12, color: colors.text2 },
  receiptValue: { fontSize: 13, color: colors.text, fontWeight: '500' },
  closeBtn: { backgroundColor: colors.card2, borderRadius: 10, padding: 12, alignItems: 'center', marginTop: 16, borderWidth: 1, borderColor: colors.border },
  closeBtnText: { color: colors.text, fontSize: 14, fontWeight: '600' },
});
