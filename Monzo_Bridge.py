import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
from getpass import getpass
import keyring
import base64
import platform

load_dotenv()

def check_keyring_requirements():
    """Check if keyring requirements are met and provide instructions if not"""
    system = platform.system().lower()
    
    if system == 'linux':
        try:
            import secretstorage
            # Test if we can actually connect to the Secret Service
            secretstorage.dbus_init()
        except Exception as e:
            print("\n⚠️  Linux Keyring Setup Required")
            print("To use secure credential storage, you need to install these packages:")
            print("\nFor Ubuntu/Debian:")
            print("  sudo apt-get install python3-dbus python3-secretstorage libsecret-1-0")
            print("\nFor Fedora:")
            print("  sudo dnf install python3-dbus python3-secretstorage libsecret")
            print("\nFor Arch Linux:")
            print("  sudo pacman -S python-secretstorage")
            print("\nAfter installing, please run this program again.")
            return False
    
    return True

# Check keyring requirements before proceeding
if not check_keyring_requirements():
    exit(1)

# Monzo API Configuration
AUTH_URL = "https://auth.monzo.com"
API_URL = "https://api.monzo.com"
REDIRECT_URI = "http://localhost:8080/callback"

# Local API Configuration
LOCAL_BANK_ACCOUNT_ID = None  # Will be set during setup

# Keyring service names
MONETR_SERVICE = "monzo_bridge_monetr"
MONZO_SERVICE = "monzo_bridge_monzo"

def encrypt_config(data):
    """Encrypt configuration data"""
    return base64.b64encode(json.dumps(data).encode()).decode()

def decrypt_config(encrypted_data):
    """Decrypt configuration data"""
    try:
        return json.loads(base64.b64decode(encrypted_data).decode())
    except:
        return None

def load_monetr_config():
    """Load Monetr configuration from secure storage"""
    try:
        encrypted_data = keyring.get_password(MONETR_SERVICE, "config")
        if encrypted_data:
            return decrypt_config(encrypted_data)
        return None
    except:
        return None

def load_monzo_config():
    """Load Monzo configuration from secure storage"""
    try:
        encrypted_data = keyring.get_password(MONZO_SERVICE, "config")
        if encrypted_data:
            return decrypt_config(encrypted_data)
        return None
    except:
        return None

def save_monetr_config(config):
    """Save Monetr configuration to secure storage"""
    encrypted_data = encrypt_config(config)
    keyring.set_password(MONETR_SERVICE, "config", encrypted_data)

def save_monzo_config(config):
    """Save Monzo configuration to secure storage"""
    encrypted_data = encrypt_config(config)
    keyring.set_password(MONZO_SERVICE, "config", encrypted_data)

def setup_monetr_config():
    """Interactive setup for Monetr configuration"""
    print("\n=== Monetr Configuration Setup ===")
    print("Please provide your Monetr details:")
    
    # Get existing config if available
    existing_config = load_monetr_config()
    
    # Get Monetr URL
    default_url = existing_config.get('monetr_url', 'http://localhost:4000') if existing_config else 'http://localhost:4000'
    url = input(f"\nMonetr URL [{default_url}]: ").strip()
    url = url if url else default_url
    
    # Remove trailing slash if present
    url = url.rstrip('/')
    
    # Get email
    default_email = existing_config.get('monetr_email', '') if existing_config else ''
    email = input(f"Monetr Email [{default_email}]: ").strip()
    email = email if email else default_email
    
    # Get password (without showing input)
    password = getpass("Monetr Password: ").strip()

    # Get Bank Account ID with instructions
    print("\nBank Account ID Instructions:")
    print("1. Login to your Monetr instance")
    print("2. Go to the Transactions page")
    print("3. Look at the URL, it will be in this format:")
    print("   http://localhost:4000/bank/bac_XXXXXXXXXXXXXXXXXX/transactions")
    print("4. Copy the 'bac_XXXXXXXXXXXXXXXXXX' part")
    
    default_bank_id = existing_config.get('bank_account_id', '') if existing_config else ''
    bank_id = input(f"\nBank Account ID [{default_bank_id}]: ").strip()
    bank_id = bank_id if bank_id else default_bank_id
    
    if not bank_id.startswith('bac_'):
        print("\n⚠️  Warning: Bank Account ID should start with 'bac_'")
        print("    Please verify this is correct")
        if input("Continue anyway? (yes/no): ").lower().strip() != 'yes':
            return setup_monetr_config()
    
    # Verify the credentials
    print("\nVerifying Monetr credentials...")
    config = {
        'monetr_url': url,
        'monetr_email': email,
        'monetr_password': password,
        'bank_account_id': bank_id
    }
    
    # Test the connection
    try:
        global LOCAL_BANK_ACCOUNT_ID
        LOCAL_BANK_ACCOUNT_ID = bank_id
        test_client = LocalAPIClient(config)
        test_client.login()
        print("✓ Monetr credentials verified successfully!")
        
        # Save the configuration securely
        save_monetr_config(config)
        print("✓ Configuration saved securely")
        return config
        
    except Exception as e:
        print(f"✗ Failed to verify Monetr credentials: {str(e)}")
        retry = input("\nWould you like to try again? (yes/no): ").lower().strip()
        if retry == 'yes':
            return setup_monetr_config()
        return None

