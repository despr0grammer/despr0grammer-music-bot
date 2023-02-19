#CÓDIGO SIN TOCAR URL DE MEESEEKS FUNCIONANDO
import discord
import asyncio
from discord.ext import commands
import youtube_dl
from discord import FFmpegPCMAudio
import random
from youtubesearchpython import VideosSearch
import re


bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]  
}

async def download_info(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info

# Personalizar la ayuda del bot
class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Comandos disponibles:")
        for cog, commands in mapping.items():
            command_list = [f"{command.name}: {command.short_doc}" for command in commands]
            if command_list:
                cog_name = getattr(cog, "qualified_name", "Sin categoría")
                embed.add_field(name=cog_name, value="\n".join(command_list), inline=False)
        await self.get_destination().send(embed=embed)

bot.help_command = CustomHelpCommand()

@bot.command()
async def ayuda(ctx):
    """Muestra los comandos disponibles en una ventana desplegable."""
    embed = discord.Embed(title='Comandos disponibles', color=discord.Color.blue())

    for command in bot.commands:
        if not command.hidden:
            embed.add_field(name=command.name, value=command.help or "Sin descripción.", inline=False)

    await ctx.send(embed=embed)

@bot.command(help='sólo ADMIN')
@commands.is_owner()
async def serveradmin(ctx):
    for guild in bot.guilds:
        member_names = [member.name for member in guild.members]
        msg = f"Server Name: {guild.name}\nServer ID: {guild.id}\nMember Count: {guild.member_count}\nMembers: {', '.join(member_names)}"
        await ctx.send(msg)

@bot.command(help='sólo ADMIN')
@commands.is_owner()
async def servers(ctx):
    for guild in bot.guilds:
        msg = f"Server Name: {guild.name}\nServer ID: {guild.id}\nMember Count: {guild.member_count}\n"
        await ctx.send(msg)

@bot.command(name='reto', help='Selecciona dos miembros aleatorios conectados en el canal de voz.')
async def reto(ctx):
    voice_channel = ctx.author.voice.channel
    members = voice_channel.members if voice_channel else []
    if len(members) < 2:
        await ctx.send("No hay suficientes miembros conectados en el canal de voz.")
        return
    member1, member2 = random.sample(members, 2)
    await ctx.send(f"{member1.mention} debe cumplir un reto de {member2.mention} !")

@bot.command(help='Selecciona un usuario completamente al azar.')
async def ruleta(ctx):
    voice_channel = ctx.author.voice.channel
    members = voice_channel.members

    selected_user = random.choice(members)

    await ctx.send(f"El usuario seleccionado es: {selected_user.name}")

queue = {}
current_song = {}

@bot.command(help='Para reproducir una canción y/o agregarla a una lista.')
async def play(ctx, *, arg: str):
    global queue
    global current_song

    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is None or voice.channel != ctx.author.voice.channel:
        voice = await ctx.author.voice.channel.connect()

    url_pattern = re.compile(r'https?://\S+')
    if url_pattern.match(arg):
        url = arg
    else:
        videos_search = VideosSearch(arg, limit=1)
        url = videos_search.result()["result"][0]["link"]

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        title = info['title']
        server = ctx.guild.id

        if server not in queue:
            queue[server] = asyncio.Queue()
        if server not in current_song:
            current_song[server] = None

        await ctx.send(f"Se ha agregado a la lista de reproducción: {title}")
        await queue[server].put({
        'title': title,
        'url': audio_url,
        'ctx': ctx,
    })
        if not voice.is_playing() and not voice.is_paused():
            await play_next_song(voice, ctx, server)

async def play_next_song(voice, ctx, server):
    global queue
    global current_song

    if queue[server].empty():
        current_song[server] = None
        return

    song = await queue[server].get()
    current_song[server] = song

    source = discord.FFmpegPCMAudio(song['url'])
    voice.play(source)
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

    await ctx.send(f'Reproduciendo: {song["title"]}')
    while voice.is_playing():
        await asyncio.sleep(1)

    await play_next_song(voice, ctx, server)

@bot.command(help='Para saltar a la siguiente canción en la lista.')
async def skip(ctx):
    server = ctx.guild.id
    voice = ctx.guild.voice_client

    if voice is None or voice.channel != ctx.author.voice.channel:
        await ctx.send("No estoy conectado a un canal de voz o no estamos en el mismo canal.")
        return

    if voice.is_paused() or voice.is_playing():
        voice.stop()
        await play_next_song(voice, ctx, server)
        await ctx.send("Saltando canción.")
    else:
        await ctx.send("No hay nada que saltar.")

@bot.command(help='sólo ADMIN')
@commands.is_owner()
async def listaadmin(ctx):
    global queue

    if not queue:
        await ctx.send("No hay canciones en cola.")
        return

    output = ""
    for server in queue:
        if not queue[server].empty():
            song_list = "\n".join([f"{i + 1}. {song['title']}" for i, song in enumerate(list(queue[server]._queue))])
            output += f"Lista de reproducción para el servidor {bot.get_guild(server).name}:\n{song_list}\n\n"

    if output == "":
        output = "No hay canciones en cola."
    await ctx.send(output)

@bot.command(help='sólo ADMIN')
@commands.is_owner()
async def mensaje(ctx, *, message):
    if ctx.author.id != "Your Discord ID":
        return

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    sent_message = await channel.send(message)
                    break
                except:
                    continue

    await asyncio.sleep(600)
    await sent_message.delete()
    
@bot.command(help='Muestra las siguientes canciones en cola.')
async def lista(ctx):
    global queue

    if ctx.guild.id not in queue or queue[ctx.guild.id].empty():
        await ctx.send("La lista de reproducción está vacía.")
        return

    queue_list = list(queue[ctx.guild.id]._queue)
    queue_message = ""
    for i, song in enumerate(queue_list):
        queue_message += f"{i+1}. {song['title']}\n"

    await ctx.send(f"Canciones en cola:\n{queue_message}")

@bot.command(help='Conecta el bot a un canal de voz.')
async def join(ctx):

    voice_channel = ctx.author.voice.channel
    vc = await voice_channel.connect()

@bot.command(help='Desconecta el bot de un canal de voz.')
async def leave(ctx):

    vc = ctx.voice_client
    if vc:
        await vc.disconnect()

@bot.command(help='Execute order 66 - Emperor Palpatine.')
async def order(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return


    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=sfNZThKEU1Q"
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Execute order 66"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1  

@bot.command(help='Sin descripción, sólo hazlo.')
async def moan(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=F81LPqjSlhM"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Moan .."))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1  

@bot.command(help='Hello There - Obi Wan Kenobi.')
async def ht(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=Ns0zbSiKxpA"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Hello There!"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1   

@bot.command(help='Audio de fábrica de Marti.')
async def marti(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=zwsRq3suTRU"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Sos puro pecho wevón"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1    

@bot.command(help='C mamo - Franco Escamilla.')
async def cmamo(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=rzxPdwQX7bI"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("HAHA C MAMO"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Argentino ebrio, sin comentarios.')
async def puni(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=vbWymUYZSJg"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Move bitch.')
async def move(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=BwUBNGQ2AS0"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Pa que me la bese uwu.')
async def trece(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=xKOu_kFjvJQ"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Directed by - No necesita más descripción.')
async def panpan(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    # Verifica si ya estás conectado a un canal de voz
    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=qzbtdclsJXw"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Música triste, para momentos aún más tristes.')
async def sad(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=teP_sazpYTU"

    # Descarga el audio con youtube_dl
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Amogus.')
async def sus(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=MO9IHZ3qEN8"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Roblox, para niños rata.')
async def oof(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=JHIeIBMil2o"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Trompeta de rechazo.')
async def bad(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=425aq_LBZy8"
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Gatito turip ip ip.')
async def turip(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=W6it0R87t_I"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Sonido de desconexión.')
async def bye(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=ioNd_hLYti4"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 50

@bot.command(help='QUE BENDICION AAAAAHHHH.')
async def qb(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=o6NiR4-h-MU"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Homero Douh.')
async def dou(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=FoACuGFGKuA"

    with youtube_dl.YoutubeDL({'verbose': True, **ydl_opts}) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Sonido de Bob Esponja decepcionado.')
async def dece(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=Gbw3UdE0xVo"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Amarillos los plátanos.')
async def platanos(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=vynIUZjwJ5Y"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 1

@bot.command(help='Its Britney bitch.')
async def bb(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=MMtdmK31epQ"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command(help='A sos vivo.')
async def vivo(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=AUWcNzYd9HA"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 50

@bot.command(help='Esa horrible voz - Betty la Fea.')
async def bt(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=p7I9Es5xLl4"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command(help='Notificación Troll.')
async def noti(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=rIPq9Fl5r44"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command(help='Pero no le pregunté.')
async def jevi(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=cztRuhxcFiA"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command(help='Run.')
async def run(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=opk5XJ023ms"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command(help='X Files.')
async def confirmed(ctx):
    if ctx.author.voice is None:
        await ctx.send("Tienes que estar conectado a un canal de voz para usar este comando.")
        return

    voice = ctx.guild.voice_client
    if voice is not None and voice.channel == ctx.author.voice.channel:
        pass
    else:
        voice = await ctx.author.voice.channel.connect()

    url = "https://www.youtube.com/watch?v=sahAbxq8WPw"

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    source = discord.FFmpegPCMAudio(audio_url)
    voice.play(source, after=lambda e: print("Success"))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 10

@bot.command()
@commands.is_owner()
async def comandos_random(ctx):
    if ctx.author.id != "Your Discord ID":
        return

    message = "COMANDOS RANDOM:\n\n"
    message += "!order : Reproduce la orden 66 del Canciller Palpatine.\n"
    message += "!moan : U know what i mean. @Mona CHINA grabada en vivo.\n"
    message += "!ht : El famoso Hello There!\n"
    message += "!marti : El audio por defecto de la @MARTINALGA\n"
    message += "!cmamo : Sin comentarios.\n"
    message += "!puni : No sé que estaba pensando. By @PUNIetas\n"
    message += "!move : Move bitch - favor usar a discreción, el admin es propenso a kickear gente con este audio @EL VIRGEN DE LA CUEVA\n"
    message += "!trece : Más me crece.\n"
    message += "!panpan : Directed by .... no necesita más.\n"
    message += "!sad : Música triste, como mi vida y la de la persona que use este comando.\n"
    message += "!sus : SUUUUUUUUUUUUUUUUUUUUUS\n"
    message += "!oof : No sé poner una descripción para semejante comando. échenle la culpa a @CHICO ROBLOX\n"
    message += "!bad : Nop, definitivamente nop.\n"
    message += "!turip : Turip ip ip ip. (¿En serio necesitaba descripción?)\n"
    message += "!bye : Sonido de desconexión de Discord.... por que puedo, por que quiero y por que se me dió la gana.\n"
    message += "!qb : AAAAAAAAAAAAAAH QUE BENDICIÓN.\n"
    message += "!dou : Homero ... Los Simpson .... DOU\n"
    message += "!dece : Sonido de decepción de Bot Toronja (Problemas con los derechos, favor omitir comentarios).\n"
    message += "!platanos : Ideal para cuando extrañas tu población.\n"
    message += "!bb : IT'S BRITNEY BITCH .-\n"
    message += "!vivo : No sé, no lo entendí. @FLO PEQUEÑA @El JOTO  Necesito contexto.\n"

    await ctx.send(message)

bot.run('Your Bot Token - From Dev Discord.')