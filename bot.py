import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import random

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

user_balances = {}
user_last_daily = {}

SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🍉", "🔔", "⭐", "7️⃣"]
CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
    '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}
STARTING_BALANCE = 100
DAILY_COOLDOWN = timedelta(hours=24)

def get_user_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = STARTING_BALANCE
    return user_balances[user_id]

def format_currency(amount):
    return f"💵 {amount:,}"

@bot.event
async def on_ready():
    print(f'✅ Bot ready as {bot.user}')

@bot.command(name='daily')
async def daily(ctx):
    user_id = ctx.author.id
    now = datetime.utcnow()

    last_claim = user_last_daily.get(user_id)
    if last_claim and now - last_claim < DAILY_COOLDOWN:
        next_claim = last_claim + DAILY_COOLDOWN
        remaining = next_claim - now
        hours, remainder = divmod(remaining.total_seconds(), 3600)
        minutes = remainder // 60
        await ctx.send(
            f"⏳ {ctx.author.mention}, you've already claimed your daily reward!\n"
            f"Try again in **{int(hours)}h {int(minutes)}m**."
        )
        return

    reward = random.randint(500, 7000)
    user_balances[user_id] = get_user_balance(user_id) + reward
    user_last_daily[user_id] = now

    await ctx.send(
        f"🎁 {ctx.author.mention}, you've claimed your daily reward of {format_currency(reward)}!\n"
        f"Your new balance: {format_currency(user_balances[user_id])}"
    )