def setup_monzo_config():
    """Interactive setup for Monzo configuration"""
    print("\n=== Monzo Configuration Setup ===")
    print("Please provide your Monzo API credentials:")
    
    # Get existing config if available
    existing_config = load_monzo_config()
    
    # Get Client ID
    default_client_id = existing_config.get('client_id', '') if existing_config else ''
    client_id = input(f"\nMonzo Client ID [{default_client_id}]: ").strip()
    client_id = client_id if client_id else default_client_id
    
    # Get Client Secret
    client_secret = getpass("Monzo Client Secret: ").strip()
    
    config = {
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': None,
        'refresh_token': None
    }
    
    # Save the configuration securely
    save_monzo_config(config)
    print("✓ Monzo configuration saved securely")
    return config

def save_tokens(access_token, refresh_token):
    """Save tokens to secure storage"""
    config = load_monzo_config()
    if config:
        config['access_token'] = access_token
        config['refresh_token'] = refresh_token
        save_monzo_config(config)

def load_saved_tokens():
    """Load tokens from secure storage"""
    config = load_monzo_config()
    if config:
        return config.get('access_token')
    return None

class LocalAPIClient:
    def __init__(self, config=None):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        self.auth_cookie = None
        self.config = config or load_monetr_config()
        if not self.config:
            self.config = setup_monetr_config()
            if not self.config:
                raise Exception("Monetr configuration is required")
            
            # Set the global bank account ID
            global LOCAL_BANK_ACCOUNT_ID
            LOCAL_BANK_ACCOUNT_ID = self.config['bank_account_id']
    
    def login(self):
        """Login to Monetr API"""
        try:
            login_url = f"{self.config['monetr_url']}/api/authentication/login"
            print(f"\nAttempting login to Monetr...")
            
            response = self.session.post(
                login_url,
                json={
                    'email': self.config['monetr_email'],
                    'password': self.config['monetr_password']
                }
            )
            
            if response.status_code != 200:
                print(f"Login failed with status {response.status_code}")
                print(f"Response: {response.text}")
                response.raise_for_status()
            
            self.auth_cookie = response.cookies
            print("✓ Successfully logged in to Monetr")
            
        except requests.exceptions.RequestException as e:
            print(f"\nFailed to login to Monetr:")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                print(f"Error: {e.response.text}")
            raise Exception(f"Monetr login failed: {str(e)}")

    def post_transaction(self, amount, name, date, is_pending=False):
        if not self.auth_cookie:
            self.login()

        # Convert amount to positive if it's negative
        if amount < 0:
            amount = -amount
        # convert amount to negative if it's positive
        elif amount > 0:
            amount = -amount

        transaction_data = {
            "bankAccountId": LOCAL_BANK_ACCOUNT_ID,
            "amount": int(amount * 100),  # Convert to cents
            "name": name,
            "merchantName": name,
            "date": date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "isPending": is_pending,
            "spendingId": None,
            "adjustsBalance": True
        }
        
        try:
            response = self.session.post(
                f"{self.config['monetr_url']}/api/bank_accounts/{LOCAL_BANK_ACCOUNT_ID}/transactions",
                json=transaction_data,
                cookies=self.auth_cookie
            )
            
            if response.status_code != 200:
                print(f"Failed to post transaction with status {response.status_code}")
                print(f"Response: {response.text}")
                response.raise_for_status()
                
            print(f"✓ Successfully posted transaction: {name} for ${abs(amount):.2f}")
            
        except requests.exceptions.RequestException as e:
            print(f"\nFailed to post transaction:")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                print(f"Error: {e.response.text}")
            raise Exception(f"Failed to post transaction: {str(e)}")

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth callback"""
        try:
            # Extract the authorization code from the URL
            query_components = dict(qc.split('=') for qc in self.path.split('?')[1].split('&'))
            auth_code = query_components['code']
            
            # Store the auth code securely
            keyring.set_password(MONZO_SERVICE, "auth_code", auth_code)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_message = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; text-align: center;">
                <h2 style="color: #2ecc71;">✓ Authorization Successful!</h2>
                <p>You can now close this window and return to the application.</p>
            </body>
            </html>
            """
            self.wfile.write(success_message.encode())
            
        except Exception as e:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; text-align: center;">
                <h2 style="color: #e74c3c;">✗ Authorization Failed</h2>
                <p>Error: {str(e)}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            self.wfile.write(error_message.encode())

