import discord
from discord.ext import commands
import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================
# チャンネル設定（固定）
# =====================
CHANNEL_ID = 1500520708974051498        # 診断専用
RESULT_CHANNEL_ID = 1500500850311954534  # 管理チャンネル

DATA_FILE = "data.json"

# =====================
# データ管理
# =====================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "house_count": {},
            "daily_log": {},
            "completed": [],
            "active_sessions": {}
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

completed = set()

# =====================
# 質問
# =====================
questions = [
    ("廊下の奥から音がする。",
     {"A":("確かめる","gryffindor"),
      "B":("観察","ravenclaw"),
      "C":("整理","slytherin"),
      "D":("知らせる","hufflepuff")}),

    ("机に箱がある。",
     {"A":("触る","gryffindor"),
      "B":("考える","ravenclaw"),
      "C":("価値判断","slytherin"),
      "D":("放置","hufflepuff")}),

    ("予定が重なる。",
     {"A":("重要な方","slytherin"),
      "B":("両立","ravenclaw"),
      "C":("先約","hufflepuff"),
      "D":("直感","gryffindor")}),

    ("本が落ちている。",
     {"A":("読む","ravenclaw"),
      "B":("持つ","gryffindor"),
      "C":("分析","slytherin"),
      "D":("戻す","hufflepuff")}),

    ("落とし物。",
     {"A":("届ける","hufflepuff"),
      "B":("分析","ravenclaw"),
      "C":("使う","slytherin"),
      "D":("追う","gryffindor")}),

    ("説明なしの選択。",
     {"A":("安全","hufflepuff"),
      "B":("意味","ravenclaw"),
      "C":("成果","slytherin"),
      "D":("直感","gryffindor")})
]

weights = [1.0, 1.0, 1.2, 1.2, 1.5, 2.0]

house_names = {
    "gryffindor":"グリフィンドール",
    "slytherin":"スリザリン",
    "ravenclaw":"レイブンクロー",
    "hufflepuff":"ハッフルパフ"
}

comments = {
    "gryffindor":"行動が速く直感型だ。",
    "slytherin":"結果重視の判断力がある。",
    "ravenclaw":"思考と分析が強い。",
    "hufflepuff":"調和と誠実さを重視する。"
}

# =====================
# スタートUI
# =====================
class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="はい", style=discord.ButtonStyle.success)
    async def start(self, interaction, button):

        uid = str(interaction.user.id)

        # 1回制限
        if interaction.user.id in data["completed"]:
            await interaction.response.send_message("…お前はすでに組み分け済みだ。", ephemeral=True)
            return

        # 途中復帰
        if uid in data["active_sessions"]:
            session = data["active_sessions"][uid]
            await interaction.response.send_message("…続きから始めるぞ。", ephemeral=True)
            await ask(interaction, session["scores"], session["step"])
            return

        scores = {k:0 for k in house_names}

        data["active_sessions"][uid] = {
            "scores": scores,
            "step": 0
        }
        save_data(data)

        await interaction.response.send_message("……帽子をかぶりなさい。", ephemeral=True)
        await ask(interaction, scores, 0)

# =====================
# 質問処理
# =====================
async def ask(interaction, scores, i):

    q, opts = questions[i]

    view = discord.ui.View(timeout=120)

    async def make_callback(house):
        async def callback(inter):
            await handle(inter, scores, i, house)
        return callback

    for k,(text,house) in opts.items():
        btn = discord.ui.Button(label=f"{k}: {text}", style=discord.ButtonStyle.primary)
        btn.callback = await make_callback(house)
        view.add_item(btn)

    await interaction.followup.send(f"🧙‍♂️ {q}", view=view, ephemeral=True)

# =====================
# 回答処理
# =====================
async def handle(interaction, scores, i, house):

    uid = str(interaction.user.id)

    scores[house] += weights[i]

    await interaction.response.send_message(comments[house], ephemeral=True)

    await asyncio.sleep(1)

    # 進行保存
    data["active_sessions"][uid]["step"] = i + 1
    data["active_sessions"][uid]["scores"] = scores
    save_data(data)

    if i in [2,4]:
        await interaction.followup.send("……ふむ……考えさせてもらおう……", ephemeral=True)
        await asyncio.sleep(1)

    if i+1 < len(questions):
        await ask(interaction, scores, i+1)
    else:
        await result(interaction, scores)

# =====================
# 結果処理
# =====================
async def result(interaction, scores):

    uid = str(interaction.user.id)
    member = interaction.user
    guild = interaction.guild

    max_score = max(scores.values())
    candidates = [k for k,v in scores.items() if v == max_score]
    result = candidates[0]

    await interaction.followup.send("……決まった。", ephemeral=True)
    await asyncio.sleep(2)

    role = discord.utils.get(guild.roles, name=house_names[result])

    if role:
        try:
            await member.add_roles(role)
        except:
            pass

    today = datetime.now().strftime("%Y-%m-%d")

    data["house_count"][result] = data["house_count"].get(result,0)+1
    data["daily_log"].setdefault(today, []).append(result)

    data["completed"].append(member.id)

    if uid in data["active_sessions"]:
        del data["active_sessions"][uid]

    save_data(data)

    # ユーザー
    await interaction.followup.send(
        f"🧙‍♂️ {house_names[result]}！\n\n{comments[result]}",
        ephemeral=True
    )

    # 管理チャンネル
    ch = bot.get_channel(RESULT_CHANNEL_ID)
    if ch:
        await ch.send(f"{member.mention} → {house_names[result]}")

    await send_stats()

# =====================
# 統計表示
# =====================
async def send_stats():

    ch = bot.get_channel(RESULT_CHANNEL_ID)
    if not ch:
        return

    house = data["house_count"]

    today = datetime.now().strftime("%Y-%m-%d")
    daily = defaultdict(int)

    for h in data["daily_log"].get(today, []):
        daily[h]+=1

    rank = sorted(daily.items(), key=lambda x:x[1], reverse=True)

    house_text = "\n".join([f"{k}:{v}" for k,v in house.items()]) or "なし"
    rank_text = "\n".join([f"{i+1}位 {k}:{v}" for i,(k,v) in enumerate(rank)]) or "なし"

    await ch.send(f"📊統計\n\n🏰寮\n{house_text}\n\n📅今日\n{rank_text}")

# =====================
# !stats
# =====================
@bot.command()
async def stats(ctx):
    await send_stats()

# =====================
# 起動
# =====================
@bot.event
async def on_ready():
    print("ready")
    bot.add_view(StartView())

    ch = bot.get_channel(CHANNEL_ID)
    if ch:
        await ch.send(
            "🧙‍♂️ 組み分け帽子があなたを待っている…",
            view=StartView()
        )

bot.run(os.getenv("DISCORD_TOKEN"))
