import discord
from discord.ext import commands
import requests
import asyncio
from datetime import datetime

# I changed the token when I uploaded it so no one else can use it 
TOKEN = "OTMyNzI3Mjg3MzcwMEzMDM2.ZJb7j.rCk8rHWj34ajHysYAGgZEAfWxVXpOl1mMJeM"

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to fetch the Coinbase order book
def get_coinbase_order_book(product_id="DOGE-USD", level=2):
    """
    Fetch the order book for a given product from Coinbase Exchange's public API.
    """
    url = f'https://api.exchange.coinbase.com/products/{product_id}/book'
    params = {'level': level}  # Level 2 returns aggregated book
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

# Function to analyze the order book
async def analyze_order_book():
    """
    Analyze the order book to calculate average asks and bids and determine percentages.
    """
    order_book = get_coinbase_order_book("DOGE-USD")
    if isinstance(order_book, str):  # Handle errors
        return order_book

    asks = order_book.get('asks', [])
    bids = order_book.get('bids', [])

    if not asks or not bids:
        return "No ask or bid data available."

    # Calculate total volumes
    total_ask_volume = sum(float(ask[1]) for ask in asks[:10])  # Top 10 asks
    total_bid_volume = sum(float(bid[1]) for bid in bids[:10])  # Top 10 bids
    total_volume = total_ask_volume + total_bid_volume

    # Calculate percentages
    ask_percentage = round((total_ask_volume / total_volume) * 100, 2)
    bid_percentage = round((total_bid_volume / total_volume) * 100, 2)

    return (
        f"Order Book for DOGE-USD:\n"
        f"Total Ask Volume: {total_ask_volume:.2f}\n"
        f"Total Bid Volume: {total_bid_volume:.2f}\n"
        f"Ask Percentage: {ask_percentage}%\n"
        f"Bid Percentage: {bid_percentage}%"
    )

# Bot command to fetch and analyze the order book
@bot.command(name="orderbook")
async def orderbook(ctx):
    """
    Respond to the !orderbook command with the analyzed Coinbase order book data.
    """
    await ctx.send("Fetching order book for DOGE-USD. Please wait...")
    result = await analyze_order_book()
    await ctx.send(result)

# Start the bot
bot.run(TOKEN)