def get_auth_code():
    """Get the stored auth code"""
    return keyring.get_password(MONZO_SERVICE, "auth_code")

def clear_auth_code():
    """Clear the stored auth code"""
    try:
        keyring.delete_password(MONZO_SERVICE, "auth_code")
    except keyring.errors.PasswordDeleteError:
        pass  # Code was already cleared

def exchange_auth_code(auth_code, client_id, client_secret):
    """Exchange authorization code for access token"""
    config = load_monzo_config()
    if not config:
        raise Exception("Monzo configuration not found")
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': REDIRECT_URI,
        'code': auth_code
    }
    
    response = requests.post(f"{API_URL}/oauth2/token", data=data)
    response.raise_for_status()
    
    tokens = response.json()
    expiry = (datetime.now() + timedelta(seconds=tokens['expires_in'])).isoformat()
    
    # Save tokens securely
    save_tokens(tokens['access_token'], tokens['refresh_token'])
    
    # Clear the used auth code
    clear_auth_code()
    
    return tokens['access_token']

def get_access_token(auth_code):
    global CLIENT_ID, CLIENT_SECRET
    return exchange_auth_code(auth_code, CLIENT_ID, CLIENT_SECRET)

def refresh_access_token(refresh_token):
    global CLIENT_ID, CLIENT_SECRET
    token_url = f"{API_URL}/oauth2/token"
    data = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token
    }
    
    response = requests.post(token_url, data=data)
    tokens = response.json()
    
    # Calculate expiry time
    expiry = (datetime.now() + timedelta(seconds=tokens['expires_in'])).isoformat()
    
    token_data = {
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token'],
        'expiry': expiry
    }
    
    save_tokens(tokens['access_token'], tokens['refresh_token'])
    return tokens['access_token']

def load_saved_tokens():
    """Load tokens from secure storage"""
    config = load_monzo_config()
    if config:
        return config.get('access_token')
    return None

def get_accounts(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"{API_URL}/accounts", headers=headers)
    return response.json().get('accounts', [])

def get_transactions(account_id, access_token, quiet=False):
    """Get transactions for an account"""
    # Calculate timestamp for last hour
    since = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    url = f"{API_URL}/transactions"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        'account_id': account_id,
        'since': since,
        'expand[]': 'merchant',
        'limit': 50  # Get enough transactions to ensure we don't miss any
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        transactions = data.get('transactions', [])
        
        # Sort transactions by created date in descending order (newest first)
        sorted_transactions = sorted(transactions, key=lambda x: x['created'], reverse=True)
        
        return sorted_transactions
    except Exception as e:
        if not quiet:
            print(f"Error getting transactions: {str(e)}")
        return []

def wait_for_app_approval(access_token):
    """Wait for user to manually confirm they've approved the app in Monzo"""
    print("\n=== Monzo App Approval Required ===")
    print("1. Open your Monzo app")
    print("2. Look for the approval notification")
    print("3. Review and accept the permissions")
    print("4. Type 'yes' here once you've approved")
    print("Type 'exit' to quit at any time")
    print("===================================")
    
    while True:
        response = input("\nHave you approved the app in Monzo? (yes/no/exit): ").lower().strip()
        if response == 'yes':
            try:
                # Verify the approval by attempting to list accounts
                accounts = get_accounts(access_token)
                print("\n App approval confirmed!")
                return True
            except Exception as e:
                print("\n Couldn't verify app approval. Please make sure you've approved in the Monzo app.")
                print(f"Error: {str(e)}")
                continue
        elif response == 'no':
            print("\nPlease approve the app in Monzo first.")
            continue
        elif response == 'exit':
            print("\nExiting...")
            return False
        else:
            print("\nPlease enter 'yes', 'no', or 'exit'")

