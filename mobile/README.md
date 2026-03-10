# PA Lite — React Native App

Full React Native port of the PA Lite resident web app.

## Prerequisites

- Node.js 18+
- [Expo CLI](https://docs.expo.dev/get-started/installation/): `npm install -g expo-cli`
- For iOS: Mac with Xcode 15+
- For Android: Android Studio with SDK 34+
- Expo Go app on your phone for quick testing

## Setup

### 1. Set your server IP

Edit `src/api.ts` and update `API_BASE` to your GateKeeper server address:

```ts
// For local dev with Expo Go on same WiFi network:
export const API_BASE = 'http://192.168.1.XXX:3001';

// For production:
export const API_BASE = 'https://your-domain.com';
```

Find your local IP with: `ipconfig` (Windows) or `ifconfig | grep inet` (Mac/Linux)

### 2. Install dependencies

```bash
npm install
```

### 3. Run in Expo Go (fastest — no build needed)

```bash
npx expo start
```

Scan the QR code with:
- **iOS**: Camera app
- **Android**: Expo Go app

### 4. Build for iOS (requires Mac + Apple Developer account)

```bash
# Install EAS CLI
npm install -g eas-cli
eas login

# Configure build
eas build:configure

# Build for simulator (free, no developer account needed)
npx expo run:ios

# Build for device / App Store
eas build --platform ios
```

### 5. Build for Android

```bash
# Run on connected device or emulator
npx expo run:android

# Build APK for sideloading
eas build --platform android --profile preview

# Build AAB for Play Store
eas build --platform android
```

## Screens

| Screen | Route | Description |
|--------|-------|-------------|
| Login | — | Phone + OTP auth |
| Home | `Home` | Tile grid dashboard |
| Bookings | `Bookings` | Space listing + booking form |
| Visitors | `Visitors` | Gate invites + move requests |
| Marketplace | `Marketplace` | Buy/sell with photos |
| Profile | `Profile` | Vehicles, pets, family, invoices |
| Locks | `Locks` | Placeholder (coming soon) |
| News | `News` | Placeholder (coming soon) |

## Voice Assistant

Tap the **🎤 mic button** in the bottom nav. Say things like:

- *"Book the gym tomorrow at 6pm"* → opens Bookings, pre-fills date/time/space
- *"Invite Rahul for delivery"* → opens Visitors, pre-fills name + type
- *"Post a sell listing for my sofa, 3000 rupees"* → opens Marketplace with form filled
- *"Show my profile"* → navigates to Profile

Voice uses `@react-native-voice/voice` on device. Requires microphone permission.

## Project Structure

```
PALite-RN/
├── App.tsx                    # Root app, auth state, navigation shell
├── app.json                   # Expo config, permissions
├── package.json
└── src/
    ├── api.ts                 # fetch wrapper + SecureStore token
    ├── theme.ts               # colors, spacing, typography
    ├── components/
    │   ├── Badge.tsx          # Status badge
    │   ├── Card.tsx           # Card wrapper
    │   ├── FormModal.tsx      # Bottom-sheet form modal
    │   ├── PageHeader.tsx     # Back arrow + title
    │   └── VoiceAssistant.tsx # Voice overlay + Claude API
    └── screens/
        ├── LoginScreen.tsx
        ├── HomeScreen.tsx
        ├── BookingsScreen.tsx
        ├── VisitorsScreen.tsx
        ├── MarketplaceScreen.tsx
        ├── ProfileScreen.tsx
        ├── LocksScreen.tsx
        └── NewsScreen.tsx
```

## Demo Credentials

| Phone | Role |
|-------|------|
| 9876543210 | Resident (Rahul) |
| 9999900001 | Admin + Super Admin |
| 9999900002 | Guard |

OTP: **123456**