@bot.command(name='s')
async def slots(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_user_balance(user_id)

    if bet <= 0:
        await ctx.send(f"{ctx.author.mention}, bet must be positive!")
        return
    if bet > balance:
        await ctx.send(f"{ctx.author.mention}, insufficient funds! Your balance: {format_currency(balance)}")
        return

    row = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    win_chance = random.random()

    if row[0] == row[1] == row[2]:
        winnings = bet * 10
        result_text = f"🎉 **JACKPOT!** {ctx.author.mention} won {format_currency(winnings)}!"
    elif row[0] == row[1] or row[1] == row[2] or win_chance < 0.5:
        winnings = bet * 2
        result_text = f"🎊 {ctx.author.mention} won {format_currency(winnings)}!"
    else:
        winnings = -bet
        result_text = f"💸 {ctx.author.mention} lost {format_currency(bet)}!"

    user_balances[user_id] += winnings

    embed = discord.Embed(title="🎰 SLOTS", color=discord.Color.blue())
    embed.add_field(name="Result", value=f"| {' | '.join(row)} |", inline=False)
    embed.add_field(name="Bet", value=format_currency(bet), inline=True)
    embed.add_field(name="New Balance", value=format_currency(user_balances[user_id]), inline=True)
    embed.set_footer(text="Play again with !s <amount>")

    await ctx.send(embed=embed)
    await ctx.send(result_text)

@bot.command(name='setbalance')
async def setbalance(ctx, member: discord.Member, amount: int):
    bot_owner_id = 1126869924028088412
    if ctx.author.id != bot_owner_id:
        await ctx.send(f"{ctx.author.mention}, you do not have permission to use this command.")
        return
    if amount < 0:
        await ctx.send(f"{ctx.author.mention}, balance cannot be negative!")
        return

    user_balances[member.id] = amount
    await ctx.send(f"✅ {member.mention}'s balance has been set to {format_currency(amount)}!")

@bot.command(name='bj')
async def blackjack(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_user_balance(user_id)

    if bet <= 0:
        await ctx.send(f"{ctx.author.mention}, bet must be positive!")
        return
    if bet > balance:
        await ctx.send(f"{ctx.author.mention}, insufficient funds! Your balance: {format_currency(balance)}")
        return

    deck = list(CARD_VALUES.keys()) * 4
    random.shuffle(deck)

    user_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    def calculate_hand_value(hand):
        value = sum(CARD_VALUES[card] for card in hand)
        aces = hand.count('A')
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    user_value = calculate_hand_value(user_hand)
    dealer_value = calculate_hand_value(dealer_hand)
    game_active = True

    embed = discord.Embed(title="🃏 BLACKJACK", color=discord.Color.green())
    embed.add_field(name="Your Hand", value=f"{' '.join(user_hand)} (Value: {user_value})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} ❓", inline=False)
    embed.set_footer(text="React with ✅ to HIT or ❌ to STAND")
    msg = await ctx.send(embed=embed)

    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check_reaction(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == msg.id

    while game_active and user_value < 21:
        try:
            reaction, user = await bot.wait_for('reaction_add', check=check_reaction, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up! You automatically stand.")
            break

        if str(reaction.emoji) == "✅":
            user_hand.append(deck.pop())
            user_value = calculate_hand_value(user_hand)
            embed = discord.Embed(title="🃏 BLACKJACK", color=discord.Color.green())
            embed.add_field(name="Your Hand", value=f"{' '.join(user_hand)} (Value: {user_value})", inline=False)
            embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} ❓", inline=False)
            await msg.edit(embed=embed)
            if user_value > 21:
                game_active = False
        elif str(reaction.emoji) == "❌":
            break

    if game_active:
        while dealer_value < 17:
            dealer_hand.append(deck.pop())
            dealer_value = calculate_hand_value(dealer_hand)

    if user_value > 21:
        result = "BUST - You lose!"
        winnings = -bet
    elif dealer_value > 21 or user_value > dealer_value:
        result = "You win!"
        winnings = bet
    elif user_value < dealer_value:
        result = "Dealer wins!"
        winnings = -bet
    else:
        result = "Push (tie)!"
        winnings = 0

    user_balances[user_id] += winnings

    embed = discord.Embed(title="🃏 BLACKJACK - RESULTS", color=discord.Color.green())
    embed.add_field(name="Your Hand", value=f"{' '.join(user_hand)} (Value: {user_value})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"{' '.join(dealer_hand)} (Value: {dealer_value})", inline=False)
    embed.add_field(name="Result", value=result, inline=False)
    embed.add_field(name="New Balance", value=format_currency(user_balances[user_id]), inline=True)
    await ctx.send(embed=embed)

@bot.command(name='cf')
async def coinflip(ctx, *args):
    if len(args) == 2 and args[0].lower() == 'all':
        if ctx.author.id != 1126869924028088412:
            await ctx.send(f"{ctx.author.mention}, you do not have permission to set balances for all users.")
            return
        try:
            amount = int(args[1])
            if amount < 0:
                await ctx.send(f"{ctx.author.mention}, balance cannot be negative!")
                return
        except ValueError:
            await ctx.send(f"{ctx.author.mention}, please provide a valid number for the balance.")
            return
        for user_id in user_balances:
            user_balances[user_id] = amount
        await ctx.send(f"✅ {ctx.author.mention} has set the balance for all users to {format_currency(amount)}!")
        return

    if len(args) == 2:
        try:
            bet = int(args[0])
        except ValueError:
            await ctx.send(f"{ctx.author.mention}, please provide a valid number for the bet.")
            return
        choice = args[1].lower()
    else:
        await ctx.send(f"{ctx.author.mention}, please use the correct format: !cf <bet> <heads/tails>")
        return

    user_id = ctx.author.id
    balance = get_user_balance(user_id)

    if bet <= 0:
        await ctx.send(f"{ctx.author.mention}, bet must be positive!")
        return
    if bet > balance:
        await ctx.send(f"{ctx.author.mention}, insufficient funds! Your balance: {format_currency(balance)}")
        return
    if choice not in ['heads', 'tails']:
        await ctx.send(f"{ctx.author.mention}, please choose 'heads' or 'tails'!")
        return

    result = random.choice(['heads', 'tails'])
    if choice == result:
        winnings = bet
        outcome = f"🎉 You won {format_currency(bet)}!"
    else:
        winnings = -bet
        outcome = f"💸 You lost {format_currency(bet)}!"

    user_balances[user_id] += winnings

    embed = discord.Embed(title="🪙 COIN FLIP", color=discord.Color.gold())
    embed.add_field(name="Your Choice", value=choice.capitalize(), inline=True)
    embed.add_field(name="Result", value=result.capitalize(), inline=True)
    embed.add_field(name="Outcome", value=outcome, inline=False)
    embed.add_field(name="New Balance", value=format_currency(user_balances[user_id]), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def clear(ctx, arg: str = None):
    if ctx.author.guild_permissions.manage_messages:
        if arg and arg.lower() == "all":
            await ctx.channel.purge()
            await ctx.send("All messages deleted!", delete_after=3)
        else:
            await ctx.send("Usage: `!clear all`", delete_after=3)
    else:
        await ctx.send("You don't have permission to do this.", delete_after=3)

@bot.command(name='balance')
async def balance(ctx):
    user_id = ctx.author.id
    balance = get_user_balance(user_id)
    await ctx.send(f"{ctx.author.mention}, your balance is {format_currency(balance)}")

# Run bot with your token below:
TOKEN = "MTM1NDUxMDczNTEyMzgxMjYyMg.GA097Q.v3YwNaN10nDdmwMEaglGln_wUVjbaJc7y78904"
bot.run(TOKEN)
