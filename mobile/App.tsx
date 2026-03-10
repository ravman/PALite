import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { NavigationContainer, useNavigation } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, getToken, clearToken } from './src/api';
import { colors } from './src/theme';

import LoginScreen    from './src/screens/LoginScreen';
import HomeScreen     from './src/screens/HomeScreen';
import BookingsScreen from './src/screens/BookingsScreen';
import VisitorsScreen from './src/screens/VisitorsScreen';
import MarketplaceScreen from './src/screens/MarketplaceScreen';
import ProfileScreen  from './src/screens/ProfileScreen';
import LocksScreen    from './src/screens/LocksScreen';
import NewsScreen     from './src/screens/NewsScreen';
import VoiceAssistant from './src/components/VoiceAssistant';

const Stack = createNativeStackNavigator();

// ─── Bottom nav ────────────────────────────────────────────────────────────────
function BottomNav({ currentRoute, onNavigate, voiceOpen, onVoiceOpen }: {
  currentRoute: string;
  onNavigate: (screen: string) => void;
  voiceOpen: boolean;
  onVoiceOpen: () => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.navContainer, { paddingBottom: insets.bottom + 8 }]}>
      <View style={styles.navPill}>
        <TouchableOpacity style={styles.navBtn} onPress={() => onNavigate('Locks')}>
          <Text style={[styles.navIcon, currentRoute === 'Locks' && styles.navIconActive]}>🔒</Text>
          <Text style={[styles.navLabel, currentRoute === 'Locks' && styles.navLabelActive]}>Lock</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.navCenter, voiceOpen && styles.navCenterActive]} onPress={onVoiceOpen}>
          <Text style={styles.navCenterIcon}>🎤</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navBtn} onPress={() => onNavigate('Bookings')}>
          <Text style={[styles.navIcon, currentRoute === 'Bookings' && styles.navIconActive]}>📅</Text>
          <Text style={[styles.navLabel, currentRoute === 'Bookings' && styles.navLabelActive]}>Book</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ─── Main navigator with voice ─────────────────────────────────────────────────
function AppNavigator({ ctx, onLogout, switchApt }: { ctx: any; onLogout: () => void; switchApt: (id: string) => void }) {
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceAction, setVoiceAction] = useState<{ screen: string; prefill: Record<string, string> } | null>(null);
  const navigation = useNavigation<any>();
  const [currentRoute, setCurrentRoute] = useState('Home');

  const handleVoiceNavigate = (screen: string, prefill: Record<string, string> = {}) => {
    setVoiceAction({ screen, prefill });
    navigation.navigate(screen, { prefill });
    setTimeout(() => setVoiceAction(null), 5000);
  };

  return (
    <>
      <Stack.Navigator
        screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}
        screenListeners={{ state: e => {
          const routes = e.data?.state?.routes;
          if (routes) setCurrentRoute(routes[routes.length - 1]?.name || 'Home');
        }}}
      >
        <Stack.Screen name="Home" children={() =>
          <HomeScreen ctx={ctx} navigate={screen => navigation.navigate(screen)} />} />
        <Stack.Screen name="Bookings" children={({ route }) =>
          <BookingsScreen navigation={navigation} prefill={(route.params as any)?.prefill} />} />
        <Stack.Screen name="Visitors" children={({ route }) =>
          <VisitorsScreen navigation={navigation} ctx={ctx} prefill={(route.params as any)?.prefill} />} />
        <Stack.Screen name="Marketplace" children={({ route }) =>
          <MarketplaceScreen navigation={navigation} prefill={(route.params as any)?.prefill} />} />
        <Stack.Screen name="Profile" children={() =>
          <ProfileScreen navigation={navigation} ctx={ctx} onLogout={onLogout} switchApt={switchApt} />} />
        <Stack.Screen name="Locks" children={() => <LocksScreen navigation={navigation} />} />
        <Stack.Screen name="News" children={() => <NewsScreen navigation={navigation} />} />
      </Stack.Navigator>

      <BottomNav
        currentRoute={currentRoute}
        onNavigate={screen => navigation.navigate(screen)}
        voiceOpen={voiceOpen}
        onVoiceOpen={() => setVoiceOpen(true)}
      />

      <VoiceAssistant
        visible={voiceOpen}
        onNavigate={handleVoiceNavigate}
        onClose={() => setVoiceOpen(false)}
      />
    </>
  );
}

// ─── Root ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [ctx, setCtx] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const t = await getToken();
    if (!t) { setLoading(false); return; }
    setTokenState(t);
    const d = await api('/api/auth/me');
    if (d.error) { await clearToken(); setTokenState(null); }
    else { setUser(d.user); setCtx(d); }
    setLoading(false);
  }, []);

  useEffect(() => { loadMe(); }, [loadMe]);

  const handleLogin = async (t: string, u: any) => {
    setTokenState(t); setUser(u); setLoading(true);
    setTimeout(loadMe, 100);
  };

  const handleLogout = async () => {
    await clearToken(); setTokenState(null); setUser(null); setCtx(null);
  };

  const switchApt = async (aptId: string) => {
    await api('/api/context/switch', { method: 'POST', body: JSON.stringify({ apartmentId: aptId }) });
    loadMe();
  };

  if (loading) return (
    <View style={styles.splash}>
      <Text style={styles.splashTitle}>PA Lite</Text>
      <Text style={styles.splashSub}>Loading...</Text>
    </View>
  );

  if (!token) return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg} />
      <LoginScreen onLogin={handleLogin} />
    </SafeAreaProvider>
  );

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg} />
      <NavigationContainer theme={{ dark: true, colors: { background: colors.bg, card: colors.card, text: colors.text, border: colors.border, primary: colors.accent, notification: colors.red } }}>
        <AppNavigator ctx={ctx} onLogout={handleLogout} switchApt={switchApt} />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  splash: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  splashTitle: { fontSize: 40, fontWeight: '700', color: colors.accent2 },
  splashSub: { fontSize: 14, color: colors.text2, marginTop: 8 },
  navContainer: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    alignItems: 'center', pointerEvents: 'box-none',
  },
  navPill: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(20,20,31,0.96)',
    borderRadius: 50, paddingHorizontal: 28, paddingVertical: 10,
    gap: 32, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
  },
  navBtn: { alignItems: 'center', gap: 3, paddingHorizontal: 8, paddingVertical: 4 },
  navIcon: { fontSize: 22, opacity: 0.5 },
  navIconActive: { opacity: 1 },
  navLabel: { fontSize: 9, fontWeight: '500', color: colors.text2 },
  navLabelActive: { color: colors.white },
  navCenter: {
    width: 52, height: 52, borderRadius: 26,
    backgroundColor: colors.white, alignItems: 'center', justifyContent: 'center',
    shadowColor: colors.white, shadowOpacity: 0.2, shadowRadius: 8, elevation: 8,
  },
  navCenterActive: { backgroundColor: colors.accent },
  navCenterIcon: { fontSize: 22 },
});
