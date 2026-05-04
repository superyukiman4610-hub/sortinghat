import discord
from discord.ext import commands
import os

# ===== Discord設定 =====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 設定 =====
CHANNEL_ID = 1500520708974051498

# ===== 質問 =====
questions = [
    {
        "question": "…ふむ。暗い森の中で、遠くにかすかな光が見える。お前ならどうする？",
        "options": {
            "A": ("慎重に様子を見ながら近づく", "ravenclaw"),
            "B": ("危険でもまっすぐ進む", "gryffindor"),
            "C": ("役に立つものがないか周囲を探す", "slytherin"),
            "D": ("仲間を探して一緒に進む", "hufflepuff")
        }
    },
    {
        "question": "授業の後、誰もいない教室に不思議な箱が残されている…どうする？",
        "options": {
            "A": ("中身を推理してから開ける", "ravenclaw"),
            "B": ("すぐ開ける", "gryffindor"),
            "C": ("価値があるか考える", "slytherin"),
            "D": ("先生に届ける", "hufflepuff")
        }
    },
    {
        "question": "友人が困っているが、自分にも大事な用事がある。どうする？",
        "options": {
            "A": ("助けつつ効率よく終わらせる", "slytherin"),
            "B": ("迷わず助ける", "hufflepuff"),
            "C": ("解決策を考えてアドバイス", "ravenclaw"),
            "D": ("自分を後回しにしてでも助ける", "gryffindor")
        }
    },
    {
        "question": "未知の魔法書を見つけた。どう扱う？",
        "options": {
            "A": ("安全を確認して研究する", "ravenclaw"),
            "B": ("試してみる", "gryffindor"),
            "C": ("使い道を考える", "slytherin"),
            "D": ("共有して皆で読む", "hufflepuff")
        }
    },
    {
        "question": "勝利が目前だが、ルール違反をすれば確実に勝てる…どうする？",
        "options": {
            "A": ("正々堂々戦う", "gryffindor"),
            "B": ("ルールを守る", "hufflepuff"),
            "C": ("状況によって判断する", "slytherin"),
            "D": ("別の方法を考える", "ravenclaw")
        }
    }
]

houses = ["gryffindor", "slytherin", "ravenclaw", "hufflepuff"]
priority = ["gryffindor", "slytherin", "ravenclaw", "hufflepuff"]

completed_users = set()

# ===== スタートボタン =====
class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="はい", style=discord.ButtonStyle.success, custom_id="start_sorting")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id in completed_users:
            await interaction.response.send_message(
                "…お前はすでに組み分けられておる。",
                ephemeral=True
            )
            return

        scores = {house: 0 for house in houses}

        await interaction.response.send_message(
            "…おやおや、新しい生徒か。さあ、頭をこちらへ…",
            ephemeral=True
        )

        await send_question(interaction, scores, 0)

# ===== 質問UI =====
class QuestionView(discord.ui.View):
    def __init__(self, interaction, scores, q_index):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.scores = scores
        self.q_index = q_index

        q = questions[q_index]
        for key, (text, house) in q["options"].items():
            self.add_item(AnswerButton(key, text, house))

class AnswerButton(discord.ui.Button):
    def __init__(self, key, text, house):
        super().__init__(label=f"{key}: {text}", style=discord.ButtonStyle.primary)
        self.house = house

    async def callback(self, interaction: discord.Interaction):
        view: QuestionView = self.view

        if interaction.user != view.interaction.user:
            await interaction.response.send_message("これは君の試練ではない…", ephemeral=True)
            return

        view.scores[self.house] += 1
        view.stop()

        next_index = view.q_index + 1

        await interaction.response.defer(ephemeral=True)

        if next_index < len(questions):
            await interaction.followup.send("…なるほど……次へ進もう。", ephemeral=True)
            await send_question(interaction, view.scores, next_index)
        else:
            await interaction.followup.send("…すべて見せてもらった…", ephemeral=True)
            await show_result(interaction, view.scores)

# ===== 質問送信 =====
async def send_question(interaction, scores, index):
    q = questions[index]

    text = q["question"]
    for key, (desc, _) in q["options"].items():
        text += f"\n{key}: {desc}"

    view = QuestionView(interaction, scores, index)
    await interaction.followup.send(text, view=view, ephemeral=True)

# ===== 結果 =====
async def show_result(interaction, scores):
    max_score = max(scores.values())
    candidates = [k for k, v in scores.items() if v == max_score]

    for house in priority:
        if house in candidates:
            result = house
            break

    messages = {
        "gryffindor": "グリフィンドール！",
        "slytherin": "スリザリン！",
        "ravenclaw": "レイブンクロー！",
        "hufflepuff": "ハッフルパフ！"
    }

    await interaction.followup.send(
        f"…見えるぞ…お前の資質が…\n{messages[result]}",
        ephemeral=True
    )

    try:
        guild = interaction.guild
        member = interaction.user

        role_map = {
            "gryffindor": "グリフィンドール",
            "slytherin": "スリザリン",
            "ravenclaw": "レイブンクロー",
            "hufflepuff": "ハッフルパフ"
        }

        role = discord.utils.get(guild.roles, name=role_map[result])

        if role:
            await member.add_roles(role)

    except Exception as e:
        print(f"ロール付与エラー: {e}")

    completed_users.add(interaction.user.id)

# ===== 起動時 =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    bot.add_view(StartView())

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(
            "🧙‍♂️ 組み分け帽子があなたを待っている…\n診断を始めるかね？",
            view=StartView()
        )

# ===== 起動 =====
bot.run(os.getenv("TOKEN"))
