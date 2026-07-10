import discord
from discord.ext import commands

TOKEN = "あなたのBotトークン"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
# 質問（サンプル）
# ----------------------------
questions = [
    {
        "question": "休日はどちらを選ぶことが多いですか？",
        "A": "友達と遊びに行く",
        "B": "家でゆっくり過ごす"
    },
    {
        "question": "物事を判断するときは？",
        "A": "論理を優先する",
        "B": "気持ちを優先する"
    },
    {
        "question": "旅行では？",
        "A": "計画を立てる",
        "B": "その場で決める"
    }
]

# ユーザーごとの進行状況
sessions = {}

# ----------------------------
# 回答処理
# ----------------------------
async def next_question(interaction: discord.Interaction, answer: str):

    if interaction.user.id not in sessions:
        await interaction.response.send_message(
            "先に診断を開始してください。",
            ephemeral=True
        )
        return

    session = sessions[interaction.user.id]

    session["answers"].append(answer)
    session["index"] += 1

    # 全問終了
    if session["index"] >= len(questions):

        result = "\n".join(
            f"Q{i+1}: {a}"
            for i, a in enumerate(session["answers"])
        )

        embed = discord.Embed(
            title="診断終了！",
            description="お疲れ様でした！",
            color=discord.Color.green()
        )

        embed.add_field(
            name="回答一覧",
            value=result,
            inline=False
        )

        del sessions[interaction.user.id]

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )
        return

    q = questions[session["index"]]

    embed = discord.Embed(
        title=f"質問 {session['index']+1}/{len(questions)}",
        description=q["question"],
        color=discord.Color.blurple()
    )

    embed.add_field(name="A", value=q["A"], inline=False)
    embed.add_field(name="B", value=q["B"], inline=False)

    await interaction.response.edit_message(
        embed=embed,
        view=QuestionView(interaction.user)
    )

# ----------------------------
# 質問画面
# ----------------------------
class QuestionView(discord.ui.View):

    def __init__(self, user):
        super().__init__(timeout=600)
        self.user = user

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
    async def button_a(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.user:
            await interaction.response.send_message(
                "この診断はあなたのものではありません。",
                ephemeral=True
            )
            return

        await next_question(interaction, "A")

    @discord.ui.button(label="B", style=discord.ButtonStyle.success)
    async def button_b(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.user:
            await interaction.response.send_message(
                "この診断はあなたのものではありません。",
                ephemeral=True
            )
            return

        await next_question(interaction, "B")

# ----------------------------
# スタート画面
# ----------------------------
class StartView(discord.ui.View):

    @discord.ui.button(
        label="▶ 診断開始",
        style=discord.ButtonStyle.green
    )
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):

        sessions[interaction.user.id] = {
            "index": 0,
            "answers": []
        }

        q = questions[0]

        embed = discord.Embed(
            title=f"質問 1/{len(questions)}",
            description=q["question"],
            color=discord.Color.blurple()
        )

        embed.add_field(name="A", value=q["A"], inline=False)
        embed.add_field(name="B", value=q["B"], inline=False)

        await interaction.response.edit_message(
            embed=embed,
            view=QuestionView(interaction.user)
        )

# ----------------------------
# コマンド
# ----------------------------
@bot.command()
async def mbti(ctx):

    embed = discord.Embed(
        title="🧠 MBTI診断",
        description=(
            "ようこそ！\n\n"
            f"全 **{len(questions)}問** の質問に答えることで診断できます。\n\n"
            "準備ができたら下のボタンを押してください。"
        ),
        color=discord.Color.orange()
    )

    await ctx.send(
        embed=embed,
        view=StartView()
    )

# ----------------------------
# 起動
# ----------------------------
bot.run(TOKEN)
