# FreeSMS

<div align="center">
  <img src="src/gui/assets/sms_icon.png" alt="FreeSMS Logo" width="200"/>
  <p>A cross-platform Python application with Tkinter GUI that allows sending free SMS messages to mobile phones worldwide.</p>
  
  ![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
  ![License](https://img.shields.io/badge/license-MIT-green.svg)
  ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
</div>

## ✨ Features

- 📱 **Free SMS Messaging**: Send text messages to mobile phones around the world
- 🌐 **Multiple API Integrations**: Support for Twilio, TextBelt, and other SMS gateways
- 📋 **Contact Management**: Organize recipients with CSV import/export capability
- 🔄 **Message Scheduling**: Set up recurring messages with flexible scheduling options
- 📝 **Message Templates**: Save and reuse common message formats
- 📊 **Message History**: Track all sent messages with delivery status
- 🔐 **Secure Storage**: Encrypted storage of API keys and credentials
- 🖥️ **Modern UI**: Clean, intuitive Tkinter interface with customizable themes
- 🔔 **Notifications**: Desktop alerts for message delivery status
- 💻 **CLI Support**: Powerful command-line interface for scripting and automation
- 🔌 **System Tray Integration**: Run in the background with quick access
- 🌍 **Cross-Platform**: Works on Windows, macOS, and Linux

## 🚀 Setup Instructions

### Prerequisites

- Python 3.6 or higher
- Tkinter (usually included with Python)
- Git (for cloning the repository)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tboy1337/FreeSMS.git
   cd FreeSMS
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Register for SMS API services**
   - [Twilio](https://www.twilio.com/try-twilio) - Create a free account
   - [TextBelt](https://textbelt.com/) - Get a free API key

4. **Configure the application**
   
   You can configure the application in one of these ways:
   
   - **Through the UI**: Launch the app and enter your API keys in the Settings tab
   - **Using environment variables**: Set up the following environment variables:
     ```
     TWILIO_ACCOUNT_SID=your_account_sid
     TWILIO_AUTH_TOKEN=your_auth_token
     TWILIO_PHONE_NUMBER=your_twilio_phone_number
     TEXTBELT_API_KEY=your_textbelt_api_key
     ```
   - **Using a .env file**: Create a `.env` file in the project root with the above variables

5. **Run the application**
   ```bash
   python run.py
   ```

## 🖥️ Command Line Interface

FreeSMS provides a robust CLI for automation and integration with other tools:

### Basic Usage

Get help with available commands:
```bash
python run.py cli --help
```

Send a message directly from the command line:
```bash
python run.py cli send "+1234567890" "Hello from FreeSMS"
```

### CLI Commands

- **Send Messages**
  ```bash
  python run.py cli send RECIPIENT MESSAGE [--service SERVICE]
  ```

- **Manage Contacts**
  ```bash
  python run.py cli contacts list
  python run.py cli contacts add NAME PHONE [--country COUNTRY] [--notes NOTES]
  python run.py cli contacts delete ID
  ```

- **View Message History**
  ```bash
  python run.py cli history [--limit LIMIT] [--status STATUS]
  ```

- **Schedule Messages**
  ```bash
  python run.py cli schedule list [--all]
  python run.py cli schedule add RECIPIENT MESSAGE TIME [--service SERVICE] [--recurring {daily,weekly,monthly}] [--interval INTERVAL]
  python run.py cli schedule cancel ID
  ```

- **Manage Templates**
  ```bash
  python run.py cli templates list
  python run.py cli templates add NAME CONTENT
  python run.py cli templates delete ID
  python run.py cli templates use ID RECIPIENT
  ```

- **Configure SMS Services**
  ```bash
  python run.py cli services list
  python run.py cli services configure NAME CREDENTIALS
  python run.py cli services activate NAME
  ```

- **Export/Import Data**
  ```bash
  python run.py cli export contacts FILENAME
  python run.py cli import contacts FILENAME
  python run.py cli export history FILENAME [--format {csv,json}]
  ```

## ⚙️ Command Line Options

The application supports various command line options:

```
python run.py --help
usage: main.py [-h] [--minimized] [--debug] [--config CONFIG] [--cli]

FreeSMS - Free SMS Messaging Application

optional arguments:
  -h, --help       Show this help message and exit
  --minimized      Start application minimized to system tray
  --debug          Enable debug logging
  --config CONFIG  Path to custom config file
  --cli            Run in command line mode
```

## 📋 System Requirements

- **Python**: 3.6 or higher
- **Tkinter**: Usually included with Python installation
- **Disk Space**: ~50MB for installation and databases
- **Memory**: 100MB+ recommended

### System Tray Support
- **Windows**: No additional requirements
- **macOS**: `rumps` package (installed automatically)
- **Linux**: `PyGObject` and `AppIndicator3` libraries
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-gi gir1.2-appindicator3-0.1
  ```

## ⚠️ Usage Limitations

- **Twilio Free Trial**:
  - Limited credits ($15-$20) for testing
  - Recipient phone numbers must be verified before messaging
  - Twilio branding on messages

- **TextBelt**:
  - Free tier: 1 free SMS per day with API key
  - $0.05 per message after free quota

- **Rate Limiting**:
  - Built-in rate limiting to comply with API restrictions
  - Configurable through settings

## 📁 Project Structure

```
FreeSMS/
├── src/
│   ├── api/          # SMS service interfaces and implementations
│   ├── automation/   # Message scheduling and automation
│   ├── cli/          # Command line interface
│   ├── gui/          # User interface components
│   │   └── assets/   # Images and UI resources
│   ├── models/       # Data models and database interaction
│   ├── security/     # Security and credentials management
│   ├── services/     # Application services
│   └── utils/        # Utility functions and helpers
├── tests/            # Unit and integration tests
├── .github/          # GitHub workflows and templates
├── .gitignore        # Git ignore file
├── LICENSE.txt       # MIT license
├── README.md         # This file
├── requirements.txt  # Python dependencies
└── run.py            # Application entry point
```

## 🧪 Testing

Run the complete test suite:
```bash
python -m unittest discover tests
```

Run tests with coverage report:
```bash
pytest --cov=src tests/
```

## 🔧 Customization

- **Application Settings**: Stored in `~/.message_master/config.json`
- **Logs**: Stored in `~/.message_master/logs/`
- **Database**: SQLite database at `~/.message_master/message_master.db`
- **Themes**: Customizable through the Settings menu

## 🔒 Security

- API keys and credentials are stored securely using environment-specific encryption
- No message content is sent to our servers; all communication is direct to SMS providers
- Optional password protection for application access
- Automatic session timeout for security

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgements

- [Twilio](https://www.twilio.com/) - SMS API provider
- [TextBelt](https://textbelt.com/) - SMS API provider
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - GUI toolkit
- All open-source packages listed in requirements.txt

## 📄 License

This project is licensed under the CRL License - see the [LICENSE.md](LICENSE.md) file for details.

## 📬 Contact

Project maintained by [tboy1337](https://github.com/tboy1337)

GitHub: [https://github.com/tboy1337/FreeSMS](https://github.com/tboy1337/FreeSMS)