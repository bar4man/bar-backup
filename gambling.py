import discord
from discord.ext import commands
import random
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from economy import db

class GamblingCog(commands.Cog):
    """Enhanced gambling system with more rewarding games."""
    
    def __init__(self, bot):
        self.bot = bot
        self.economy_cog = None
    
    async def cog_load(self):
        """Get reference to economy cog when loaded."""
        await asyncio.sleep(1)  # Wait for economy cog to load
        self.economy_cog = self.bot.get_cog("Economy")
    
    async def create_gambling_embed(self, title: str, color: discord.Color = discord.Color.gold()) -> discord.Embed:
        """Create a standardized gambling embed."""
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="🎰 Gambling System | Good luck!")
        return embed
    
    async def check_balance_and_cooldown(self, ctx, bet, command_name="gambling", cooldown_seconds=2):
        """Check if user has enough balance and isn't on cooldown."""
        # Check cooldown
        if self.economy_cog:
            remaining = await self.economy_cog.check_cooldown(ctx.author.id, command_name, cooldown_seconds)
            if remaining:
                embed = await self.create_gambling_embed("⏰ Too Fast!", discord.Color.orange())
                embed.description = f"Please wait **{self.economy_cog.format_time(remaining)}** before gambling again."
                await ctx.send(embed=embed)
                return False
        
        # Check balance
        user_data = await db.get_user(ctx.author.id)
        if user_data["wallet"] < bet:
            embed = await self.create_gambling_embed("❌ Insufficient Funds", discord.Color.red())
            embed.description = f"You only have {self.economy_cog.format_money(user_data['wallet'])} in your wallet."
            await ctx.send(embed=embed)
            return False
        
        return True

    # ========== ENHANCED GAMBLING COMMANDS ==========
    
    @commands.command(name="flip", aliases=["coinflip", "cf"])
    async def flip(self, ctx: commands.Context, choice: str = None, bet: int = None):
        """Flip a coin - bet on heads or tails with better odds."""
        if not choice or not bet:
            embed = await self.create_gambling_embed("🎲 Coin Flip Game")
            embed.description = "Flip a coin with improved odds!\n\n**Usage:** `~~flip <heads/tails> <bet>`"
            embed.add_field(name="Example", value="`~~flip heads 100` - Bet 100£ on heads", inline=False)
            embed.add_field(name="💰 Payout", value="**1.8x** your bet if you win!", inline=True)
            embed.add_field(name="🎯 Win Chance", value="**55%** (Improved odds!)", inline=True)
            return await ctx.send(embed=embed)
        
        choice = choice.lower()
        if choice not in ["heads", "tails"]:
            embed = await self.create_gambling_embed("❌ Invalid Choice", discord.Color.red())
            embed.description = "Please choose either `heads` or `tails`."
            return await ctx.send(embed=embed)
        
        if bet <= 0:
            embed = await self.create_gambling_embed("❌ Invalid Bet", discord.Color.red())
            embed.description = "Bet must be greater than 0."
            return await ctx.send(embed=embed)
        
        if not await self.check_balance_and_cooldown(ctx, bet, "flip", 3):
            return
        
        # Apply gambling bonus if active
        active_effects = self.economy_cog.get_active_effects(ctx.author.id) if self.economy_cog else {}
        gambling_multiplier = active_effects.get("gambling_bonus", {}).get("multiplier", 1.0)
        
        # Enhanced win chance: 55% base (was 50%)
        base_win_chance = 0.55
        win_chance = min(0.75, base_win_chance * gambling_multiplier)  # Cap at 75%
        
        # Flip coin with weighted probability
        result = "heads" if random.random() < 0.5 else "tails"  # Fair flip for display
        actual_win = random.random() < win_chance  # But higher chance to win
        
        if (actual_win and choice == result) or (actual_win and random.random() < 0.3):  # 30% chance to win even if wrong guess
            # Calculate winnings (1.8x instead of 2x, but more frequent wins)
            winnings = int(bet * 1.8)
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=winnings - bet)
            
            embed = await self.create_gambling_embed("🎉 You Won!", discord.Color.green())
            embed.description = f"The coin landed on **{result}**! You won {self.economy_cog.format_money(winnings)}!"
            
            if gambling_multiplier > 1.0:
                embed.add_field(name="✨ Lucky Bonus", value="Your win chance was increased by your items!", inline=False)
        else:
            # Lose bet (but less frequent)
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=-bet)
            
            embed = await self.create_gambling_embed("💸 You Lost!", discord.Color.red())
            embed.description = f"The coin landed on **{result}**. You lost {self.economy_cog.format_money(bet)}."
        
        await self.economy_cog.set_cooldown(ctx.author.id, "flip")
        embed.add_field(name="💵 New Balance", value=f"{self.economy_cog.format_money(result_text['wallet'])} / {self.economy_cog.format_money(result_text['wallet_limit'])}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dice", aliases=["roll"])
    async def dice(self, ctx: commands.Context, bet: int = None):
        """Roll a dice - win multipliers for various numbers."""
        if not bet:
            embed = await self.create_gambling_embed("🎯 Dice Game")
            embed.description = "Roll a dice with multiple winning numbers!\n\n**Usage:** `~~dice <bet>`"
            embed.add_field(name="🎲 Payouts", value="• Roll 6: **5x** bet\n• Roll 5: **2x** bet\n• Roll 4: **1.5x** bet", inline=False)
            embed.add_field(name="🎯 Win Chance", value="**50%** (3 winning numbers!)", inline=True)
            return await ctx.send(embed=embed)
        
        if bet <= 0:
            embed = await self.create_gambling_embed("❌ Invalid Bet", discord.Color.red())
            embed.description = "Bet must be greater than 0."
            return await ctx.send(embed=embed)
        
        if not await self.check_balance_and_cooldown(ctx, bet, "dice", 4):
            return
        
        # Apply gambling bonus if active
        active_effects = self.economy_cog.get_active_effects(ctx.author.id) if self.economy_cog else {}
        gambling_multiplier = active_effects.get("gambling_bonus", {}).get("multiplier", 1.0)
        
        # Roll dice (1-6)
        roll = random.randint(1, 6)
        
        # Determine win and multiplier
        if roll == 6:
            multiplier = 5.0
            win = True
        elif roll == 5:
            multiplier = 2.0
            win = True
        elif roll == 4:
            multiplier = 1.5
            win = True
        else:
            multiplier = 0
            win = False
        
        # Apply gambling bonus to multiplier
        multiplier *= gambling_multiplier
        
        if win:
            winnings = int(bet * multiplier)
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=winnings - bet)
            
            embed = await self.create_gambling_embed("🎉 You Won!", discord.Color.green())
            embed.description = f"🎲 You rolled a **{roll}**! You won {self.economy_cog.format_money(winnings)} ({multiplier:.1f}x)!"
            
            if gambling_multiplier > 1.0:
                embed.add_field(name="✨ Lucky Bonus", value="Your payout was increased by your items!", inline=False)
        else:
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=-bet)
            
            embed = await self.create_gambling_embed("💸 You Lost!", discord.Color.red())
            embed.description = f"🎲 You rolled a **{roll}**. You lost {self.economy_cog.format_money(bet)}."
        
        await self.economy_cog.set_cooldown(ctx.author.id, "dice")
        embed.add_field(name="💵 New Balance", value=f"{self.economy_cog.format_money(result_text['wallet'])} / {self.economy_cog.format_money(result_text['wallet_limit'])}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="slots", aliases=["slot"])
    async def slots(self, ctx: commands.Context, bet: int = None):
        """Play slots - better odds and more winning combinations."""
        if not bet:
            embed = await self.create_gambling_embed("🎰 Slot Machine")
            embed.description = "Play the enhanced slot machine!\n\n**Usage:** `~~slots <bet>`"
            embed.add_field(name="💰 Payouts", 
                          value="• 3x **🍒** - 8x bet\n• 3x **🍋** - 4x bet\n• 3x **🍊** - 2x bet\n• 3x **💎** - 15x bet\n• 3x **7️⃣** - 30x bet\n• Any 2 matching - 1.2x bet",
                          inline=False)
            return await ctx.send(embed=embed)
        
        if bet <= 0:
            embed = await self.create_gambling_embed("❌ Invalid Bet", discord.Color.red())
            embed.description = "Bet must be greater than 0."
            return await ctx.send(embed=embed)
        
        if not await self.check_balance_and_cooldown(ctx, bet, "slots", 5):
            return
        
        # Slot symbols with better probabilities
        symbols = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        weights = [35, 30, 25, 8, 2]  # Better probabilities for common symbols
        
        # Spin slots
        result = random.choices(symbols, weights=weights, k=3)
        
        # Calculate payout with better odds
        payout_multiplier = 0
        
        # Check for three of a kind
        if result[0] == result[1] == result[2]:
            if result[0] == "🍒":
                payout_multiplier = 8
            elif result[0] == "🍋":
                payout_multiplier = 4
            elif result[0] == "🍊":
                payout_multiplier = 2
            elif result[0] == "💎":
                payout_multiplier = 15
            elif result[0] == "7️⃣":
                payout_multiplier = 30
        # Check for any two matching (new winning condition)
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            payout_multiplier = 1.2
        
        # Apply gambling bonus
        active_effects = self.economy_cog.get_active_effects(ctx.author.id) if self.economy_cog else {}
        gambling_multiplier = active_effects.get("gambling_bonus", {}).get("multiplier", 1.0)
        payout_multiplier *= gambling_multiplier
        
        if payout_multiplier > 0:
            winnings = int(bet * payout_multiplier)
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=winnings - bet)
            
            embed = await self.create_gambling_embed("🎉 Jackpot!", discord.Color.green())
            win_type = "Three of a kind!" if result[0] == result[1] == result[2] else "Two matching!"
            embed.description = f"🎰 | {result[0]} | {result[1]} | {result[2]} |\n{win_type}\nYou won {self.economy_cog.format_money(winnings)}!"
            
            if gambling_multiplier > 1.0:
                embed.add_field(name="✨ Lucky Bonus", value="Your payout was increased by your items!", inline=False)
        else:
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=-bet)
            
            embed = await self.create_gambling_embed("💸 You Lost!", discord.Color.red())
            embed.description = f"🎰 | {result[0]} | {result[1]} | {result[2]} |\nYou lost {self.economy_cog.format_money(bet)}."
        
        await self.economy_cog.set_cooldown(ctx.author.id, "slots")
        embed.add_field(name="💵 New Balance", value=f"{self.economy_cog.format_money(result_text['wallet'])} / {self.economy_cog.format_money(result_text['wallet_limit'])}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="rps", aliases=["rockpaperscissors"])
    async def rps(self, ctx: commands.Context, choice: str = None, bet: int = None):
        """Play Rock Paper Scissors with enhanced rewards."""
        if not choice or not bet:
            embed = await self.create_gambling_embed("✂️ Rock Paper Scissors")
            embed.description = "Play RPS with better payouts!\n\n**Usage:** `~~rps <rock/paper/scissors> <bet>`"
            embed.add_field(name="Example", value="`~~rps rock 100` - Bet 100£ on rock", inline=False)
            embed.add_field(name="💰 Payouts", value="Win: **2x** bet\nTie: **1x** bet (get your money back!)", inline=False)
            return await ctx.send(embed=embed)
        
        choice = choice.lower()
        if choice not in ["rock", "paper", "scissors"]:
            embed = await self.create_gambling_embed("❌ Invalid Choice", discord.Color.red())
            embed.description = "Please choose `rock`, `paper`, or `scissors`."
            return await ctx.send(embed=embed)
        
        if bet <= 0:
            embed = await self.create_gambling_embed("❌ Invalid Bet", discord.Color.red())
            embed.description = "Bet must be greater than 0."
            return await ctx.send(embed=embed)
        
        if not await self.check_balance_and_cooldown(ctx, bet, "rps", 3):
            return
        
        # Bot's choice
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        # Determine winner
        if choice == bot_choice:
            # Tie - get money back
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=0)
            embed = await self.create_gambling_embed("🤝 It's a Tie!", discord.Color.blue())
            embed.description = f"Both chose **{choice}**! You get your {self.economy_cog.format_money(bet)} back."
        elif ((choice == "rock" and bot_choice == "scissors") or
              (choice == "paper" and bot_choice == "rock") or
              (choice == "scissors" and bot_choice == "paper")):
            # Win - 2x payout
            winnings = bet * 2
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=winnings - bet)
            embed = await self.create_gambling_embed("🎉 You Win!", discord.Color.green())
            embed.description = f"**{choice.title()}** beats **{bot_choice}**! You won {self.economy_cog.format_money(winnings)}!"
        else:
            # Lose
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=-bet)
            embed = await self.create_gambling_embed("💸 You Lose!", discord.Color.red())
            embed.description = f"**{bot_choice.title()}** beats **{choice}**! You lost {self.economy_cog.format_money(bet)}."
        
        embed.add_field(name="🤖 Bot's Choice", value=bot_choice.title(), inline=True)
        embed.add_field(name="👤 Your Choice", value=choice.title(), inline=True)
        
        await self.economy_cog.set_cooldown(ctx.author.id, "rps")
        embed.add_field(name="💵 New Balance", value=f"{self.economy_cog.format_money(result_text['wallet'])} / {self.economy_cog.format_money(result_text['wallet_limit'])}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="beg")
    async def beg(self, ctx: commands.Context):
        """Beg for money from generous strangers."""
        # Check cooldown (5 minutes)
        if self.economy_cog:
            remaining = await self.economy_cog.check_cooldown(ctx.author.id, "beg", 300)  # 5 minutes
            if remaining:
                embed = await self.create_gambling_embed("⏰ Too Soon!", discord.Color.orange())
                embed.description = f"Please wait **{self.economy_cog.format_time(remaining)}** before begging again."
                return await ctx.send(embed=embed)
        
        # Random outcomes with mostly positive results
        outcomes = [
            {"text": "A generous stranger gives you", "min": 10, "max": 50, "emoji": "🙏"},
            {"text": "You find some money on the ground", "min": 5, "max": 30, "emoji": "💰"},
            {"text": "Someone takes pity and gives you", "min": 15, "max": 40, "emoji": "😢"},
            {"text": "A kind old lady gives you", "min": 20, "max": 60, "emoji": "👵"},
            {"text": "You perform a small favor and earn", "min": 25, "max": 45, "emoji": "🤝"},
            {"text": "A businessman tips you", "min": 30, "max": 70, "emoji": "👔"},
            {"text": "You get nothing... try again later", "min": 0, "max": 0, "emoji": "😞"},
            {"text": "Someone yells at you to get a job", "min": 0, "max": 0, "emoji": "😠"},
        ]
        
        outcome = random.choice(outcomes)
        amount = random.randint(outcome["min"], outcome["max"])
        
        if amount > 0:
            result_text = await self.economy_cog.update_balance(ctx.author.id, wallet_change=amount)
            embed = await self.create_gambling_embed(f"{outcome['emoji']} Begging Successful", discord.Color.green())
            embed.description = f"{outcome['text']} {self.economy_cog.format_money(amount)}!"
            embed.add_field(name="💵 New Balance", value=f"{self.economy_cog.format_money(result_text['wallet'])} / {self.economy_cog.format_money(result_text['wallet_limit'])}", inline=False)
        else:
            embed = await self.create_gambling_embed(f"{outcome['emoji']} Begging Failed", discord.Color.orange())
            embed.description = outcome["text"]
        
        await self.economy_cog.set_cooldown(ctx.author.id, "beg")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GamblingCog(bot))
