import discord
from discord.ext import commands
import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime

# =====================
# Intents設定
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================
# チャンネルID
# =====================
CHANNEL_ID = 1500520708974051498        # 診断チャンネル
RESULT_CHANNEL_ID = 1500500850311954534 # 管理チャンネル

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
            "active_sessions": {},
            "posted_init": False
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# =====================
# 診断データ
# =====================
questions = [
    ("廊下の奥から音がする。", {"A":("確かめる","gryffindor"),
                         "B":("観察","ravenclaw"),
                         "C":("整理","slytherin"),
                         "D":("知らせる","hufflepuff")}),

    ("机に箱がある。", {"A":("触る","gryffindor"),
                   "B":("考える","ravenclaw"),
                   "C":("価値判断","slytherin"),
                   "D":("放置","hufflepuff")}),

    ("予定が重なる。", {"A":("重要な方","slytherin"),
                   "B":("両立","ravenclaw"),
                   "C":("先約","hufflepuff"),
                   "D":("直感","gryffindor")}),

    ("本が落ちている。", {"A":("読む","ravenclaw"),
                     "B":("持つ","gryffindor"),
                     "C":("分析","slytherin"),
                     "D":("戻す","hufflepuff")}),

    ("落とし物。", {"A":("届ける","hufflepuff"),
               "B":("分析","ravenclaw"),
               "C":("使う","slytherin"),
               "D":("追う","gryffindor")}),

    ("説明なしの選択。", {"A":("安全","hufflepuff"),
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

        if interaction.user.id in data["completed"]:
            await interaction.response.send_message("…お前はすでに組み分け済みだ。", ephemeral=True)
            return

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
# 質問
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
# 回答
# =====================
async def handle(interaction, scores, i, house):

    uid = str(interaction.user.id)

    scores[house] += weights[i]

    await interaction.response.send_message(comments[house], ephemeral=True)

    await asyncio.sleep(1)

    data["active_sessions"][uid]["step"] = i + 1
    data["active_sessions"][uid]["scores"] = scores
    save_data(data)

    if i in [2,4]:
        await interaction.followup.send("……ふむ……", ephemeral=True)
        await asyncio.sleep(1)

    if i+1 < len(questions):
        await ask(interaction, scores, i+1)
    else:
        await result(interaction, scores)

# =====================
# 結果
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

    await interaction.followup.send(
        f"🧙‍♂️ {house_names[result]}！\n\n{comments[result]}",
        ephemeral=True
    )

    ch = bot.get_channel(RESULT_CHANNEL_ID)
    if ch:
        await ch.send(f"{member.mention} → {house_names[result]}")

# =====================
# 初期投稿（重複防止・安定版）
# =====================
@bot.event
async def on_ready():
    print("ready")

    bot.add_view(StartView())

    if data.get("posted_init"):
        return

    try:
        ch = await bot.fetch_channel(CHANNEL_ID)

        await ch.send(
            "🧙‍♂️ 組み分け帽子があなたを待っている…\n診断を始めるかね？",
            view=StartView()
        )

        data["posted_init"] = True
        save_data(data)

        print("初期メッセージ送信成功")

    except Exception as e:
        print("初期送信エラー:", e)

# =====================
# 起動
# =====================
bot.run("DISCORD_TOKEN")
