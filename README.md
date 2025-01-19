# 🏦 Monzo Bridge

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A secure bridge that syncs your Monzo transactions with Monetr, featuring real-time monitoring and secure credential storage.

[Features](#✨-features) • [Installation](#💻-installation) • [Setup](#🚀-setup) • [Security](#🔒-security) • [Troubleshooting](#🔧-troubleshooting)

</div>

## ✨ Features

- **Real-time Transaction Sync** 
  - Instant monitoring of new Monzo transactions
  - Automatic syncing to your Monetr instance
  - Smart transaction categorization

- **Secure Credential Management**
  - System keyring integration for secure storage
  - No plaintext credentials or config files
  - Platform-specific secure storage:
    - Windows: Windows Credential Manager
    - macOS: Keychain
    - Linux: Secret Service API (GNOME Keyring/KDE Wallet)

- **Smart Configuration**
  - Interactive setup wizard
  - Automatic Monzo OAuth flow
  - Guided Monetr configuration

## 💻 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Nerdykidtech/Monetr_Monzo_Bridge.git
   cd Monetr_Monzo_Bridge
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Linux Dependencies

If you're on Linux, you'll need these additional packages:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-dbus python3-secretstorage libsecret-1-0
```

**Fedora:**
```bash
sudo dnf install python3-dbus python3-secretstorage libsecret
```

**Arch Linux:**
```bash
sudo pacman -S python-secretstorage
```

## 🚀 Setup

### Setting up Monzo Client App

1. **Create a Monzo Client**
   - Go to [Monzo Developer Portal](https://developers.monzo.com/)
   - Sign in with your Monzo account
   - Click "New OAuth Client"
   - Fill in the following details:
     ```
     Name: Monetr Bridge (or any name you prefer)
     Logo URL: (optional)
     Redirect URLs: http://localhost:8080/callback
     Confidentiality: Confidential
     Description: Bridge to sync Monzo transactions with Monetr
     ```
   - After creating, you'll receive:
     - Client ID (looks like: oauth2client_...)
     - Client Secret
   - ⚠️ Save these credentials securely - you'll need them later!

2. **Start the Application**
   ```bash
   python Monzo_Bridge
   ```

3. **Configure Monetr**
   - Enter your Monetr instance URL
   - Provide your login credentials
   - Copy your Bank Account ID from the Monetr transactions URL
     ```
     http://localhost:4000/bank/bac_XXXXXXXXXXXXXXXXXX/transactions
     ```

4. **Configure Monzo**
   - Enter the Client ID and Secret from step 1
   - A browser window will open for Monzo authorization
   - Log in to your Monzo account if needed
   - Approve the connection
   - Check your Monzo app for the authorization request
   - After approving, you'll be redirected back to the application

5. **Start Monitoring**
   - The bridge will automatically start monitoring for new transactions
   - New transactions will be instantly synced to Monetr
   - View the status in real-time in your terminal

## 🔒 Security

- **Secure Storage**: All sensitive information is stored in your system's secure credential manager
- **No Plain Text**: No credentials are ever stored in plain text files
- **OAuth Security**: Full OAuth 2.0 flow for Monzo API access
- **Automatic Token Management**: Tokens are securely stored and automatically refreshed

## 🔧 Troubleshooting

### Common Issues

1. **Keyring Access on Linux**
   - Ensure you have the required dependencies installed
   - Make sure your D-Bus session is running
   - Check if GNOME Keyring or KDE Wallet is properly configured

2. **Monzo Authorization**
   - Verify your Client ID and Secret
   - Ensure you've approved the app in your Monzo mobile app
   - Check your callback URL configuration

3. **Monetr Connection**
   - Verify your Monetr instance is running
   - Check your Bank Account ID format (should start with 'bac_')
   - Ensure your Monetr credentials are correct

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
