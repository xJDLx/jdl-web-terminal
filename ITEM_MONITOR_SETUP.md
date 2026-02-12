# Steamdt Item Monitor Setup Guide

## Overview
The Item Monitor is a CS2 (Counter-Strike 2) item tracking system that integrates with the Steamdt.com API to monitor prices, availability, and market trends of steam items.

## Features
✅ Real-time price tracking for CS2 items
✅ Batch price updates
✅ 7-day average price tracking
✅ Google Sheets database integration
✅ Price change monitoring
✅ Multi-item inventory management
✅ Export/Import capabilities

## Prerequisites
1. **Steamdt.com Account** - Free account at https://steamdt.com
2. **Steamdt API Key** - Obtain from your account dashboard (Personal Center → API Management)
3. **Installed Dependencies** - Run: `pip install -r requirements.txt`

## Setup Instructions

### Step 1: Get Your Steamdt API Key
1. Go to https://steamdt.com and create a free account
2. Log in to your account
3. Navigate to **Personal Center** → **API Management**
4. Click **Apply** or **Enable** to get your API Key
5. Copy the API Key (it looks like a long string of characters)

### Step 2: Add API Key in the App
1. Open the app and go to the **📊 Item Monitor** tab
2. You'll see a prompt to enter your API Key
3. Paste your Steamdt API Key in the input field
4. Click **Save API Key**
5. The app will save it securely to `steamdt_config.json`

### Step 3: Add Items to Monitor
1. Go to the **➕ Add Items** tab
2. Enter the item name (e.g., "AK-47 | Phantom Disruptor")
3. Enter the **exact Market Hash Name** from Steam Community Market
   - You can find this by viewing the item on Steam Market
   - It should include the condition (Factory New, Minimal Wear, Field-Tested, etc.)
4. Select which notifications you want (price drops, rises, stock changes)
5. Click **Add Item to Monitor**

### Step 4: Monitor Your Items
1. Go to **📈 Monitor** tab to see all tracked items
2. View current prices, 7-day averages, and price changes
3. Click **🔄 Refresh Prices** to update all items immediately
4. Use **Details** to see more information about an item
5. Use **Remove** to stop monitoring an item

## Understanding Market Hash Names

The **Market Hash Name** is the exact item name from the Steam Community Market. Examples:

| Item | Market Hash Name |
|------|------------------|
| AK-47 Dragon Lore (Factory New) | "AK-47 \| Dragon Lore (Factory New)" |
| M4A4 Howl (Minimal Wear) | "M4A4 \| Howl (Minimal Wear)" |
| AWP Dragon Lore (Field-Tested) | "AWP Dragon Lore (Field-Tested)" |

**To find the exact name:**
1. Go to Steam Community Market
2. Search for the item you want
3. Click on it
4. The name displayed at the top is your Market Hash Name

## API Features

### Available Data
- **Current Price**: Real-time market price
- **7-Day Average**: Mean price over last 7 days
- **Price Trends**: Price change percentage
- **Item Stats**: Rarity, condition, wear level
- **Market Data**: Supply availability

### Rate Limits
- Steamdt API is currently **free and unlimited** during beta
- Recommended: Refresh every 5-30 minutes to avoid excessive requests

## Google Sheets Integration

The app automatically creates an **Items** worksheet in your connected Google Sheet with the following columns:

| Column | Description |
|--------|-------------|
| Item Name | Display name of the item |
| Market Hash Name | Exact market identifier |
| Added Date | When you started monitoring |
| Current Price | Latest price from API |
| Avg Price (7d) | 7-day average price |
| Price Change | Percentage change |
| Status | Active/Inactive |
| Last Updated | Most recent update timestamp |

## Troubleshooting

### "Item not found" Error
- Check the Market Hash Name spelling and capitalization
- Make sure the condition (Factory New, Minimal Wear, etc.) is included
- Verify the item exists on Steam Community Market

### "API Error" Messages
- Verify your API Key is correct
- Check your Steamdt account hasn't reached any limits
- Ensure your internet connection is stable
- Try refreshing the page

### Prices Not Updating
- Click **🔄 Refresh Prices** manually
- Check that items have valid Market Hash Names
- Verify API Key is still active in Steamdt dashboard

### "Sheet not found" Error
- The app will auto-create the **Items** worksheet on first use
- Make sure you have write access to the Google Sheet
- Check that the sheet isn't protected/locked

## Advanced Usage

### Batch Operations
- Use **Export Items** to download your monitoring list as CSV
- Share the CSV with team members or backup elsewhere

### Alert Settings
Under **⚙️ Settings**, you can configure:
- Auto-refresh interval (5-120 minutes)
- Alert thresholds for price changes
- Notification preferences

### Performance Tips
- Monitor no more than 50-100 items for best performance
- Refresh every 15-30 minutes instead of continuously
- Use CSV export to archive historical data

## API Documentation

For more details on Steamdt API:
📖 [Steamdt API Docs](https://doc.steamdt.com/)

Available Endpoints:
- `GET /open/cs2/v1/price` - Get single item price
- `POST /open/cs2/v1/batch/price` - Get multiple prices
- `GET /open/cs2/v1/avgPrice` - Get 7-day average
- `GET /open/cs2/v1/items` - Get item information

## Security Notes

🔒 **API Key Safety:**
- Your API Key is stored locally in `steamdt_config.json`
- Never share your API Key with anyone
- Regenerate your key if you suspect it's compromised
- The app only sends requests to official Steamdt API

## Support

For issues or feature requests:
- Check Steamdt API status at https://status.steamdt.com/
- Review API documentation for endpoint details
- Ensure your API key is still active in your Steamdt account

---

**Last Updated:** February 2026
**Version:** 1.0.0