def main():
    print("\n=== Monzo Bridge Setup ===")
    print("This setup will configure both Monetr and Monzo connections.")
    
    # Step 1: Setup Monetr
    print("\nStep 1: Monetr Setup")
    try:
        local_api = LocalAPIClient()
        print("✓ Monetr configuration complete")
    except Exception as e:
        print(f"✗ Failed to setup Monetr: {str(e)}")
        return
    
    # Step 2: Setup Monzo API credentials
    print("\nStep 2: Monzo API Setup")
    monzo_config = load_monzo_config()
    if not monzo_config:
        monzo_config = setup_monzo_config()
        if not monzo_config:
            print("✗ Failed to setup Monzo configuration")
            return
    
    # Set global variables from config
    global CLIENT_ID, CLIENT_SECRET
    CLIENT_ID = monzo_config['client_id']
    CLIENT_SECRET = monzo_config['client_secret']
    
    # Step 3: Start Monzo Authorization
    access_token = load_saved_tokens()
    if not access_token:
        print("\nStep 3: Starting Monzo Authorization")
        print("This process has two parts:")
        print("1. Browser authorization")
        print("2. Mobile app approval")
        input("\nPress Enter to start the authorization process...")
        
        # Start the server first so we don't miss the callback
        print("\nStarting callback server...")
        server = HTTPServer(('localhost', 8080), AuthHandler)
        
        # Generate and open authorization URL
        state = "monzo_auth_state"
        auth_url = f"{AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&state={state}"
        print("\nOpening browser for authorization...")
        webbrowser.open(auth_url)
        
        print("\nWaiting for authorization callback...")
        print("Please complete the authorization in your browser.")
        server.handle_request()
        
        # Get the authorization code
        try:
            auth_code = get_auth_code()
            print("✓ Authorization code received!")
            
            print("\nExchanging authorization code for access token...")
            access_token = get_access_token(auth_code)
            print("✓ Access token obtained!")
            
            print("\nNow you need to approve the connection in your Monzo app.")
            if not wait_for_app_approval(access_token):
                return
                
        except Exception as e:
            print(f"✗ Failed to complete authorization: {str(e)}")
            return
    
    # Step 4: Start Transaction Monitor
    print("\nStep 4: Starting Transaction Monitor")
    try:
        print("\nFetching your accounts...")
        accounts = get_accounts(access_token)
        if not accounts:
            print("No accounts found")
            return
            
        print("\nAccounts found:")
        for account in accounts:
            print(f"✓ {account['description']} ({account['type']})")
        
        # Get initial state of transactions quietly
        print("\nInitializing transaction monitor...")
        initial_transaction_ids = set()
        for account in accounts:
            if account['type'] == 'us_partner':
                transactions = get_transactions(account['id'], access_token, quiet=True)
                initial_transaction_ids.update(t['id'] for t in transactions)
        
        print("\nMonitoring for new transactions...")
        print("Press Ctrl+C to stop")
        
        while True:
            try:
                for account in accounts:
                    if account['type'] == 'us_partner':
                        print(".", end="", flush=True)  # Show activity
                        transactions = get_transactions(account['id'], access_token, quiet=True)
                        
                        if transactions:
                            for transaction in transactions:
                                # Only process transactions we haven't seen before
                                if transaction['id'] not in initial_transaction_ids:
                                    # Get the amount (convert from pennies to dollars)
                                    # Grab the amount, if it's postive, make it negative and if it's negative, make it positive
                                    if transaction['amount'] < 0:
                                        amount = abs(transaction['amount']) / 100.0 * -1
                                    else:
                                        amount = abs(transaction['amount']) / 100.0
                                    

                                    # Get the merchant name or description
                                    merchant = transaction.get('merchant', {})
                                    if merchant and merchant.get('name'):
                                        merchant_name = merchant['name']
                                    else:
                                        merchant_name = transaction.get('description', 'Unknown')
                                    
                                    # Parse the transaction time
                                    transaction_time = datetime.strptime(
                                        transaction['created'], 
                                        '%Y-%m-%dT%H:%M:%S.%fZ'
                                    )
                                    
                                    print(f"\n💰 New transaction: ${amount:.2f} at {merchant_name}")
                                    print(f"   Time: {transaction_time.strftime('%I:%M:%S %p')}")
                                    
                                    # Add emoji if available
                                    if merchant and merchant.get('emoji'):
                                        print(f"   Category: {merchant.get('emoji', '')} {merchant.get('category', 'uncategorized')}")
                                    
                                    try:
                                        local_api.post_transaction(
                                            amount=amount,
                                            name=merchant_name,
                                            date=transaction_time,
                                            is_pending=not transaction.get('settled', False)
                                        )
                                        initial_transaction_ids.add(transaction['id'])  # Add to seen transactions
                                        print("   ✓ Posted to Monetr")
                                    except Exception as e:
                                        print(f"   ✗ Failed to post to Monetr: {str(e)}")
                
                time.sleep(10)
                
            except Exception as e:
                print(f"\nError: {str(e)}")
                time.sleep(10)
                
    except Exception as e:
        print(f"✗ Error in transaction monitor: {str(e)}")
        return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping transaction monitoring...")
