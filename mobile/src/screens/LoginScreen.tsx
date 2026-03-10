import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { api, setToken } from '../api';
import { colors, spacing, radius } from '../theme';

export default function LoginScreen({ onLogin }: { onLogin: (token: string, user: any) => void }) {
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const sendOtp = async () => {
    setLoading(true); setError('');
    const d = await api('/api/auth/request-otp', { method: 'POST', body: JSON.stringify({ phone }) });
    setLoading(false);
    if (d.success) { setSessionId(d.sessionId); setStep('otp'); }
    else setError(d.error || 'Failed to send OTP');
  };

  const verify = async () => {
    setLoading(true); setError('');
    const d = await api('/api/auth/verify-otp', { method: 'POST', body: JSON.stringify({ sessionId, otp }) });
    setLoading(false);
    if (d.token) { await setToken(d.token); onLogin(d.token, d.user); }
    else setError(d.error || 'Invalid OTP');
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.appName}>PA Lite</Text>
        <Text style={styles.tagline}>Smart Community Living</Text>

        <View style={styles.form}>
          {step === 'phone' ? (
            <>
              <Text style={styles.label}>Phone Number</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter phone number"
                placeholderTextColor={colors.text2}
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
                autoFocus
              />
              <TouchableOpacity
                style={[styles.btn, loading && styles.btnDisabled]}
                onPress={sendOtp}
                disabled={loading}
              >
                <Text style={styles.btnText}>{loading ? 'Sending...' : 'Send OTP'}</Text>
              </TouchableOpacity>
              <Text style={styles.demo}>Demo: 9876543210 (Resident) • 9999900002 (Guard)</Text>
            </>
          ) : (
            <>
              <Text style={styles.label}>Enter OTP</Text>
              <TextInput
                style={[styles.input, styles.otpInput]}
                placeholder="6-digit OTP"
                placeholderTextColor={colors.text2}
                value={otp}
                onChangeText={setOtp}
                keyboardType="numeric"
                maxLength={6}
                autoFocus
              />
              <TouchableOpacity
                style={[styles.btn, loading && styles.btnDisabled]}
                onPress={verify}
                disabled={loading}
              >
                <Text style={styles.btnText}>{loading ? 'Verifying...' : 'Verify'}</Text>
              </TouchableOpacity>
              <Text style={styles.demo}>Demo OTP: 123456</Text>
              <TouchableOpacity onPress={() => setStep('phone')}>
                <Text style={[styles.demo, { color: colors.accent2, marginTop: 8 }]}>← Change number</Text>
              </TouchableOpacity>
            </>
          )}
          {!!error && <Text style={styles.error}>{error}</Text>}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  appName: { fontSize: 40, fontWeight: '700', color: colors.accent2, marginBottom: 8 },
  tagline: { fontSize: 15, color: colors.text2, marginBottom: 48 },
  form: { width: '100%', maxWidth: 360 },
  label: { fontSize: 12, color: colors.text2, marginBottom: 6 },
  input: {
    backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border,
    borderRadius: radius.sm, padding: spacing.md, color: colors.text,
    fontSize: 16, marginBottom: 14,
  },
  otpInput: { fontSize: 24, textAlign: 'center', letterSpacing: 8 },
  btn: {
    backgroundColor: colors.accent, borderRadius: 10,
    padding: 14, alignItems: 'center', marginBottom: 12,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  demo: { fontSize: 12, color: colors.text2, textAlign: 'center' },
  error: { color: colors.red, fontSize: 13, marginTop: 8, textAlign: 'center' },
});
