"""Prototype configuration. A Gmail sender address is not an account credential."""

TRADING_SESSIONS_PER_YEAR = 252
MOCK_HISTORY_SESSIONS = 5 * TRADING_SESSIONS_PER_YEAR
TARGET_FREQUENCIES = (12, 6, 1)
# Set False to offer presets only. The calculation engine accepts any positive integer.
ALLOW_CUSTOM_TARGET = True
COUNTERS = ("DEMO-SGX", "DEMO-US")
SCENARIOS = ("Trending", "Oscillating", "Sideways")
DATA_VERSION = 1

# The sender must be a Google account on the test phone and authorize gmail.send.
# Change this before rebuilding when a dedicated Gmail account is ready.
GMAIL_SENDER_ADDRESS = "kelwong98@gmail.com"
